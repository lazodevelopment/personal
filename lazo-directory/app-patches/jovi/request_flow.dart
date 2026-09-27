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

import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';
import 'dart:typed_data';
import 'dart:convert';
import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui_dart;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'dart:io' show Platform;

// ═══════════════════════════════════════════════════════════════════════════
// JOVI HEALTH — REQUEST CARE FLOW (human + pet)
// Refined 2026-09-22: Apple HIG pass (press feedback on pointer-down,
// critically-damped motion, Reduce Motion, Cupertino dialogs/sheets),
// reschedule + draft-restore fixes, guarded profile writes, mounted guards.
// ═══════════════════════════════════════════════════════════════════════════

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration select = Duration(milliseconds: 220);
  static const Duration page = Duration(milliseconds: 350);
  static const Duration enter = Duration(milliseconds: 420);
  static const Curve settle = Curves.easeOutCubic;
}

/// Press feedback that lives on pointer-down, not on release. Scales the
/// child down the instant a finger lands, releases when it lifts, and
/// springs back early if the finger travels ~10 px (a scroll, not a tap).
/// Honors the system Reduce Motion setting.

// ─── Timezone (members are nationwide; reminders must use theirs) ────────
/// Best-effort IANA zone id for this device. Dart only exposes the zone
/// abbreviation and the UTC offset, which is enough to place a US member.
/// The Cloud Functions read `users/{uid}.timezone` (and `requests.timezone`)
/// for appointment reminders, billing reminders and booster sweeps.
String _localTimezoneId() {
  final now = DateTime.now();
  final name = now.timeZoneName.toUpperCase();
  const byName = <String, String>{
    'EST': 'America/New_York',
    'EDT': 'America/New_York',
    'CST': 'America/Chicago',
    'CDT': 'America/Chicago',
    'MDT': 'America/Denver',
    'PST': 'America/Los_Angeles',
    'PDT': 'America/Los_Angeles',
    'AKST': 'America/Anchorage',
    'AKDT': 'America/Anchorage',
    'HST': 'Pacific/Honolulu',
    'AST': 'America/Puerto_Rico',
  };
  final julyOffset = DateTime(now.year, 7, 1).timeZoneOffset.inMinutes;
  if (name == 'MST') {
    // Arizona stays on MST all year; Denver moves to MDT (-360) in July.
    return julyOffset == -360 ? 'America/Denver' : 'America/Phoenix';
  }
  final mapped = byName[name];
  if (mapped != null) return mapped;
  // Some devices report "GMT-5" style names: fall back to the standard
  // (January) offset.
  final std = DateTime(now.year, 1, 1).timeZoneOffset.inMinutes;
  switch (std) {
    case -240:
      return 'America/Puerto_Rico';
    case -300:
      return 'America/New_York';
    case -360:
      return 'America/Chicago';
    case -420:
      return julyOffset == -360 ? 'America/Denver' : 'America/Phoenix';
    case -480:
      return 'America/Los_Angeles';
    case -540:
      return 'America/Anchorage';
    case -600:
      return 'Pacific/Honolulu';
  }
  final hours = (std ~/ 60).abs();
  // Etc/GMT signs are inverted by convention: UTC-5 is "Etc/GMT+5".
  return 'Etc/GMT${std <= 0 ? '+' : '-'}$hours';
}

class _Pressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final double pressedScale;
  final String? semanticsLabel;
  final String? semanticsHint;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
    this.pressedScale = 0.97,
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
    final reduce = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    final interactive = widget.onTap != null;
    final scale = (_down && interactive && !reduce) ? widget.pressedScale : 1.0;
    final scaled = AnimatedScale(
      scale: scale,
      duration: _down ? _Motion.pressIn : _Motion.pressOut,
      curve: _down ? Curves.easeOut : _Motion.settle,
      child: widget.child,
    );
    return Semantics(
      button: interactive,
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
        child: !interactive
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
    duration: duration ?? const Duration(milliseconds: 2600),
    backgroundColor: const Color(0xFF243352),
    elevation: 0,
    behavior: SnackBarBehavior.floating,
    margin: const EdgeInsets.fromLTRB(16, 0, 16, 96),
    shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: accent.withOpacity(0.35))),
  );
}

enum ScreenType { compact, medium, expanded, large }

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

class RequestsFlowWidget extends StatefulWidget {
  final double width;
  final double height;
  final String? rescheduleRequestId;

  const RequestsFlowWidget({
    Key? key,
    required this.width,
    required this.height,
    this.rescheduleRequestId,
  }) : super(key: key);

  @override
  _RequestsFlowWidgetState createState() => _RequestsFlowWidgetState();
}

class _RequestsFlowWidgetState extends State<RequestsFlowWidget>
    with TickerProviderStateMixin {
  // ═══════════════════════════════════════════════════════════════
  // Jovi Brand Colors (navy + glass + coral design system)
  // ═══════════════════════════════════════════════════════════════
  static const Color _brandPrimary = Color(0xFFFF6B4A); // joviCoral
  static const Color _brandDark = Color(0xFFE5583A); // joviCoralDark (accent)
  static const Color _brandLight = Color(0xFFFF8F73); // joviCoralLight

  static const Color joviCoral = Color(0xFFFF6B4A);
  static const Color joviCoralDark = Color(0xFFE5583A);
  static const Color joviCoralLight = Color(0xFFFF8F73);
  static const Color joviNavy = Color(0xFF1A2744);
  static const Color joviNavyDark = Color(0xFF0F1A2E);
  static const Color joviMint = Color(0xFF00D4AA);
  static const Color joviMintDark = Color(0xFF00B894);
  static const Color joviGold = Color(0xFFFFD166);

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

  final _formKey = GlobalKey<FormState>();
  final _uuid = Uuid();
  final PageController _pageController = PageController();
  int _pageIndex = 0;

  bool _isRescheduleMode = false;
  DocumentSnapshot? _existingRequest;

  String? _visitType;
  String? _visitMode;
  String? _selectedClinic;
  List<String> _patientNames = [];
  String? _selectedPatient;

  bool _userHasKurvPass = false;
  List<String> _suggestedSymptoms = [];

  final Map<String, List<String>> _symptomsByType = {
    'Urgent Care': [
      'Fever/Chills',
      'Cough/Cold',
      'Sore Throat',
      'Sinus Pressure',
      'Runny Nose',
      'Congestion',
      'Difficulty Breathing',
      'Shortness of Breath',
      'Wheezing',
      'Ear Pain',
      'Ear Infection',
      'Hearing Loss',
      'Eye Redness',
      'Eye Pain',
      'Vision Changes',
      'Pink Eye',
      'Nausea/Vomiting',
      'Diarrhea',
      'Constipation',
      'Stomach Pain',
      'Abdominal Cramps',
      'Heartburn',
      'Acid Reflux',
      'Food Poisoning',
      'Loss of Appetite',
      'Headache',
      'Migraine',
      'Back Pain',
      'Neck Pain',
      'Joint Pain',
      'Muscle Pain',
      'Chest Pain',
      'Cuts/Wounds',
      'Burns',
      'Bruising',
      'Sprains/Strains',
      'Fracture Concern',
      'Rash/Skin Issue',
      'Hives',
      'Itching',
      'Skin Infection',
      'Insect Bites',
      'Acne',
      'Eczema Flare',
      'Psoriasis',
      'UTI/Bladder Issue',
      'Kidney Pain',
      'STD Screening',
      'Allergic Reaction',
      'Seasonal Allergies',
      'Asthma Attack',
      'Dizziness',
      'Fainting',
      'Dehydration',
      'Fatigue',
      'Insomnia',
      'Anxiety Attack',
      'Depression Symptoms',
      'COVID-19 Symptoms',
      'Flu Symptoms',
      'Urgent Care Medication Refill',
    ],
    'Primary Care': [
      'Annual Physical',
      'Sports Physical',
      'Pre-Employment Physical',
      'School Physical',
      'Well Woman Exam',
      'Well Man Exam',
      'Blood Pressure Check',
      'Diabetes Management',
      'High Cholesterol',
      'Thyroid Issues',
      'Arthritis',
      'Asthma Management',
      'COPD Management',
      'Heart Disease Follow-up',
      'Weight Management',
      'Obesity Consultation',
      'Nutritional Counseling',
      'Eating Disorder Support',
      'Mental Health',
      'Depression',
      'Anxiety',
      'ADHD Evaluation',
      'Stress Management',
      'Grief Counseling',
      'Chronic Pain',
      'Fibromyalgia',
      'Arthritis Pain',
      'Back Pain Management',
      'Headache Management',
      'Medication Management',
      'Preventive Care',
      'Lab Results Review',
      'Cancer Screening',
      'STD Testing',
      'Immunizations',
      'Travel Vaccinations',
      'Birth Control Consultation',
      'Pregnancy Test',
      'Menstrual Issues',
      'Menopause Symptoms',
      'PCOS Management',
      'Erectile Dysfunction',
      'Low Testosterone',
      'Prostate Health',
      'Male Pattern Baldness',
      'Smoking Cessation',
      'Substance Abuse Counseling',
      'Sleep Disorders',
      'Fatigue Evaluation',
      'Primary Care Medication Refill',
    ],
    'Wellness': [
      'Weight Loss',
      'Weight Gain',
      'Muscle Building',
      'Fitness Planning',
      'Exercise Planning',
      'Athletic Performance',
      'Body Composition Analysis',
      'Nutrition Counseling',
      'Meal Planning',
      'Dietary Supplements',
      'Vitamin Deficiency',
      'Food Sensitivity Testing',
      'Gut Health',
      'Stress Management',
      'Mindfulness Training',
      'Work-Life Balance',
      'Burnout Prevention',
      'Emotional Wellness',
      'Sleep Issues',
      'Sleep Optimization',
      'Energy Enhancement',
      'Fatigue Management',
      'Preventive Screening',
      'Health Risk Assessment',
      'Genetic Testing',
      'Age Management',
      'Longevity Planning',
      'Health Coaching',
      'Lifestyle Changes',
      'Habit Formation',
      'Addiction Recovery Support',
      'Holistic Health',
      'Functional Medicine',
      'Integrative Health',
    ],
  };

  String _symptomSearchQuery = '';
  List<String> _filteredSymptoms = [];
  final TextEditingController _symptomSearchController =
      TextEditingController();

  String? _selectedSymptom;
  String? _symptomDuration;
  final TextEditingController _detailsCtrl = TextEditingController();
  final TextEditingController _medicationCtrl = TextEditingController();

  String? _selectedBeverage;
  String? _selectedTeaType;

  final TextEditingController _currentMedicationsCtrl = TextEditingController();
  final TextEditingController _allergiesCtrl = TextEditingController();
  final TextEditingController _previousSurgeriesCtrl = TextEditingController();
  final TextEditingController _familyHistoryCtrl = TextEditingController();
  final TextEditingController _primaryPhysicianCtrl = TextEditingController();

  String? _smokingStatus;
  String? _alcoholConsumption;
  String? _exerciseFrequency;
  final TextEditingController _dietaryRestrictionsCtrl =
      TextEditingController();

  String? _emergencyContactName;
  String? _emergencyContactPhone;
  String? _preferredPharmacy;

  Uint8List? _photoBytes;
  String? _photoUrl;
  DateTime? _selectedDate;
  TimeOfDay? _selectedTime;
  String? _selectedTimeSlot;
  final _picker = ImagePicker();

  late AnimationController _animController;
  late Animation<double> _scaleAnim;
  late Animation<double> _fadeAnim;

  static const Set<String> _noSymptomsSteps = {
    'Annual Physical',
    'Blood Pressure Check',
    'Preventive Care',
    'Preventive Screening',
  };

  static const Set<String> _noAppointmentNeeded = {
    'Urgent Care Medication Refill',
    'Primary Care Medication Refill',
  };

  static const Set<String> _needsPhotoSymptoms = {
    'Cuts/Wounds',
    'Rash/Skin Issue',
    'Eye Problem',
  };

  bool _isLoading = false;
  bool _showSuccess = false;

  Timer? _autoSaveTimer;

  List<String> _availableTimeSlots = [];
  List<String> _bookedTimeSlots = [];

  DateTime _calendarMonth = DateTime.now();
  bool _showMorningSlots = true;

  final Map<String, Map<String, dynamic>> _clinicLocations = {
    'Littleton - Dakota Ridge': {
      'address': '13402 W Coal Mine Ave Suite 225',
      'city': 'Littleton',
      'state': 'CO',
      'zip': '80127',
      'fullAddress': '13402 W Coal Mine Ave Suite 225, Littleton, CO 80127',
      'lat': 39.5847,
      'lng': -105.1511,
      'phone': '(844) 774-5878',
    },
    'Scottsdale - Scottsdale Gateway': {
      'address': '9201 E Mountain View Rd Suite 220',
      'city': 'Scottsdale',
      'state': 'AZ',
      'zip': '85258',
      'fullAddress': '9201 E Mountain View Rd Suite 220, Scottsdale, AZ 85258',
      'lat': 33.5764,
      'lng': -111.8442,
      'phone': '(844) 774-5878',
    },
    'Dallas - Medical City Campus': {
      'address': '7777 Forest Ln., C-699',
      'city': 'Dallas',
      'state': 'TX',
      'zip': '75230',
      'fullAddress': '7777 Forest Ln., C-699, Dallas, TX 75230',
      'lat': 32.8618,
      'lng': -96.7586,
      'phone': '(844) 774-5878',
    },
  };

  final List<String> _teaOptions = [
    'Chamomile',
    'Ginger',
    'Peppermint',
    'Lemon',
    'Green Tea',
  ];

  // ═══════════════════════════════════════════════════════════════
  // FLOW MODE SELECTOR (human vs pet)
  // When null, the widget shows the chooser landing. When set, it
  // renders the corresponding flow. Persisted to SharedPreferences
  // so returning users skip straight to their last-used mode; a
  // one-tap "Switch" affordance in each flow lets them flip back
  // to the chooser.
  //
  // Rescheduling bypasses the chooser — an appointment being
  // rescheduled was already booked under a specific mode, so the
  // flow mode is inferred from the appointment being edited.
  // ═══════════════════════════════════════════════════════════════
  String? _flowMode; // null | 'human' | 'pet'
  bool _flowModeInitialized = false;

  // List of pets registered to this user. Loaded on mount from
  // users/{uid}.pets (JSON-encoded strings, same schema as the
  // profile/onboarding widgets). Used to gate the pet choice card
  // in the chooser — if the user has no pets, we nudge them to
  // register one instead of letting them into an empty pet flow.
  List<Map<String, dynamic>> _userPets = [];
  bool _petsLoaded = false;

  // Human profiles on the account (primary user + any dependents).
  // Loaded in parallel with pets for the picker. Each entry has:
  //   { 'name': String, 'photoUrl': String?, 'kind': 'primary' | 'dependent' }
  // The primary account holder is always first.
  List<Map<String, dynamic>> _accountHumans = [];
  bool _humansLoaded = false;

  // ═══════════════════════════════════════════════════════════════
  // PET FLOW STATE
  // Parallel state for the Pet Request Care flow. Kept separate from
  // human state so switching between flows doesn't leak data.
  // ═══════════════════════════════════════════════════════════════

  // The pet the user has selected for this request (Step 1).
  Map<String, dynamic>? _selectedPet;
  // Pet visit type: 'Wellness' | 'Sick or Injured' (Step 2).
  String? _petVisitType;
  // Pet clinic selection (Step 3) — reuses _clinicLocations keys.
  String? _petSelectedClinic;
  // Pet date + time (Step 4) — separate from human state.
  DateTime? _petSelectedDate;
  String? _petSelectedTime;
  // Pet symptom/reason + duration (Steps 5-6).
  String? _petSelectedSymptom;
  String? _petSelectedSymptomOtherText;
  String? _petSymptomDuration;
  // Pet additional details (Step 7).
  final TextEditingController _petDetailsCtrl = TextEditingController();
  // Pet flow page index — separate from human _pageIndex.
  int _petPageIndex = 0;
  // True once the pet flow has submitted successfully.
  bool _petSubmitting = false;
  // Backs the pet "Other" free-text field so the text survives step changes.
  final TextEditingController _petOtherSymptomCtrl = TextEditingController();
  // Medical/lifestyle fields are only written back to the profile once the
  // user has actually edited them (see _saveMedicalDataToFirebase).
  bool _medicalDirty = false;

  bool get _reduceMotion =>
      MediaQuery.maybeOf(context)?.disableAnimations ?? false;

  void _toast(String message,
      {Color? accent, IconData? icon, Duration? duration}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(
      message,
      accent: accent ?? joviCoral,
      icon: icon,
      duration: duration,
    ));
  }

  void _toastError(String message) => _toast(
        message,
        accent: const Color(0xFFE53935),
        icon: CupertinoIcons.exclamationmark_circle,
        duration: const Duration(seconds: 3),
      );

  Future<bool> _openExternal(String url) async {
    final uri = Uri.tryParse(url);
    if (uri == null) return false;
    try {
      return await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      return false;
    }
  }

  int _openSlotCount() =>
      _availableTimeSlots.where((s) => !_bookedTimeSlots.contains(s)).length;

  /// Species-aware symptom catalog for the pet flow.
  /// Keys: '<visitType>|<species>' — species is 'dog', 'cat', or 'other'
  /// (matches PetType enum values in other widgets). The 'other' list
  /// is the broad fallback shown for non-dog-non-cat species.
  /// Mirrors the pattern used in Pet Symptom Checker.
  final Map<String, List<String>> _petSymptomsByKey = {
    // ─── SICK OR INJURED — DOG ────────────────────────────────────
    'Sick or Injured|dog': [
      'Vomiting',
      'Diarrhea',
      'Not Eating',
      'Lethargy',
      'Limping/Lameness',
      'Coughing',
      'Sneezing',
      'Runny Nose',
      'Scratching/Itching',
      'Hot Spots',
      'Ear Infection',
      'Eye Discharge/Redness',
      'Skin Rash',
      'Hair Loss',
      'Excessive Thirst',
      'Frequent Urination',
      'Accidents in House',
      'Blood in Stool',
      'Blood in Urine',
      'Straining to Urinate',
      'Seizure',
      'Trembling/Shaking',
      'Disoriented',
      'Collapsed',
      'Difficulty Breathing',
      'Wound/Laceration',
      'Bleeding',
      'Bite Wound',
      'Limping After Exercise',
      'Hip/Joint Pain',
      'Back Pain',
      'Bloated Belly',
      'Dragging Rear Legs',
      'Whining/Vocalizing in Pain',
      'Aggression Change',
      'Hiding/Withdrawn',
      'Destructive Behavior Change',
      'Bad Breath',
      'Drooling Excessively',
      'Teeth Issues',
      'Tick/Flea Infestation',
      'Ingested Something',
      'Dental Pain',
      'Anal Gland Issue',
      'Pawing at Mouth',
      'Other',
    ],
    // ─── SICK OR INJURED — CAT ────────────────────────────────────
    'Sick or Injured|cat': [
      'Vomiting',
      'Diarrhea',
      'Not Eating',
      'Lethargy',
      'Hiding/Withdrawn',
      'Litter Box Avoidance',
      'Straining in Litter Box',
      'Blood in Urine',
      'Blood in Stool',
      'Crying While Urinating',
      'Frequent Urination',
      'Constipation',
      'Excessive Thirst',
      'Weight Loss',
      'Weight Gain',
      'Coughing',
      'Sneezing',
      'Runny Nose',
      'Eye Discharge/Redness',
      'Scratching/Itching',
      'Hair Loss',
      'Skin Rash',
      'Lumps/Bumps',
      'Limping/Lameness',
      'Difficulty Jumping',
      'Seizure',
      'Trembling/Shaking',
      'Disoriented',
      'Collapsed',
      'Difficulty Breathing',
      'Open-Mouth Breathing',
      'Wound/Laceration',
      'Bleeding',
      'Bite/Scratch Wound',
      'Abscess',
      'Bad Breath',
      'Drooling',
      'Teeth Issues',
      'Pawing at Mouth',
      'Vocalizing in Pain',
      'Aggression Change',
      'Over-Grooming',
      'Under-Grooming',
      'Unkempt Coat',
      'Tick/Flea Infestation',
      'Ingested Something',
      'Other',
    ],
    // ─── SICK OR INJURED — OTHER (broad fallback) ─────────────────
    'Sick or Injured|other': [
      'Not Eating',
      'Lethargy',
      'Vomiting',
      'Diarrhea',
      'Difficulty Breathing',
      'Wound/Injury',
      'Bleeding',
      'Seizure',
      'Trembling/Shaking',
      'Collapsed',
      'Disoriented',
      'Skin Issue',
      'Hair/Feather Loss',
      'Eye Issue',
      'Behavior Change',
      'Weight Loss',
      'Weight Gain',
      'Drinking Too Much',
      'Not Drinking',
      'Toileting Issue',
      'Blood in Waste',
      'Overgrown Nails/Beak',
      'Temperature Issue',
      'Ingested Something',
      'Other',
    ],
    // ─── WELLNESS — DOG ───────────────────────────────────────────
    'Wellness|dog': [
      'Annual Wellness Exam',
      'Puppy Visit',
      'Senior Wellness Check',
      'Vaccinations Due',
      'Rabies Vaccine',
      'DHPP Vaccine',
      'Bordetella/Kennel Cough',
      'Lyme Vaccine',
      'Leptospirosis',
      'Heartworm Test',
      'Heartworm Prevention Refill',
      'Flea & Tick Prevention',
      'Fecal/Parasite Screening',
      'Weight Check',
      'Nutrition Counseling',
      'Dental Cleaning',
      'Dental Consultation',
      'Spay/Neuter Consultation',
      'Microchipping',
      'Nail Trim',
      'Anal Gland Expression',
      'Travel Health Certificate',
      'Behavior Consultation',
      'Chronic Condition Check-in',
      'Arthritis Management',
      'Allergy Management',
      'Diabetes Management',
      'Blood Work / Lab Panel',
      'Pre-Surgery Consultation',
      'Post-Surgery Follow-up',
      'Medication Refill',
      'Other',
    ],
    // ─── WELLNESS — CAT ───────────────────────────────────────────
    'Wellness|cat': [
      'Annual Wellness Exam',
      'Kitten Visit',
      'Senior Wellness Check',
      'Vaccinations Due',
      'Rabies Vaccine',
      'FVRCP Vaccine',
      'FeLV Vaccine',
      'FeLV/FIV Test',
      'Fecal/Parasite Screening',
      'Flea Prevention',
      'Deworming',
      'Weight Check',
      'Nutrition Counseling',
      'Dental Cleaning',
      'Dental Consultation',
      'Spay/Neuter Consultation',
      'Microchipping',
      'Nail Trim',
      'Travel Health Certificate',
      'Behavior Consultation',
      'Chronic Condition Check-in',
      'Kidney Disease Management',
      'Hyperthyroidism Management',
      'Diabetes Management',
      'Allergy Management',
      'Blood Work / Lab Panel',
      'Pre-Surgery Consultation',
      'Post-Surgery Follow-up',
      'Medication Refill',
      'Other',
    ],
    // ─── WELLNESS — OTHER ─────────────────────────────────────────
    'Wellness|other': [
      'Annual Wellness Exam',
      'New Pet Intake',
      'Senior Wellness Check',
      'Vaccinations Due',
      'Species-Appropriate Diet Consultation',
      'Nutrition Counseling',
      'Habitat Consultation',
      'Weight Check',
      'Nail/Beak/Hoof Trim',
      'Parasite Screening',
      'Blood Work / Lab Panel',
      'Behavior Consultation',
      'Chronic Condition Check-in',
      'Pre-Surgery Consultation',
      'Post-Surgery Follow-up',
      'Medication Refill',
      'Other',
    ],
  };

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
    _initializeApp();
    _symptomsByType.forEach((key, value) => value.sort());
    _startAutoSave();
    _calendarMonth = DateTime.now();
    _initializeFlowMode();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    analyzeScreenConfiguration();
  }

  // ═══════════════════════════════════════════════════════════════
  // FLOW MODE INITIALIZATION
  // Decides whether to show the chooser or jump into a flow directly.
  //
  //   1. If we're in reschedule mode, use the mode of the existing
  //      request (pet_requests vs requests collection). Reschedule
  //      never shows the chooser — that would be confusing.
  //   2. Otherwise, check SharedPreferences for the last-used mode.
  //      If found, use it — returning users expect continuity.
  //   3. Otherwise, leave _flowMode null so the chooser renders.
  //
  // Pet data is loaded in parallel so the chooser can decide whether
  // to enable the Pet card.
  // ═══════════════════════════════════════════════════════════════

  static const String _flowModePrefKey = 'jovi_request_flow_mode';

  Future<void> _initializeFlowMode() async {
    // Load pets and humans in parallel — both needed by the visual
    // profile picker. Loading is fire-and-forget; the picker shows
    // a skeleton while waiting.
    _loadUserPets();
    _loadAccountHumans();

    // Reschedule path: infer mode from the request being rescheduled.
    // Rescheduling a human request should drop the user directly into
    // the human flow (the picker doesn't make sense for an existing
    // appointment being moved). For now pet reschedule is not supported.
    if (widget.rescheduleRequestId != null &&
        widget.rescheduleRequestId!.isNotEmpty) {
      if (mounted) {
        setState(() {
          _flowMode = 'human';
          _flowModeInitialized = true;
        });
      }
      return;
    }

    // Clear any stale flow-mode preference from the old text chooser.
    // The visual profile picker is the new front door for Request Care,
    // and picking a specific person/pet IS the point of the screen —
    // remembering a previous flow would bypass that intent. This clear
    // is defensive: even if no pref was saved, calling remove() is a
    // no-op so it's safe to run on every init.
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_flowModePrefKey);
    } catch (e) {
      debugPrint('Flow mode pref clear failed: $e');
    }

    if (mounted) {
      setState(() => _flowModeInitialized = true);
    }
  }

  /// Save the chosen flow mode and update local state.
  Future<void> _setFlowMode(String mode) async {
    HapticFeedback.lightImpact();
    setState(() => _flowMode = mode);
    // Previously saved the chosen mode to SharedPreferences so the user
    // would land back in the same flow on next launch. We no longer do
    // that — the visual profile picker is the intended front door, and
    // remembering last choice would bypass the picker entirely.
    // See _initializeFlowMode(), which also actively clears any stale
    // value that may exist from the old text chooser.
  }

  /// Clear the selected mode and return to the chooser landing.
  /// Invoked from the "← Switch" affordance in each flow.
  void _clearFlowMode() {
    HapticFeedback.selectionClick();
    setState(() => _flowMode = null);
  }

  /// Load the user's pets from users/{uid}.pets. Schema matches the
  /// Load the user's pets from BOTH data sources:
  ///   - Legacy JSON array on user doc (onboarding writes here)
  ///   - Subcollection at users/{uid}/pets/{petId} (Pet Profiles writes here)
  /// Subcollection wins on duplicate petId (treat it as canonical).
  /// Empty or missing is fine — the chooser handles that case.
  Future<void> _loadUserPets() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        if (mounted) setState(() => _petsLoaded = true);
        return;
      }

      // Fire both reads in parallel so we don't waste a round trip.
      final userDocF =
          FirebaseFirestore.instance.collection('users').doc(user.uid).get();
      final subcollF = FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .collection('pets')
          .get();
      final results = await Future.wait([userDocF, subcollF]);
      final doc = results[0] as DocumentSnapshot<Map<String, dynamic>>;
      final subcoll = results[1] as QuerySnapshot<Map<String, dynamic>>;

      // Dedupe by petId — subcollection wins.
      final byId = <String, Map<String, dynamic>>{};

      // Subcollection first (canonical).
      for (final d in subcoll.docs) {
        final data = d.data();
        final withId = Map<String, dynamic>.from(data);
        // Ensure petId is in the map. Subcollection doc id is authoritative.
        withId['petId'] = d.id;
        byId[d.id] = withId;
      }

      // Legacy JSON array — add only if petId not already present.
      if (doc.exists) {
        final data = doc.data() as Map<String, dynamic>;
        final rawPets = data['pets'] as List<dynamic>? ?? [];
        for (final raw in rawPets) {
          try {
            Map<String, dynamic>? parsed;
            if (raw is String) {
              final p = jsonDecode(raw);
              if (p is Map<String, dynamic>) {
                parsed = p;
              } else if (p is Map) {
                parsed = Map<String, dynamic>.from(p);
              }
            } else if (raw is Map<String, dynamic>) {
              parsed = raw;
            } else if (raw is Map) {
              parsed = Map<String, dynamic>.from(raw);
            }
            if (parsed != null) {
              final pid = parsed['petId'] as String? ?? parsed['id'] as String?;
              if (pid != null && pid.isNotEmpty) {
                byId.putIfAbsent(pid, () => parsed!);
              } else {
                // Legacy pet with no id — use name as a synthetic key so we
                // don't add duplicates when this is re-read.
                final nameKey = 'legacy_${parsed['name'] ?? 'unnamed'}';
                byId.putIfAbsent(nameKey, () => parsed!);
              }
            }
          } catch (e) {
            debugPrint('Pet parse error: $e');
          }
        }
      }

      final pets = byId.values.toList()
        ..sort((a, b) {
          final an = (a['name'] as String? ?? '').toLowerCase();
          final bn = (b['name'] as String? ?? '').toLowerCase();
          return an.compareTo(bn);
        });

      if (mounted) {
        setState(() {
          _userPets = pets;
          _petsLoaded = true;
        });
      }
    } catch (e) {
      debugPrint('Load pets failed: $e');
      if (mounted) setState(() => _petsLoaded = true);
    }
  }

  /// Load all humans associated with this account — the primary user and
  /// any dependents saved under `users/{uid}.deps`. Photo URLs are taken
  /// from Firebase Auth for the primary user, and from the dependent
  /// doc itself (if the user has uploaded a dep photo).
  ///
  /// Data shape of each entry in _accountHumans:
  ///   {
  ///     'name': String,        // full name (required, never empty)
  ///     'photoUrl': String?,   // may be null or empty
  ///     'kind': String,        // 'primary' | 'dependent'
  ///     'dobString': String?,  // optional — used for subtitle
  ///   }
  Future<void> _loadAccountHumans() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        if (mounted) setState(() => _humansLoaded = true);
        return;
      }
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();
      final humans = <Map<String, dynamic>>[];

      // ── Primary user ────────────────────────────────────────────
      String primaryName = '';
      String? primaryPhoto = user.photoURL;
      if (doc.exists) {
        final data = doc.data() as Map<String, dynamic>;
        primaryName = (data['onboard_fullName'] as String?) ??
            (data['fullName'] as String?) ??
            '';
        // Prefer the user-uploaded photo if it exists in the doc,
        // otherwise fall back to auth photoURL.
        final docPhoto = (data['photo_url'] as String?) ??
            (data['photoUrl'] as String?) ??
            (data['onboard_photo'] as String?);
        if (docPhoto != null && docPhoto.isNotEmpty) {
          primaryPhoto = docPhoto;
        }
      }
      if (primaryName.isEmpty) {
        primaryName = user.displayName ?? 'You';
      }
      humans.add({
        'name': primaryName,
        'photoUrl': primaryPhoto,
        'kind': 'primary',
      });

      // ── Dependents ──────────────────────────────────────────────
      if (doc.exists) {
        final data = doc.data() as Map<String, dynamic>;
        final deps = data['deps'] as List<dynamic>? ?? [];
        for (final raw in deps) {
          try {
            Map<String, dynamic>? dep;
            if (raw is String) {
              final parsed = jsonDecode(raw);
              if (parsed is Map<String, dynamic>) {
                dep = parsed;
              } else if (parsed is Map) {
                dep = Map<String, dynamic>.from(parsed);
              }
            } else if (raw is Map<String, dynamic>) {
              dep = raw;
            } else if (raw is Map) {
              dep = Map<String, dynamic>.from(raw);
            }
            if (dep == null) continue;
            final first = (dep['first'] as String?) ?? '';
            final last = (dep['last'] as String?) ?? '';
            final name = '$first $last'.trim();
            if (name.isEmpty) continue;
            final photoUrl = (dep['photo_url'] as String?) ??
                (dep['photoUrl'] as String?) ??
                (dep['photo'] as String?);
            final dob =
                (dep['dob'] as String?) ?? (dep['dateOfBirth'] as String?);
            humans.add({
              'name': name,
              'photoUrl': photoUrl,
              'kind': 'dependent',
              'dobString': dob,
            });
          } catch (e) {
            debugPrint('Dep parse error: $e');
          }
        }
      }

      if (mounted) {
        setState(() {
          _accountHumans = humans;
          _humansLoaded = true;
        });
      }
    } catch (e) {
      debugPrint('Load humans failed: $e');
      if (mounted) setState(() => _humansLoaded = true);
    }
  }

  Future<void> _initializeReschedule() async {
    if (widget.rescheduleRequestId != null &&
        widget.rescheduleRequestId!.isNotEmpty) {
      setState(() {
        _isRescheduleMode = true;
      });

      try {
        final doc = await FirebaseFirestore.instance
            .collection('requests')
            .doc(widget.rescheduleRequestId)
            .get();

        if (doc.exists && mounted) {
          setState(() {
            _existingRequest = doc;
            final data = doc.data() as Map<String, dynamic>;

            _visitType = data['visitType'] ?? '';
            _visitMode = data['visitMode'] ?? '';
            _selectedClinic = data['clinic'] ?? '';
            _selectedPatient = data['patientName'] ?? '';
            _selectedSymptom = data['symptom'] ?? '';
            _symptomDuration = data['symptomDuration'] ?? '';
            _detailsCtrl.text = data['details'] ?? '';
            _medicationCtrl.text = data['medication'] ?? '';
            _userHasKurvPass = data['priority'] ?? false;

            _selectedBeverage = data['selectedBeverage'];
            _selectedTeaType = data['selectedTeaType'];

            _selectedDate = null;
            _selectedTimeSlot = null;

            // Reschedule renders a single page (the date/time step), so
            // the index must be 0 — anything else skipped validation and
            // let an empty date be submitted.
            _pageIndex = 0;
          });
        }
      } catch (e) {
        debugPrint('Error loading existing request: $e');
        _toastError('We couldn\'t load that appointment. Please try again.');
      }
    }
  }

  int _getDateTimePageIndex() {
    if (_isRefill()) return 0;

    int index = 0;
    index++;
    if (_visitType != null) index++;
    if (_visitMode == 'Clinic') index++;
    if (_visitMode == 'Clinic' && _selectedClinic != null) index++;
    if (_visitMode != null &&
        (_visitMode != 'Clinic' || _selectedClinic != null)) {
      index++;
    }
    if (_selectedPatient != null) index++;

    if (_isRefill()) {
      index++;
      index++;
      return index;
    }

    if (_selectedSymptom != null && !_isRefill()) {
      if (_needsSymptomsSteps()) index++;
      if (_needsSymptomsSteps()) index++;
      index++;
      index++;
      if (_needsPhoto(_selectedSymptom)) index++;
      return index;
    }

    return index;
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

    // Called from didChangeDependencies (before build) — no setState needed,
    // and calling it there is what caused the setState-during-build errors.
    _lastScreenWidth = screenWidth;
    _lastHasHinge = hasHinge;
    currentScreenType = screenType;
    layoutSettings = generateLayoutConfig(screenType, screenWidth, hasHinge);
  }

  ResponsiveConfig generateLayoutConfig(
      ScreenType type, double width, bool hasHinge) {
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
          constraints: BoxConstraints(maxWidth: layoutSettings.contentMax),
          child: child,
        ),
      );
    }
    return child;
  }

  EdgeInsets _getAdaptivePadding(BuildContext context) {
    return EdgeInsets.symmetric(
      horizontal: layoutSettings.paddingH,
      vertical: layoutSettings.paddingV,
    );
  }

  void _initializeAnimations() {
    _animController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    _scaleAnim = Tween<double>(begin: 0.86, end: 1.0).animate(
      CurvedAnimation(parent: _animController, curve: _Motion.settle),
    );
    _fadeAnim = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOut,
    );
  }

  Future<void> _initializeApp() async {
    await Future.wait([
      _loadPatientNames(),
      _loadSavedFormData(),
      _loadSuggestedSymptoms(),
    ]);
    await _initializeReschedule();
    _generateAvailableTimeSlots();
  }

  @override
  void dispose() {
    _autoSaveTimer?.cancel();
    // Snapshots every field synchronously before its first await, so it is
    // safe to run before the controllers below are disposed.
    _saveFormData();
    _pageController.dispose();
    _detailsCtrl.dispose();
    _medicationCtrl.dispose();
    _currentMedicationsCtrl.dispose();
    _allergiesCtrl.dispose();
    _previousSurgeriesCtrl.dispose();
    _familyHistoryCtrl.dispose();
    _primaryPhysicianCtrl.dispose();
    _dietaryRestrictionsCtrl.dispose();
    _symptomSearchController.dispose();
    _petDetailsCtrl.dispose();
    _petOtherSymptomCtrl.dispose();
    _animController.dispose();
    super.dispose();
  }

  Future<void> _loadSavedFormData() async {
    try {
      await _loadMedicalDataFromFirebase();
      final prefs = await SharedPreferences.getInstance();
      final isReschedule = (widget.rescheduleRequestId ?? '').isNotEmpty;
      if (!mounted || isReschedule) return;
      setState(() {
        // Never clobber a choice the user already made (e.g. the patient
        // picked on the "Who's this for?" screen while this was loading).
        _visitType ??= prefs.getString('visitType');
        _visitMode ??= prefs.getString('visitMode');
        _selectedPatient ??= prefs.getString('selectedPatient');
        _selectedSymptom ??= prefs.getString('selectedSymptom');
        _symptomDuration ??= prefs.getString('symptomDuration');
        if (_detailsCtrl.text.isEmpty) {
          _detailsCtrl.text = prefs.getString('details') ?? '';
        }
        if (_medicationCtrl.text.isEmpty) {
          _medicationCtrl.text = prefs.getString('medication') ?? '';
        }
        _selectedBeverage ??= prefs.getString('selectedBeverage');
        _selectedTeaType ??= prefs.getString('selectedTeaType');
      });
    } catch (e) {
      debugPrint('Error loading saved form data: $e');
    }
  }

  Future<void> _loadMedicalDataFromFirebase() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        final doc = await FirebaseFirestore.instance
            .collection('users')
            .doc(user.uid)
            .get();

        if (doc.exists && mounted) {
          final data = doc.data() as Map<String, dynamic>;
          setState(() {
            if (data['allergies'] != null) {
              if (data['allergies'] is List) {
                _allergiesCtrl.text = (data['allergies'] as List).join(', ');
              } else {
                _allergiesCtrl.text = data['allergies'].toString();
              }
            }
            _currentMedicationsCtrl.text = data['currentMedications'] ?? '';
            _previousSurgeriesCtrl.text = data['previousSurgeries'] ?? '';
            _familyHistoryCtrl.text = data['familyMedicalHistory'] ?? '';
            _primaryPhysicianCtrl.text = data['primaryPhysician'] ?? '';

            if (_familyHistoryCtrl.text.isEmpty &&
                data['onboard_conditions'] != null) {
              _familyHistoryCtrl.text = data['onboard_conditions'];
            }

            _smokingStatus = data['smokingStatus'] ??
                (data['tobacco'] == true ? 'Current smoker' : null);
            _alcoholConsumption = data['alcoholConsumption'];
            _exerciseFrequency = data['exerciseFrequency'];
            _dietaryRestrictionsCtrl.text = data['dietaryRestrictions'] ?? '';

            _emergencyContactName = data['onboard_emName'];
            _emergencyContactPhone = data['onboard_emPhone'];
            _preferredPharmacy = data['onboard_pharmacy'];
          });
        }
      }
    } catch (e) {
      debugPrint('Error loading medical data from Firebase: $e');
    }
  }

  Future<void> _saveMedicalDataToFirebase() async {
    // Only write back once the user has edited something — otherwise a
    // failed profile load (or an untouched form) would wipe their allergies
    // and history every 30 seconds via the auto-save timer.
    if (!_medicalDirty) return;
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        List<String> allergiesList = [];
        if (_allergiesCtrl.text.isNotEmpty &&
            _allergiesCtrl.text.toLowerCase() != 'none') {
          allergiesList = _allergiesCtrl.text
              .split(',')
              .map((a) => a.trim())
              .where((a) => a.isNotEmpty)
              .toList();
        }

        await FirebaseFirestore.instance
            .collection('users')
            .doc(user.uid)
            .set({
          'currentMedications': _currentMedicationsCtrl.text,
          'allergies': allergiesList,
          'previousSurgeries': _previousSurgeriesCtrl.text,
          'familyMedicalHistory': _familyHistoryCtrl.text,
          'primaryPhysician': _primaryPhysicianCtrl.text,
          'tobacco': _smokingStatus == 'Current smoker' ||
              _smokingStatus == 'Vaping/E-cigarettes',
          'smokingStatus': _smokingStatus,
          'alcoholConsumption': _alcoholConsumption,
          'exerciseFrequency': _exerciseFrequency,
          'dietaryRestrictions': _dietaryRestrictionsCtrl.text,
          'medicalDataLastUpdated': FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
        _medicalDirty = false;
      }
    } catch (e) {
      debugPrint('Error saving medical data to Firebase: $e');
    }
  }

  Future<void> _saveFormData() async {
    // A submitted request is not a draft, and a reschedule is not a new
    // request — saving either would "restore" it next time the flow opens.
    if (_showSuccess || _isRescheduleMode) return;
    // Snapshot synchronously: this also runs from dispose().
    final visitType = _visitType;
    final visitMode = _visitMode;
    final patient = _selectedPatient;
    final symptom = _selectedSymptom;
    final duration = _symptomDuration;
    final details = _detailsCtrl.text;
    final medication = _medicationCtrl.text;
    final beverage = _selectedBeverage;
    final tea = _selectedTeaType;
    final medicalSave = _saveMedicalDataToFirebase();
    try {
      final prefs = await SharedPreferences.getInstance();
      if (visitType != null) await prefs.setString('visitType', visitType);
      if (visitMode != null) await prefs.setString('visitMode', visitMode);
      if (patient != null) await prefs.setString('selectedPatient', patient);
      if (symptom != null) await prefs.setString('selectedSymptom', symptom);
      if (duration != null) await prefs.setString('symptomDuration', duration);
      await prefs.setString('details', details);
      await prefs.setString('medication', medication);
      if (beverage != null) await prefs.setString('selectedBeverage', beverage);
      if (tea != null) await prefs.setString('selectedTeaType', tea);
      await medicalSave;
    } catch (e) {
      debugPrint('Error saving form data: $e');
    }
  }

  Future<void> _loadSuggestedSymptoms() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null && _visitType != null) {
        final history = await FirebaseFirestore.instance
            .collection('requests')
            .where('userId', isEqualTo: user.uid)
            .where('visitType', isEqualTo: _visitType)
            .orderBy('createdAt', descending: true)
            .limit(10)
            .get();

        final symptoms = history.docs
            .map((doc) => doc.data()['symptom'] as String?)
            .where((s) => s != null)
            .cast<String>()
            .toSet()
            .toList();

        if (!mounted) return;
        setState(() {
          _suggestedSymptoms = symptoms.take(3).toList();
        });
      }
    } catch (e) {
      debugPrint('Error loading suggested symptoms: $e');
    }
  }

  void _startAutoSave() {
    _autoSaveTimer = Timer.periodic(Duration(seconds: 30), (_) async {
      await _saveFormData();
    });
  }

  Future<void> _showCalendarInstructions() async {
    if (_selectedDate == null || _selectedTimeSlot == null) return;

    try {
      final timeStr = _selectedTimeSlot!;
      final timeParts =
          timeStr.replaceAll(' AM', '').replaceAll(' PM', '').split(':');
      final hour = int.parse(timeParts[0]);
      final minute = int.parse(timeParts[1]);

      final is24Hour = timeStr.contains('PM') && hour != 12;
      final actualHour = is24Hour
          ? hour + 12
          : (timeStr.contains('AM') && hour == 12 ? 0 : hour);

      final startTime = DateTime(
        _selectedDate!.year,
        _selectedDate!.month,
        _selectedDate!.day,
        actualHour,
        minute,
      );

      final endTime = startTime.add(Duration(minutes: 30));

      showDialog(
        context: context,
        builder: (BuildContext context) {
          return Dialog(
            backgroundColor: Colors.transparent,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: BackdropFilter(
                filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
                child: Container(
                  padding: EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: joviNavy.withOpacity(0.92),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: Colors.white.withOpacity(0.12),
                      width: 1,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.35),
                        blurRadius: 30,
                        offset: Offset(0, 15),
                      ),
                    ],
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: joviCoral.withOpacity(0.2),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Icon(Icons.calendar_today,
                                color: joviCoral, size: 22),
                          ),
                          SizedBox(width: 12),
                          Text(
                            'Add to Calendar',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 16),
                      Text(
                        'Appointment Details:',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                      SizedBox(height: 8),
                      Text(
                          'Date: ${DateFormat.yMMMMd().format(_selectedDate!)}',
                          style:
                              TextStyle(color: Colors.white.withOpacity(0.85))),
                      Text('Time: $_selectedTimeSlot',
                          style:
                              TextStyle(color: Colors.white.withOpacity(0.85))),
                      Text('Type: ${_selectedSymptom ?? _visitType}',
                          style:
                              TextStyle(color: Colors.white.withOpacity(0.85))),
                      if (_visitMode == 'Clinic' && _selectedClinic != null)
                        Text('Location: $_selectedClinic',
                            style: TextStyle(
                                color: Colors.white.withOpacity(0.85))),
                      if (_selectedBeverage != null) ...[
                        SizedBox(height: 8),
                        Text(
                            'Beverage: $_selectedBeverage${_selectedTeaType != null ? ' ($_selectedTeaType)' : ''}',
                            style: TextStyle(
                                color: Colors.white.withOpacity(0.85))),
                      ],
                      SizedBox(height: 16),
                      Text(
                        'Please add this appointment to your calendar manually using the details above.',
                        style: TextStyle(color: Colors.white.withOpacity(0.6)),
                      ),
                      SizedBox(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          TextButton(
                            onPressed: () {
                              Navigator.of(context).pop();
                              final details = _buildCalendarDescription();
                              Clipboard.setData(ClipboardData(text: details));
                              _toast('Appointment details copied',
                                  accent: joviMint,
                                  icon: CupertinoIcons.doc_on_clipboard);
                            },
                            style: TextButton.styleFrom(
                              foregroundColor: Colors.white.withOpacity(0.8),
                            ),
                            child: Text('Copy Details'),
                          ),
                          SizedBox(width: 8),
                          ElevatedButton(
                            onPressed: () => Navigator.of(context).pop(),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: joviCoral,
                              foregroundColor: Colors.white,
                              elevation: 0,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10),
                              ),
                            ),
                            child: Text('Got It'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      );
    } catch (e) {
      debugPrint('Error showing calendar instructions: $e');
      _toast('Please add the appointment to your calendar manually.',
          accent: joviGold,
          icon: CupertinoIcons.calendar,
          duration: const Duration(seconds: 3));
    }
  }

  String _buildCalendarDescription() {
    final buffer = StringBuffer();

    buffer.writeln('Jovi Health Appointment');
    buffer.writeln('');
    buffer.writeln('Patient: ${_selectedPatient ?? 'Not specified'}');
    buffer.writeln('Visit Type: ${_visitType ?? 'Not specified'}');
    buffer.writeln('Visit Mode: ${_visitMode ?? 'Not specified'}');

    if (_selectedSymptom != null) {
      buffer.writeln('Reason: $_selectedSymptom');
    }

    if (_detailsCtrl.text.isNotEmpty) {
      buffer.writeln('Notes: ${_detailsCtrl.text}');
    }

    if (_selectedBeverage != null) {
      buffer.writeln(
          'Complimentary Beverage: $_selectedBeverage${_selectedTeaType != null ? ' ($_selectedTeaType)' : ''}');
    }

    buffer.writeln('');
    buffer.writeln('Please arrive 15 minutes early for check-in.');

    if (_visitMode == 'Virtual') {
      buffer.writeln('');
      buffer.writeln(
          'This is a virtual appointment. You will receive connection details via email.');
    }

    return buffer.toString();
  }

  String _getCalendarLocation() {
    if (_visitMode == 'Virtual') {
      return 'Virtual Appointment';
    } else if (_selectedClinic != null &&
        _clinicLocations.containsKey(_selectedClinic)) {
      return _clinicLocations[_selectedClinic]!['fullAddress'] as String;
    }
    return 'Jovi Health';
  }

  Future<void> _launchMapNavigation() async {
    if (_selectedClinic == null) return;

    final clinicInfo = _clinicLocations[_selectedClinic];
    if (clinicInfo == null) return;

    final lat = clinicInfo['lat'] as double;
    final lng = clinicInfo['lng'] as double;
    final address = Uri.encodeComponent(clinicInfo['fullAddress'] as String);

    try {
      if (Platform.isIOS) {
        final appleMapsUrl = 'http://maps.apple.com/?daddr=$lat,$lng&dirflg=d';
        if (await _openExternal(appleMapsUrl)) return;
      }

      if (Platform.isAndroid) {
        final googleMapsApp = 'google.navigation:q=$lat,$lng&mode=d';
        if (await _openExternal(googleMapsApp)) return;
      }

      final googleMapsWeb =
          'https://www.google.com/maps/dir/?api=1&destination=$lat,$lng&travelmode=driving';
      if (await _openExternal(googleMapsWeb)) return;

      final fallbackUrl =
          'https://www.google.com/maps/search/?api=1&query=$address';
      if (!await _openExternal(fallbackUrl)) {
        throw Exception('No map apps available');
      }
    } catch (e) {
      debugPrint('Error launching maps: $e');
      _toast('Unable to open Maps. Address: ${clinicInfo['fullAddress']}',
          accent: joviGold,
          icon: CupertinoIcons.map,
          duration: const Duration(seconds: 5));
    }
  }

  Future<void> _showFallbackDatePicker() async {
    final DateTime now = DateTime.now();
    final List<DateTime> availableDates = [];

    for (int i = 0; i < 30; i++) {
      final date = now.add(Duration(days: i));
      if (date.weekday != DateTime.sunday) {
        availableDates.add(date);
      }
    }

    await showDialog(
      context: context,
      builder: (BuildContext context) {
        return Dialog(
          backgroundColor: Colors.transparent,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: BackdropFilter(
              filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
              child: Container(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.of(context).size.height * 0.7,
                  maxWidth: layoutSettings.wideMode
                      ? 600
                      : MediaQuery.of(context).size.width * 0.9,
                ),
                decoration: BoxDecoration(
                  color: joviNavy.withOpacity(0.92),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.12),
                    width: 1,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.35),
                      blurRadius: 30,
                      offset: Offset(0, 15),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      padding: EdgeInsets.all(layoutSettings.paddingH),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [joviCoral, joviCoralDark],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.vertical(
                          top: Radius.circular(20),
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.calendar_today, color: Colors.white),
                          SizedBox(width: 12),
                          Text(
                            'Select Date',
                            style: TextStyle(
                              fontSize: layoutSettings.wideMode ? 22 : 20,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Flexible(
                      child: ListView.builder(
                        shrinkWrap: true,
                        padding: EdgeInsets.symmetric(vertical: 8),
                        itemCount: availableDates.length,
                        itemBuilder: (context, index) {
                          final date = availableDates[index];
                          final isToday = date.year == now.year &&
                              date.month == now.month &&
                              date.day == now.day;
                          final isTomorrow = date.year == now.year &&
                              date.month == now.month &&
                              date.day == now.day + 1;

                          String dateLabel =
                              DateFormat.yMMMMEEEEd().format(date);
                          if (isToday) dateLabel = 'Today - $dateLabel';
                          if (isTomorrow) dateLabel = 'Tomorrow - $dateLabel';

                          final isSelected = _selectedDate != null &&
                              _selectedDate!.year == date.year &&
                              _selectedDate!.month == date.month &&
                              _selectedDate!.day == date.day;

                          return ListTile(
                            onTap: () {
                              setState(() {
                                _selectedDate = date;
                                _selectedTimeSlot = null;
                              });
                              _generateAvailableTimeSlots();
                              _loadBookedTimeSlots();
                              Navigator.of(context).pop();
                              HapticFeedback.mediumImpact();
                            },
                            title: Text(
                              dateLabel,
                              style: TextStyle(
                                fontSize: layoutSettings.actionTextSize + 3,
                                fontWeight: isToday || isTomorrow
                                    ? FontWeight.w600
                                    : FontWeight.normal,
                                color: Colors.white,
                              ),
                            ),
                            trailing: isSelected
                                ? Icon(Icons.check_circle, color: joviCoral)
                                : Icon(Icons.chevron_right,
                                    color: Colors.white.withOpacity(0.4)),
                            tileColor:
                                isSelected ? joviCoral.withOpacity(0.12) : null,
                          );
                        },
                      ),
                    ),
                    Container(
                      padding: EdgeInsets.all(layoutSettings.paddingH),
                      child: TextButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: Text(
                          'Cancel',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.7),
                            fontSize: layoutSettings.actionTextSize + 3,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _loadPatientNames() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        final doc = await FirebaseFirestore.instance
            .collection('users')
            .doc(user.uid)
            .get();
        if (!mounted) return;
        if (doc.exists) {
          final data = doc.data() as Map<String, dynamic>;
          final names = <String>[];

          final primaryName = (data['onboard_fullName'] as String?) ??
              (data['fullName'] as String?);
          if (primaryName != null && primaryName.isNotEmpty) {
            names.add(primaryName);
          }

          final deps = data['deps'] as List<dynamic>? ?? [];
          for (var depJson in deps) {
            try {
              final dep = depJson is String
                  ? Map<String, dynamic>.from(jsonDecode(depJson) as Map)
                  : Map<String, dynamic>.from(depJson as Map);
              final depFirst = dep['first'] as String?;
              final depLast = dep['last'] as String?;
              if (depFirst != null && depLast != null) {
                names.add('$depFirst $depLast');
              }
            } catch (e) {
              debugPrint('Error parsing dependent: $e');
            }
          }

          setState(() {
            _patientNames = names.isNotEmpty ? names : ['Patient'];
          });
        } else {
          setState(() {
            _patientNames = [user.displayName ?? 'Patient'];
          });
        }
      } else {
        setState(() {
          _patientNames = ['Patient'];
        });
      }
    } catch (e) {
      debugPrint('Error loading patient names: $e');
      if (mounted) setState(() => _patientNames = ['Patient']);
    }
  }

  void _generateAvailableTimeSlots() {
    final slots = <String>[];
    final now = DateTime.now();
    final isToday = _selectedDate != null &&
        _selectedDate!.year == now.year &&
        _selectedDate!.month == now.month &&
        _selectedDate!.day == now.day;

    final allSlots = [
      {'hour': 9, 'minute': 0, 'display': '9:00 AM'},
      {'hour': 9, 'minute': 30, 'display': '9:30 AM'},
      {'hour': 10, 'minute': 0, 'display': '10:00 AM'},
      {'hour': 10, 'minute': 30, 'display': '10:30 AM'},
      {'hour': 11, 'minute': 0, 'display': '11:00 AM'},
      {'hour': 11, 'minute': 30, 'display': '11:30 AM'},
      {'hour': 12, 'minute': 0, 'display': '12:00 PM'},
      {'hour': 12, 'minute': 30, 'display': '12:30 PM'},
      {'hour': 13, 'minute': 0, 'display': '1:00 PM'},
      {'hour': 13, 'minute': 30, 'display': '1:30 PM'},
      {'hour': 14, 'minute': 0, 'display': '2:00 PM'},
      {'hour': 14, 'minute': 30, 'display': '2:30 PM'},
      {'hour': 15, 'minute': 0, 'display': '3:00 PM'},
      {'hour': 15, 'minute': 30, 'display': '3:30 PM'},
      {'hour': 16, 'minute': 0, 'display': '4:00 PM'},
      {'hour': 16, 'minute': 30, 'display': '4:30 PM'},
    ];

    for (var slot in allSlots) {
      if (isToday) {
        final slotTime = DateTime(
          now.year,
          now.month,
          now.day,
          slot['hour'] as int,
          slot['minute'] as int,
        );
        final minimumTime = now.add(Duration(minutes: 30));
        if (slotTime.isAfter(minimumTime)) {
          slots.add(slot['display'] as String);
        }
      } else {
        slots.add(slot['display'] as String);
      }
    }

    if (!mounted) return;
    setState(() {
      _availableTimeSlots = slots;
    });
  }

  Future<void> _loadBookedTimeSlots() async {
    if (_selectedDate == null || _visitMode == null) return;

    try {
      final dateString = DateFormat('yyyy-MM-dd').format(_selectedDate!);
      QuerySnapshot snapshot;

      if (_visitMode == 'Clinic' && _selectedClinic != null) {
        snapshot = await FirebaseFirestore.instance
            .collection('requests')
            .where('appointmentDate', isGreaterThanOrEqualTo: dateString)
            .where('appointmentDate', isLessThan: dateString + 'T23:59:59')
            .where('visitMode', isEqualTo: 'Clinic')
            .where('clinic', isEqualTo: _selectedClinic)
            .where('status', whereIn: ['pending', 'confirmed']).get();
      } else if (_visitMode == 'Virtual') {
        snapshot = await FirebaseFirestore.instance
            .collection('requests')
            .where('appointmentDate', isGreaterThanOrEqualTo: dateString)
            .where('appointmentDate', isLessThan: dateString + 'T23:59:59')
            .where('visitMode', isEqualTo: 'Virtual')
            .where('status', whereIn: ['pending', 'confirmed']).get();
      } else {
        return;
      }

      final bookedSlots = <String>[];
      for (var doc in snapshot.docs) {
        if (_isRescheduleMode && doc.id == widget.rescheduleRequestId) {
          continue;
        }

        final data = doc.data() as Map<String, dynamic>;
        final timeSlot = data['appointmentTime'] as String?;
        if (timeSlot != null && timeSlot.isNotEmpty) {
          bookedSlots.add(timeSlot);
        }
      }

      if (!mounted) return;
      setState(() {
        _bookedTimeSlots = bookedSlots;
      });
    } catch (e) {
      debugPrint('Error loading booked time slots: $e');
    }
  }

  String _getEstimatedWaitTime() {
    if (_userHasKurvPass) {
      return '0-5 minutes';
    }
    final hour = DateTime.now().hour;
    if (hour < 10 || hour > 16) {
      return '15-30 minutes';
    } else if (hour >= 12 && hour <= 14) {
      return '45-60 minutes';
    } else {
      return '30-45 minutes';
    }
  }

  bool _isRefill() => _noAppointmentNeeded.contains(_selectedSymptom);

  bool _needsPhoto(String? symptom) {
    return symptom != null && _needsPhotoSymptoms.contains(symptom);
  }

  bool _needsSymptomsSteps() {
    return _selectedSymptom != null &&
        !_noSymptomsSteps.contains(_selectedSymptom) &&
        !_isRefill();
  }

  Future<void> _pickPhoto() async {
    HapticFeedback.selectionClick();
    final source = await showCupertinoModalPopup<ImageSource>(
      context: context,
      builder: (ctx) => CupertinoActionSheet(
        title: const Text('Add a Photo'),
        message: const Text('A clear, well-lit photo helps your provider.'),
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
    if (source == null || !mounted) return;
    try {
      final pickedFile = await _picker.pickImage(
        source: source,
        maxWidth: 1600,
        imageQuality: 85,
      );
      if (pickedFile == null) return;
      final bytes = await pickedFile.readAsBytes();
      if (!mounted) return;
      setState(() {
        _photoBytes = bytes;
        _photoUrl = pickedFile.path;
      });
      HapticFeedback.mediumImpact();
    } catch (e) {
      debugPrint('Error picking photo: $e');
      _toastError('We couldn\'t add that photo. Please try again.');
    }
  }

  bool _canProceedFromCurrentPage() {
    final pages = _buildPages();
    if (_pageIndex >= pages.length) return true;

    if (_visitType == null && _pageIndex == 0) return false;
    if (_visitType != null && _visitMode == null && _pageIndex == 1)
      return false;
    if (_visitMode == 'Clinic' && _selectedClinic == null && _pageIndex == 2)
      return false;

    if (_visitMode == 'Clinic' && _selectedClinic != null && _pageIndex == 3) {
      if (_selectedBeverage == 'Hot Tea' && _selectedTeaType == null) {
        return false;
      }
    }

    final patientPageIndex = _visitMode == 'Clinic' ? 4 : 2;
    if (_selectedPatient == null && _pageIndex == patientPageIndex)
      return false;

    final symptomPageIndex = _visitMode == 'Clinic' ? 5 : 3;
    if (_selectedSymptom == null && _pageIndex == symptomPageIndex)
      return false;

    if (_selectedSymptom != null) {
      if (_isRefill()) {
        if (_medicationCtrl.text.trim().isEmpty) {
          final medicationPageIndex = _visitMode == 'Clinic' ? 6 : 4;
          if (_pageIndex == medicationPageIndex) return false;
        }

        final refillMedicalHistoryIndex = _visitMode == 'Clinic' ? 7 : 5;
        if (_pageIndex == refillMedicalHistoryIndex) {
          if (_currentMedicationsCtrl.text.trim().isEmpty ||
              _allergiesCtrl.text.trim().isEmpty ||
              _primaryPhysicianCtrl.text.trim().isEmpty) {
            return false;
          }
        }
      } else {
        if (_needsSymptomsSteps()) {
          const durationOffset = 1;
          const detailsOffset = 2;
          const medicalHistoryOffset = 3;
          const lifestyleOffset = 4;
          final baseIndex = _visitMode == 'Clinic' ? 5 : 3;

          if (_symptomDuration == null &&
              _pageIndex == baseIndex + durationOffset) return false;
          if (_detailsCtrl.text.trim().isEmpty &&
              _pageIndex == baseIndex + detailsOffset) return false;

          if (_pageIndex == baseIndex + medicalHistoryOffset) {
            if (_currentMedicationsCtrl.text.trim().isEmpty ||
                _allergiesCtrl.text.trim().isEmpty ||
                _previousSurgeriesCtrl.text.trim().isEmpty ||
                _familyHistoryCtrl.text.trim().isEmpty ||
                _primaryPhysicianCtrl.text.trim().isEmpty) {
              return false;
            }
          }

          if (_pageIndex == baseIndex + lifestyleOffset) {
            if (_smokingStatus == null ||
                _alcoholConsumption == null ||
                _exerciseFrequency == null ||
                _dietaryRestrictionsCtrl.text.trim().isEmpty) {
              return false;
            }
          }
        } else {
          for (int i = 0; i < pages.length; i++) {
            final page = pages[i];
            if (page.key is ValueKey) {
              final key = (page.key as ValueKey).value;

              if (i == _pageIndex && key != 'timeStep' && key != 'photoStep') {
                final baseIndex = _visitMode == 'Clinic' ? 5 : 3;
                final medicalHistoryIndex = baseIndex + 1;

                if (i == medicalHistoryIndex) {
                  if (_currentMedicationsCtrl.text.trim().isEmpty ||
                      _allergiesCtrl.text.trim().isEmpty ||
                      _previousSurgeriesCtrl.text.trim().isEmpty ||
                      _familyHistoryCtrl.text.trim().isEmpty ||
                      _primaryPhysicianCtrl.text.trim().isEmpty) {
                    return false;
                  }
                }

                final lifestyleIndex = medicalHistoryIndex + 1;
                if (i == lifestyleIndex) {
                  if (_smokingStatus == null ||
                      _alcoholConsumption == null ||
                      _exerciseFrequency == null ||
                      _dietaryRestrictionsCtrl.text.trim().isEmpty) {
                    return false;
                  }
                }
              }
            }
          }
        }

        if (_needsPhoto(_selectedSymptom)) {
          for (int i = 0; i < pages.length; i++) {
            final pageKey = pages[i].key;
            if (pageKey is ValueKey &&
                pageKey.value == 'photoStep' &&
                i == _pageIndex) {
              return true;
            }
          }
        }

        for (int i = 0; i < pages.length; i++) {
          final pageKey = pages[i].key;
          if (pageKey is ValueKey &&
              pageKey.value == 'timeStep' &&
              i == _pageIndex) {
            return _selectedDate != null &&
                (_selectedTimeSlot != null || _selectedTime != null);
          }
        }
      }
    }

    return true;
  }

  void _nextPage() {
    HapticFeedback.lightImpact();

    if (!_canProceedFromCurrentPage()) {
      HapticFeedback.heavyImpact();

      String errorMessage = 'Please make a selection before proceeding';

      final pages = _buildPages();

      if (_visitMode == 'Clinic' &&
          _pageIndex == 3 &&
          _selectedBeverage == 'Hot Tea' &&
          _selectedTeaType == null) {
        errorMessage = 'Please select a tea type to continue';
      }

      if (_selectedSymptom != null && !_isRefill()) {
        if (_needsSymptomsSteps()) {
          const medicalHistoryOffset = 3;
          const lifestyleOffset = 4;
          final baseIndex = _visitMode == 'Clinic' ? 5 : 3;

          if (_pageIndex == baseIndex + medicalHistoryOffset) {
            errorMessage =
                'Please fill in all medical history fields. Write "None" if not applicable.';
          } else if (_pageIndex == baseIndex + lifestyleOffset) {
            errorMessage = 'Please answer all lifestyle questions';
          }
        } else {
          final baseIndex = _visitMode == 'Clinic' ? 5 : 3;
          final medicalHistoryIndex = baseIndex + 1;
          final lifestyleIndex = medicalHistoryIndex + 1;

          if (_pageIndex == medicalHistoryIndex) {
            errorMessage =
                'Please fill in all medical history fields. Write "None" if not applicable.';
          } else if (_pageIndex == lifestyleIndex) {
            errorMessage = 'Please answer all lifestyle questions';
          }
        }
      }

      if (_isRefill()) {
        final refillMedicalHistoryIndex = _visitMode == 'Clinic' ? 7 : 5;
        if (_pageIndex == refillMedicalHistoryIndex) {
          errorMessage =
              'Please fill in all medical information. Write "None" if not applicable.';
        }
      }

      if (!_isRefill()) {
        for (int i = 0; i < pages.length; i++) {
          final pageKey = pages[i].key;
          if (pageKey is ValueKey &&
              pageKey.value == 'timeStep' &&
              i == _pageIndex) {
            if (_selectedDate == null &&
                (_selectedTimeSlot == null && _selectedTime == null)) {
              errorMessage = 'Please select both date and time';
            } else if (_selectedDate == null) {
              errorMessage = 'Please select a date';
            } else if (_selectedTimeSlot == null && _selectedTime == null) {
              errorMessage = 'Please select a time';
            }
            break;
          }
        }
      }

      _toastError(errorMessage);
      return;
    }

    final pages = _buildPages();
    if (_pageIndex < pages.length - 1) {
      HapticFeedback.selectionClick();
      _pageController.nextPage(
        duration: _reduceMotion ? Duration.zero : _Motion.page,
        curve: _Motion.settle,
      );
    } else {
      if (_isRefill()) {
        _submitRefill();
      } else if (_isRescheduleMode) {
        _submitReschedule();
      } else {
        _showUpsellAndSubmit();
      }
    }
  }

  void _prevPage() {
    HapticFeedback.lightImpact();
    if (_pageIndex > 0) {
      _pageController.previousPage(
        duration: _reduceMotion ? Duration.zero : _Motion.page,
        curve: _Motion.settle,
      );
    } else if (_isRescheduleMode) {
      Navigator.of(context).pop();
    } else {
      // Step one's Cancel returns to the "Who's this for?" picker, which is
      // the front door of this flow — not out of the page entirely.
      _clearFlowMode();
    }
  }

  Future<bool> _processKurvPassPayment() async {
    try {
      setState(() => _isLoading = true);

      // Never create an anonymous account just to take a payment — a care
      // request needs the real, signed-in member behind it.
      final currentUser = FirebaseAuth.instance.currentUser;
      if (currentUser == null) {
        throw Exception('Please sign in to add Jovi Pass.');
      }

      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(currentUser.uid)
          .get();

      String? payarcCustomerId;
      String? cardLast4;

      if (userDoc.exists) {
        final userData = userDoc.data() as Map<String, dynamic>;
        payarcCustomerId = userData['payarcCustomerId'] as String?;
        cardLast4 = userData['cardLast4'] as String?;
      }

      bool useExistingCard = false;

      if (payarcCustomerId != null && cardLast4 != null) {
        useExistingCard = await showDialog<bool>(
              context: context,
              barrierDismissible: false,
              builder: (context) => CupertinoAlertDialog(
                title: const Text('Payment Method'),
                content: Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                      'Charge \$49.00 to your saved card ending in $cardLast4?'),
                ),
                actions: [
                  CupertinoDialogAction(
                    onPressed: () => Navigator.of(context).pop(false),
                    child: const Text('Use New Card'),
                  ),
                  CupertinoDialogAction(
                    isDefaultAction: true,
                    onPressed: () => Navigator.of(context).pop(true),
                    child: const Text('Use Saved Card'),
                  ),
                ],
              ),
            ) ??
            false;
      }

      Map<String, dynamic> paymentData;

      if (!useExistingCard) {
        final result = await showDialog<Map<String, String>>(
          context: context,
          barrierDismissible: false,
          builder: (context) => _CardInputDialog(),
        );

        if (result == null) {
          if (mounted) setState(() => _isLoading = false);
          return false;
        }

        final expiry =
            '${result['expMonth']!.padLeft(2, '0')}/${result['expYear']}';

        paymentData = {
          'amount': 49.00,
          'cardNumber': result['cardNumber']!,
          'expiry': expiry,
          'cvv': result['cvv']!,
          'firstName': _selectedPatient?.split(' ').first ?? 'Guest',
          'lastName': _selectedPatient?.split(' ').last ?? 'User',
          'email': currentUser.email ?? 'support@jovihealth.com',
          'phone': '',
          'subscriptionType': 'kurvpass',
          'userId': currentUser.uid,
          'isUpdate': false,
        };
      } else {
        paymentData = {
          'amount': 49.00,
          'payarcCustomerId': payarcCustomerId,
          'userId': currentUser.uid,
          'subscriptionType': 'kurvpass',
          'isUpdate': false,
        };
      }

      final functions = FirebaseFunctions.instance;
      final callable = functions.httpsCallable('processMembershipPayment');

      final result = await callable.call(paymentData);

      if (result.data['success'] == true) {
        if (result.data['payarcCustomerId'] != null) {
          await FirebaseFirestore.instance
              .collection('users')
              .doc(currentUser.uid)
              .update({
            'payarcCustomerId': result.data['payarcCustomerId'],
            'lastKurvPassPurchase': FieldValue.serverTimestamp(),
          });
        }

        if (mounted) setState(() => _isLoading = false);
        return true;
      } else {
        if (mounted) setState(() => _isLoading = false);
        _toastError((result.data['error'] as String?) ??
            'Payment failed. Please try again.');
        return false;
      }
    } catch (e) {
      debugPrint('Error processing payment: $e');
      if (mounted) setState(() => _isLoading = false);

      String errorMessage = 'Payment failed: ';
      if (e.toString().contains('firebase_functions/unauthenticated')) {
        errorMessage = 'Authentication failed. Please refresh and try again.';
      } else if (e.toString().contains('network')) {
        errorMessage = 'Network error. Please check your connection.';
      } else {
        errorMessage += e.toString();
      }

      _toastError(errorMessage);
      return false;
    }
  }

  Future<void> _submitReschedule() async {
    setState(() => _isLoading = true);
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('User not authenticated');
      }

      if (_existingRequest == null || widget.rescheduleRequestId == null) {
        throw Exception('No existing request found');
      }

      final dateString = _selectedDate != null
          ? DateFormat('yyyy-MM-dd').format(_selectedDate!) + 'T00:00:00'
          : '';

      await FirebaseFirestore.instance
          .collection('requests')
          .doc(widget.rescheduleRequestId)
          .update({
        'appointmentDate': dateString,
        'appointmentTime': _selectedTimeSlot ??
            (_selectedTime != null
                ? '${_selectedTime!.hour}:${_selectedTime!.minute.toString().padLeft(2, '0')}'
                : ''),
        'rescheduledAt': FieldValue.serverTimestamp(),
        'timezone': _localTimezoneId(),
        'status': 'pending',
      });

      debugPrint(
          '[RESCHEDULE] Appointment rescheduled: ${widget.rescheduleRequestId}');

      await _sendConfirmationEmail(widget.rescheduleRequestId!);

      if (!mounted) return;
      _autoSaveTimer?.cancel();
      setState(() {
        _isLoading = false;
        _showSuccess = true;
      });

      _animController.forward();
    } catch (e) {
      debugPrint('Error rescheduling appointment: $e');
      if (mounted) setState(() => _isLoading = false);
      _toastError('Failed to reschedule appointment: ${e.toString()}');
    }
  }

  Future<void> _sendConfirmationEmail(String requestId) async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        debugPrint('[EMAIL] No user authenticated');
        return;
      }

      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();

      final email = userDoc.data()?['email'] as String?;
      if (email == null || email.isEmpty) {
        debugPrint('[EMAIL] No email found for user');
        return;
      }

      final callable = FirebaseFunctions.instance
          .httpsCallable('sendAppointmentConfirmation');

      await callable.call({
        'email': email,
        'patientName': _selectedPatient,
        'visitType': _visitType,
        'visitMode': _visitMode,
        'symptom': _selectedSymptom,
        'appointmentDate': _selectedDate?.toIso8601String(),
        'appointmentTime': _selectedTimeSlot,
        'requestId': requestId,
        'clinic': _selectedClinic,
        'selectedBeverage': _selectedBeverage,
        'selectedTeaType': _selectedTeaType,
        'hasPriority': _userHasKurvPass,
      });

      debugPrint('[EMAIL] Appointment confirmation sent successfully');
    } catch (e) {
      debugPrint('[EMAIL ERROR] Failed to send confirmation email: $e');
    }
  }

  Future<void> _submitRequest() async {
    setState(() => _isLoading = true);
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('User not authenticated');
      }

      await _saveMedicalDataToFirebase();

      String? uploadedPhotoUrl;

      if (_photoBytes != null) {
        try {
          final storageRef = FirebaseStorage.instance
              .ref()
              .child('request_photos')
              .child('${_uuid.v4()}.jpg');

          final uploadTask = await storageRef.putData(
              _photoBytes!, SettableMetadata(contentType: 'image/jpeg'));
          uploadedPhotoUrl = await uploadTask.ref.getDownloadURL();
        } catch (e) {
          debugPrint('Error uploading photo: $e');
        }
      }

      final dateString = _selectedDate != null
          ? DateFormat('yyyy-MM-dd').format(_selectedDate!) + 'T00:00:00'
          : '';

      final requestData = {
        'id': _uuid.v4(),
        'userId': user.uid,
        // appointmentDate/appointmentTime are local wall-clock strings;
        // this tells the reminder function which clock they belong to.
        'timezone': _localTimezoneId(),
        'visitType': _visitType ?? '',
        'visitMode': _visitMode ?? '',
        'clinic': _selectedClinic ?? '',
        'patientName': _selectedPatient ?? '',
        'symptom': _selectedSymptom ?? '',
        'symptomDuration': _symptomDuration ?? '',
        'details': _detailsCtrl.text,
        'medication': _medicationCtrl.text,
        'selectedBeverage': _selectedBeverage ?? '',
        'selectedTeaType': _selectedTeaType ?? '',
        'currentMedications': _currentMedicationsCtrl.text,
        'allergies': _allergiesCtrl.text,
        'previousSurgeries': _previousSurgeriesCtrl.text,
        'familyMedicalHistory': _familyHistoryCtrl.text,
        'primaryPhysician': _primaryPhysicianCtrl.text,
        'smokingStatus': _smokingStatus ?? '',
        'alcoholConsumption': _alcoholConsumption ?? '',
        'exerciseFrequency': _exerciseFrequency ?? '',
        'dietaryRestrictions': _dietaryRestrictionsCtrl.text,
        'appointmentDate': dateString,
        'appointmentTime': _selectedTimeSlot ??
            (_selectedTime != null
                ? '${_selectedTime!.hour}:${_selectedTime!.minute.toString().padLeft(2, '0')}'
                : ''),
        'photoUrl': uploadedPhotoUrl ?? '',
        'status': 'pending',
        'priority': _userHasKurvPass,
        'kurvPassPurchased': _userHasKurvPass,
        'createdAt': FieldValue.serverTimestamp(),
        'estimatedWaitTime': _getEstimatedWaitTime(),
      };

      requestData.removeWhere((key, value) => value == null || value == '');

      final docRef = await FirebaseFirestore.instance
          .collection('requests')
          .add(requestData);

      debugPrint('[APPOINTMENT] Appointment saved with ID: ${docRef.id}');

      await _sendConfirmationEmail(docRef.id);

      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('visitType');
      await prefs.remove('visitMode');
      await prefs.remove('selectedPatient');
      await prefs.remove('selectedSymptom');
      await prefs.remove('symptomDuration');
      await prefs.remove('details');
      await prefs.remove('medication');
      await prefs.remove('selectedBeverage');
      await prefs.remove('selectedTeaType');

      if (!mounted) return;
      _autoSaveTimer?.cancel();
      setState(() {
        _isLoading = false;
        _showSuccess = true;
      });

      _animController.forward();
    } catch (e) {
      debugPrint('Error submitting request: $e');
      if (mounted) setState(() => _isLoading = false);
      _toastError('Failed to submit request: ${e.toString()}');
    }
  }

  Future<void> _submitRefill() async {
    setState(() => _isLoading = true);
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('User not authenticated');
      }

      await _saveMedicalDataToFirebase();

      final refillData = {
        'id': _uuid.v4(),
        'userId': user.uid,
        'patientName': _selectedPatient ?? '',
        'medicationType': _selectedSymptom ?? '',
        'medicationName': _medicationCtrl.text,
        'currentMedications': _currentMedicationsCtrl.text,
        'allergies': _allergiesCtrl.text,
        'primaryPhysician': _primaryPhysicianCtrl.text,
        'status': 'pending',
        'type': 'refill',
        'createdAt': FieldValue.serverTimestamp(),
      };

      refillData.removeWhere((key, value) => value == null || value == '');

      await FirebaseFirestore.instance.collection('refills').add(refillData);

      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('visitType');
      await prefs.remove('visitMode');
      await prefs.remove('selectedPatient');
      await prefs.remove('selectedSymptom');
      await prefs.remove('medication');

      if (!mounted) return;
      _autoSaveTimer?.cancel();
      setState(() {
        _isLoading = false;
        _showSuccess = true;
      });

      _animController.forward();
    } catch (e) {
      debugPrint('Error submitting refill: $e');
      if (mounted) setState(() => _isLoading = false);
      _toastError('Error submitting refill: ${e.toString()}');
    }
  }

  Future<void> _showUpsellAndSubmit() async {
    final shouldUpsell = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: BackdropFilter(
            filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
            child: Container(
              constraints: BoxConstraints(
                maxWidth: layoutSettings.wideMode ? 600 : double.infinity,
              ),
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                color: joviNavy.withOpacity(0.92),
                border: Border.all(
                  color: Colors.white.withOpacity(0.12),
                  width: 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.35),
                    blurRadius: 30,
                    offset: Offset(0, 15),
                  ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Jovi Pass badge (replaces the old Kurv Pass logo).
                  Container(
                    width: 84,
                    height: 84,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [joviCoral, joviCoralDark],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: joviCoral.withOpacity(0.4),
                          blurRadius: 20,
                          offset: Offset(0, 8),
                        ),
                      ],
                    ),
                    child: Icon(Icons.flash_on, color: Colors.white, size: 40),
                  ),
                  SizedBox(height: layoutSettings.paddingV),
                  Text(
                    'Skip the Wait!',
                    style: TextStyle(
                      fontSize: layoutSettings.wideMode ? 30 : 28,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 12),
                  Container(
                    padding: EdgeInsets.symmetric(
                        horizontal: layoutSettings.paddingH * 0.8,
                        vertical: layoutSettings.paddingV * 0.4),
                    decoration: BoxDecoration(
                      color: joviMint.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: joviMint.withOpacity(0.4)),
                    ),
                    child: Text(
                      'Jovi Pass · \$49 one-time',
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize + 5,
                        fontWeight: FontWeight.bold,
                        color: joviMint,
                      ),
                    ),
                  ),
                  SizedBox(height: layoutSettings.paddingV),
                  Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH),
                    decoration: BoxDecoration(
                      color: joviGold.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: joviGold.withOpacity(0.35)),
                    ),
                    child: Column(
                      children: [
                        Icon(Icons.speed, color: joviGold, size: 32),
                        SizedBox(height: 8),
                        Text(
                          'Jovi Pass Priority',
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 3,
                            fontWeight: FontWeight.w700,
                            color: joviGold,
                            letterSpacing: -0.2,
                          ),
                        ),
                        SizedBox(height: 8),
                        Text(
                          '✓ See the doctor immediately\n'
                          '✓ No waiting in line\n'
                          '✓ Priority service for this visit',
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 1,
                            height: 1.5,
                            color: Colors.white.withOpacity(0.9),
                          ),
                        ),
                      ],
                    ),
                  ),
                  SizedBox(height: layoutSettings.paddingV),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.of(context).pop(false),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white.withOpacity(0.9),
                            padding: EdgeInsets.symmetric(
                                vertical: layoutSettings.paddingV * 0.7),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            side: BorderSide(
                                color: Colors.white.withOpacity(0.3)),
                          ),
                          child: Text(
                            'No Thanks',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.9),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                      SizedBox(width: layoutSettings.paddingH * 0.8),
                      Expanded(
                        flex: 2,
                        child: ElevatedButton(
                          onPressed: () => Navigator.of(context).pop(true),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: joviCoral,
                            foregroundColor: Colors.white,
                            padding: EdgeInsets.symmetric(
                                vertical: layoutSettings.paddingV * 0.7),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            elevation: 3,
                            shadowColor: joviCoral.withOpacity(0.5),
                          ),
                          child: Text(
                            'Get Jovi Pass',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: layoutSettings.actionTextSize + 3,
                              color: Colors.white,
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
    );

    if (!mounted) return;
    if (shouldUpsell == true) {
      final paymentSuccess = await _processKurvPassPayment();
      if (!mounted) return;
      if (paymentSuccess) {
        setState(() => _userHasKurvPass = true);
        _submitRequest();
      }
    } else {
      _submitRequest();
    }
  }

  Widget _buildBeverageSelectionPage() {
    return _buildStep(
      icon: Icons.local_cafe,
      title: 'Complimentary Beverage',
      subtitle:
          'Would you like a complimentary beverage ready for your arrival?',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: EdgeInsets.all(layoutSettings.paddingH),
            margin: EdgeInsets.only(bottom: layoutSettings.paddingV),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  joviCoral.withOpacity(0.15),
                  joviCoralLight.withOpacity(0.10),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: joviCoral.withOpacity(0.35)),
            ),
            child: Row(
              children: [
                Container(
                  padding: EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: joviCoral.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    Icons.coffee,
                    color: joviCoral,
                    size: layoutSettings.actionIconDimension,
                  ),
                ),
                SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Complimentary Service',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 3,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Your beverage will be prepared and waiting for you at the clinic',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 1,
                          color: Colors.white.withOpacity(0.75),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          _buildBeverageOption(
            'No beverage',
            'I don\'t need a beverage',
            Icons.block,
            Colors.white.withOpacity(0.5),
            null,
          ),
          SizedBox(height: layoutSettings.paddingV * 0.8),
          _buildBeverageOption(
            'Premium Water',
            'Refreshing Fiji Water',
            Icons.water_drop,
            joviMint,
            'Premium Water',
          ),
          SizedBox(height: layoutSettings.paddingV * 0.8),
          _buildBeverageOption(
            'Hot Tea',
            'Select from our tea collection',
            Icons.local_cafe,
            joviCoral,
            'Hot Tea',
          ),
          if (_selectedBeverage == 'Hot Tea') ...[
            SizedBox(height: layoutSettings.paddingV),
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.07),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: joviCoral.withOpacity(0.35)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Select your tea',
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 3,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children:
                        _teaOptions.map((tea) => _buildTeaChip(tea)).toList(),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildBeverageOption(
    String title,
    String subtitle,
    IconData icon,
    Color color,
    String? beverageValue,
  ) {
    final isSelected = _selectedBeverage == beverageValue ||
        (beverageValue == null && _selectedBeverage == null);

    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() {
          _selectedBeverage = beverageValue;
          if (beverageValue != 'Hot Tea') {
            _selectedTeaType = null;
          }
        });
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        padding: EdgeInsets.all(layoutSettings.paddingH),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [color.withOpacity(0.8), color],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? color : Colors.white.withOpacity(0.15),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: isSelected
                  ? color.withOpacity(0.3)
                  : Colors.black.withOpacity(0.15),
              blurRadius: isSelected ? 20 : 10,
              offset: Offset(0, isSelected ? 8 : 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isSelected
                    ? Colors.white.withOpacity(0.2)
                    : color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon,
                  color: isSelected ? Colors.white : color,
                  size: layoutSettings.actionIconDimension),
            ),
            SizedBox(width: layoutSettings.paddingH * 0.8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 5,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 1,
                      color: isSelected
                          ? Colors.white.withOpacity(0.9)
                          : Colors.white.withOpacity(0.6),
                    ),
                  ),
                ],
              ),
            ),
            if (isSelected)
              Icon(Icons.check_circle,
                  color: Colors.white,
                  size: layoutSettings.actionIconDimension),
          ],
        ),
      ),
    );
  }

  Widget _buildTeaChip(String tea) {
    final isSelected = _selectedTeaType == tea;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _selectedTeaType = tea);
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        padding: EdgeInsets.symmetric(
            horizontal: layoutSettings.paddingH * 0.8,
            vertical: layoutSettings.paddingV * 0.5),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [joviCoral, joviCoralDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? joviCoral : joviCoral.withOpacity(0.4),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Text(
          tea,
          style: TextStyle(
            color: isSelected ? Colors.white : joviCoralLight,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
            fontSize: layoutSettings.actionTextSize + 1,
          ),
        ),
      ),
    );
  }

  List<Widget> _buildPages() {
    List<Widget> pages = [];

    if (_isRescheduleMode && _selectedSymptom != null && !_isRefill()) {
      pages.add(_buildDateTimeStep());
      return pages;
    }

    final symptoms =
        _visitType != null ? (_symptomsByType[_visitType] ?? []) : <String>[];
    final reasonTitle =
        _visitType == 'Wellness' ? 'Wellness goal?' : 'Current symptom/reason?';
    final durationTitle =
        _visitType == 'Wellness' ? 'How long pursuing?' : 'How long?';
    final detailsTitle =
        _visitType == 'Wellness' ? 'More about your goals' : 'More details';

    pages.add(_buildStep(
      icon: Icons.medical_services,
      title: 'Select Visit Type',
      subtitle: 'What kind of care do you need?',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildVisitTypeCard('Urgent Care', Icons.local_hospital,
              'Immediate care for non-emergency conditions', Color(0xFFE53935)),
          SizedBox(height: layoutSettings.paddingV * 0.8),
          _buildVisitTypeCard('Primary Care', Icons.favorite,
              'Routine check-ups and ongoing care', joviCoral),
          SizedBox(height: layoutSettings.paddingV * 0.8),
          _buildVisitTypeCard('Wellness', Icons.spa,
              'Preventive care and lifestyle management', joviMint),
        ],
      ),
    ));

    if (_visitType != null) {
      pages.add(_buildStep(
        icon: Icons.location_on,
        title: 'Choose Visit Mode',
        subtitle: 'How would you like to be seen?',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildModeCard(
                'Clinic', Icons.business, 'Visit our physical location', true),
            SizedBox(height: layoutSettings.paddingV * 0.8),
            _buildModeCard('Virtual', Icons.video_call,
                'Connect from home via video', false),
          ],
        ),
      ));
    }

    if (_visitMode == 'Clinic') {
      pages.add(_buildStep(
        icon: Icons.place,
        title: 'Select Clinic Location',
        subtitle: 'Choose your preferred clinic',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: _clinicLocations.keys
              .map((clinic) =>
                  _buildClinicCard(clinic, _clinicLocations[clinic]!))
              .toList(),
        ),
      ));

      if (_selectedClinic != null) {
        pages.add(_buildBeverageSelectionPage());
      }
    }

    if (_visitMode != null &&
        (_visitMode != 'Clinic' || _selectedClinic != null)) {
      // If a patient was already picked from the profile picker, show a
      // confirmation card instead of the full patient selector. Users still
      // see the step (keeping all downstream page indices intact), but they
      // get a calmer "this visit is for..." moment rather than a list of
      // family members where theirs is already highlighted.
      final hasPreselectedPatient =
          _selectedPatient != null && _selectedPatient!.isNotEmpty;
      pages.add(_buildStep(
        icon: Icons.person,
        title: hasPreselectedPatient ? 'Confirm Patient' : 'Select Patient',
        subtitle: hasPreselectedPatient
            ? 'This visit is for the person below. Tap Edit if you need to change it.'
            : 'Who is this appointment for?',
        child: hasPreselectedPatient
            ? _buildPreselectedPatientCard(_selectedPatient!)
            : Column(
                children: _patientNames
                    .map((name) => _buildPatientCard(name))
                    .toList(),
              ),
      ));
    }

    if (_selectedPatient != null && symptoms.isNotEmpty) {
      // Derived every build so an empty result set stays empty (it used to
      // snap back to the full list) and a visit-type change refreshes it.
      _filteredSymptoms = _symptomSearchQuery.isEmpty
          ? List<String>.from(symptoms)
          : symptoms
              .where((s) => s.toLowerCase().contains(_symptomSearchQuery))
              .toList();

      pages.add(_buildStep(
        icon: Icons.healing,
        title: reasonTitle,
        subtitle: 'Select or search for your primary concern',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withOpacity(0.15)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    blurRadius: 10,
                    offset: Offset(0, 2),
                  ),
                ],
              ),
              child: TextField(
                controller: _symptomSearchController,
                textInputAction: TextInputAction.search,
                style: TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'Search symptoms',
                  hintStyle: TextStyle(color: Colors.white.withOpacity(0.5)),
                  prefixIcon: Icon(Icons.search, color: joviCoral),
                  suffixIcon: _symptomSearchQuery.isNotEmpty
                      ? IconButton(
                          icon: Icon(Icons.clear,
                              color: Colors.white.withOpacity(0.6)),
                          onPressed: () {
                            setState(() {
                              _symptomSearchController.clear();
                              _symptomSearchQuery = '';
                            });
                          },
                        )
                      : null,
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.symmetric(
                      horizontal: layoutSettings.paddingH * 0.8,
                      vertical: layoutSettings.paddingV * 0.7),
                ),
                onChanged: (value) => setState(
                    () => _symptomSearchQuery = value.trim().toLowerCase()),
              ),
            ),
            SizedBox(height: layoutSettings.paddingV),
            if (_suggestedSymptoms.isNotEmpty &&
                _symptomSearchQuery.isEmpty) ...[
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      joviCoral.withOpacity(0.12),
                      joviCoralDark.withOpacity(0.08),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: joviCoral.withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.history, color: joviCoral, size: 20),
                        SizedBox(width: 8),
                        Text(
                          'Recent symptoms',
                          style: TextStyle(
                              fontSize: layoutSettings.actionTextSize + 1,
                              color: Colors.white,
                              fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                    SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _suggestedSymptoms
                          .map((symptom) => _buildSuggestedSymptomChip(symptom))
                          .toList(),
                    ),
                  ],
                ),
              ),
              SizedBox(height: layoutSettings.paddingV),
            ],
            if (_filteredSymptoms.isEmpty) ...[
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withOpacity(0.12)),
                ),
                child: Column(
                  children: [
                    Icon(Icons.search_off,
                        size: 48, color: Colors.white.withOpacity(0.3)),
                    SizedBox(height: 12),
                    Text(
                      'No symptoms found',
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize + 3,
                        fontWeight: FontWeight.w600,
                        color: Colors.white.withOpacity(0.7),
                      ),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Try searching with different keywords',
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize + 1,
                        color: Colors.white.withOpacity(0.5),
                      ),
                    ),
                  ],
                ),
              ),
            ] else ...[
              Container(
                constraints: BoxConstraints(maxHeight: 400),
                child: SingleChildScrollView(
                  child: Column(
                    children: [
                      if (_symptomSearchQuery.isNotEmpty) ...[
                        Container(
                          padding:
                              EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          child: Row(
                            children: [
                              Text(
                                '${_filteredSymptoms.length} result${_filteredSymptoms.length == 1 ? '' : 's'} found',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 1,
                                  color: Colors.white.withOpacity(0.6),
                                ),
                              ),
                            ],
                          ),
                        ),
                        SizedBox(height: 8),
                      ],
                      ..._filteredSymptoms
                          .map((symptom) => _buildSymptomCard(symptom))
                          .toList(),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ));
    }

    if (_selectedSymptom != null && _isRefill()) {
      pages.add(_buildStep(
        icon: Icons.medication,
        title: 'Medication Details',
        subtitle: 'What medication needs refilling?',
        child: _buildStyledTextField(
          _medicationCtrl,
          'Medication Name',
          'Enter the exact name as it appears on your prescription',
          Icons.medical_services,
        ),
      ));

      pages.add(_buildStep(
        icon: Icons.medical_information,
        title: 'Medical History',
        subtitle: 'Review your medical information for safe refills',
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_currentMedicationsCtrl.text.isNotEmpty ||
                  _allergiesCtrl.text.isNotEmpty ||
                  _primaryPhysicianCtrl.text.isNotEmpty) ...[
                Container(
                  padding: EdgeInsets.all(12),
                  margin:
                      EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
                  decoration: BoxDecoration(
                    color: joviMint.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: joviMint.withOpacity(0.4)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: joviMint, size: 20),
                      SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Medical information loaded from your profile',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: layoutSettings.actionTextSize,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Please review and update if needed',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.7),
                                fontSize: layoutSettings.actionTextSize - 1,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ] else ...[
                Container(
                  padding: EdgeInsets.all(12),
                  margin:
                      EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
                  decoration: BoxDecoration(
                    color: joviGold.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: joviGold.withOpacity(0.4)),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, color: joviGold, size: 20),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'All fields are required for medication safety',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: layoutSettings.actionTextSize,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              _buildStyledTextField(
                _currentMedicationsCtrl,
                'Current Medications *',
                'List all medications (or write "None" if not taking any)',
                Icons.medication,
                maxLines: 3,
                isRequired: true,
              ),
              SizedBox(height: layoutSettings.paddingV * 0.8),
              _buildStyledTextField(
                _allergiesCtrl,
                'Allergies *',
                'Drug, food, environmental (or write "None" if no allergies)',
                Icons.warning_amber,
                maxLines: 2,
                isRequired: true,
              ),
              SizedBox(height: layoutSettings.paddingV * 0.8),
              _buildStyledTextField(
                _primaryPhysicianCtrl,
                'Primary Care Physician *',
                'Doctor name and clinic (or write "None" if no PCP)',
                Icons.person,
                isRequired: true,
              ),
              SizedBox(height: layoutSettings.paddingV),
              OutlinedButton.icon(
                onPressed: () async {
                  _medicalDirty = true;
                  await _saveMedicalDataToFirebase();
                  HapticFeedback.mediumImpact();
                  _toast('Medical information saved to your profile',
                      accent: joviMint, icon: CupertinoIcons.checkmark_circle);
                },
                icon: Icon(Icons.save_outlined, size: 18),
                label: Text('Save Updates to Profile'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: joviCoral,
                  padding: EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  side: BorderSide(color: joviCoral.withOpacity(0.6)),
                ),
              ),
            ],
          ),
        ),
      ));
    }

    if (_selectedSymptom != null && _needsSymptomsSteps()) {
      pages.add(_buildStep(
        icon: Icons.schedule,
        title: durationTitle,
        subtitle: 'How long have you been experiencing this?',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildDurationCard('Less Than 24 Hours', Icons.hourglass_top,
                'Just started recently', joviGold),
            SizedBox(height: layoutSettings.paddingV * 0.8),
            _buildDurationCard('More Than 24 Hours', Icons.hourglass_bottom,
                'Ongoing for a while', joviCoralDark),
          ],
        ),
      ));

      pages.add(_buildStep(
        icon: Icons.description,
        title: detailsTitle,
        subtitle: 'Help us understand your situation better',
        child: _buildStyledTextField(
          _detailsCtrl,
          'Describe your symptoms',
          'The more details you provide, the better we can help',
          Icons.edit_note,
          maxLines: 5,
        ),
      ));
    }

    if (_selectedSymptom != null && !_isRefill()) {
      pages.add(_buildStep(
        icon: Icons.medical_information,
        title: 'Medical History',
        subtitle: 'All fields are required for your safety',
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: EdgeInsets.all(12),
                margin: EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
                decoration: BoxDecoration(
                  color: joviGold.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: joviGold.withOpacity(0.4)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: joviGold, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'All fields are required to ensure safe and effective care',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: layoutSettings.actionTextSize,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              _buildStyledTextField(
                _currentMedicationsCtrl,
                'Current Medications *',
                'List all medications (or write "None" if not taking any)',
                Icons.medication,
                maxLines: 3,
                isRequired: true,
              ),
              SizedBox(height: layoutSettings.paddingV * 0.8),
              _buildStyledTextField(
                _allergiesCtrl,
                'Allergies *',
                'Drug, food, environmental (or write "None" if no allergies)',
                Icons.warning_amber,
                maxLines: 2,
                isRequired: true,
              ),
              SizedBox(height: layoutSettings.paddingV * 0.8),
              _buildStyledTextField(
                _previousSurgeriesCtrl,
                'Previous Surgeries *',
                'List surgeries/procedures (or write "None" if never had surgery)',
                Icons.local_hospital,
                maxLines: 2,
                isRequired: true,
              ),
              SizedBox(height: layoutSettings.paddingV * 0.8),
              _buildStyledTextField(
                _familyHistoryCtrl,
                'Family Medical History *',
                'Diabetes, heart disease, cancer, etc. (or write "None")',
                Icons.family_restroom,
                maxLines: 3,
                isRequired: true,
              ),
              SizedBox(height: layoutSettings.paddingV * 0.8),
              _buildStyledTextField(
                _primaryPhysicianCtrl,
                'Primary Care Physician *',
                'Doctor name and clinic (or write "None" if no PCP)',
                Icons.person,
                isRequired: true,
              ),
            ],
          ),
        ),
      ));

      pages.add(_buildStep(
        icon: Icons.favorite_border,
        title: 'Lifestyle Information',
        subtitle: 'Your daily habits affect your health',
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: EdgeInsets.all(12),
                margin: EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
                decoration: BoxDecoration(
                  color: joviMint.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: joviMint.withOpacity(0.35)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.check_circle_outline, color: joviMint, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Please answer all questions honestly for accurate care',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: layoutSettings.actionTextSize,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        'Smoking Status',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 3,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                      Text(
                        ' *',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 3,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFE53935),
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 12),
                  ..._buildRadioOptions(
                    'smoking',
                    [
                      'Never smoked',
                      'Former smoker',
                      'Current smoker',
                      'Vaping/E-cigarettes'
                    ],
                    _smokingStatus,
                    (value) => setState(() {
                      _smokingStatus = value;
                      _medicalDirty = true;
                    }),
                  ),
                ],
              ),
              SizedBox(height: layoutSettings.paddingV),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        'Alcohol Consumption',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 3,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                      Text(
                        ' *',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 3,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFE53935),
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 12),
                  ..._buildRadioOptions(
                    'alcohol',
                    [
                      'None',
                      'Occasional (1-2 drinks/week)',
                      'Moderate (3-7 drinks/week)',
                      'Heavy (>7 drinks/week)'
                    ],
                    _alcoholConsumption,
                    (value) => setState(() {
                      _alcoholConsumption = value;
                      _medicalDirty = true;
                    }),
                  ),
                ],
              ),
              SizedBox(height: layoutSettings.paddingV),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        'Exercise Frequency',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 3,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                      Text(
                        ' *',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 3,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFE53935),
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 12),
                  ..._buildRadioOptions(
                    'exercise',
                    [
                      'No regular exercise',
                      '1-2 times/week',
                      '3-4 times/week',
                      '5+ times/week'
                    ],
                    _exerciseFrequency,
                    (value) => setState(() {
                      _exerciseFrequency = value;
                      _medicalDirty = true;
                    }),
                  ),
                ],
              ),
              SizedBox(height: layoutSettings.paddingV),
              _buildStyledTextField(
                _dietaryRestrictionsCtrl,
                'Dietary Restrictions *',
                'Vegetarian, allergies, etc. (or write "None")',
                Icons.restaurant_menu,
                maxLines: 2,
                isRequired: true,
              ),
            ],
          ),
        ),
      ));
    }

    if (_selectedSymptom != null && _needsPhoto(_selectedSymptom)) {
      pages.add(_buildStep(
        key: ValueKey('photoStep'),
        icon: Icons.camera_alt,
        title: 'Upload Photo',
        subtitle: 'A photo helps providers assess your condition',
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_photoBytes != null)
              Container(
                height: 250,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  image: DecorationImage(
                    image: MemoryImage(_photoBytes!),
                    fit: BoxFit.cover,
                  ),
                ),
              )
            else
              Container(
                height: 200,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.15),
                    width: 2,
                  ),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.add_a_photo,
                        size: 60, color: Colors.white.withOpacity(0.35)),
                    SizedBox(height: 12),
                    Text(
                      'No photo uploaded',
                      style: TextStyle(color: Colors.white.withOpacity(0.7)),
                    ),
                  ],
                ),
              ),
            SizedBox(height: layoutSettings.paddingV),
            ElevatedButton.icon(
              icon: Icon(Icons.camera_alt),
              label:
                  Text(_photoBytes != null ? 'Change Photo' : 'Add Photo'),
              onPressed: _pickPhoto,
              style: ElevatedButton.styleFrom(
                backgroundColor: joviCoral,
                foregroundColor: Colors.white,
                padding: EdgeInsets.symmetric(
                    vertical: layoutSettings.paddingV * 0.8),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ],
        ),
      ));
    }

    if (_selectedSymptom != null && !_isRefill()) {
      pages.add(_buildDateTimeStep());
    }

    if ((_selectedSymptom != null &&
            _isRefill() &&
            _medicationCtrl.text.isNotEmpty) ||
        (_selectedSymptom != null &&
            !_isRefill() &&
            _selectedDate != null &&
            (_selectedTimeSlot != null || _selectedTime != null))) {
      pages.add(_buildConfirmationPage());
    }

    return pages;
  }

  Widget _buildDateTimeStep() {
    return _buildStep(
      key: ValueKey('timeStep'),
      icon: Icons.calendar_today,
      title:
          _isRescheduleMode ? 'Reschedule Appointment' : 'Schedule Appointment',
      subtitle: _isRescheduleMode
          ? 'Choose your new preferred date and time'
          : 'Choose your preferred date and time',
      child: Column(
        children: [
          if (_isRescheduleMode && _existingRequest != null) ...[
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              margin: EdgeInsets.only(bottom: layoutSettings.paddingV),
              decoration: BoxDecoration(
                color: joviGold.withOpacity(0.12),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: joviGold.withOpacity(0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.schedule, color: joviGold, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Current Appointment',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 3,
                          fontWeight: FontWeight.w600,
                          color: joviGold,
                        ),
                      ),
                    ],
                  ),
                  SizedBox(height: 8),
                  if (_existingRequest!.data() != null) ...[
                    Builder(
                      builder: (context) {
                        final data =
                            _existingRequest!.data() as Map<String, dynamic>;
                        final dateStr = data['appointmentDate'] as String?;
                        final timeStr = data['appointmentTime'] as String?;

                        DateTime? currentDate;
                        if (dateStr != null) {
                          try {
                            currentDate = DateTime.parse(dateStr.split('T')[0]);
                          } catch (e) {
                            debugPrint('Error parsing date: $e');
                          }
                        }

                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (currentDate != null)
                              Text(
                                'Date: ${DateFormat.yMMMMEEEEd().format(currentDate)}',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 1,
                                  color: Colors.white.withOpacity(0.85),
                                ),
                              ),
                            if (timeStr != null && timeStr.isNotEmpty)
                              Text(
                                'Time: $timeStr',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 1,
                                  color: Colors.white.withOpacity(0.85),
                                ),
                              ),
                          ],
                        );
                      },
                    ),
                  ],
                ],
              ),
            ),
          ],
          Container(
            padding: EdgeInsets.all(layoutSettings.paddingH),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  joviCoral.withOpacity(0.12),
                  joviCoralDark.withOpacity(0.08),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: joviCoral.withOpacity(0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.flash_on, color: joviCoral, size: 20),
                    SizedBox(width: 8),
                    Text(
                      'Quick Selection',
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize + 3,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _buildQuickActionButton(
                        'Next Available',
                        Icons.schedule,
                        () => _selectNextAvailable(),
                      ),
                    ),
                    SizedBox(width: 12),
                    Expanded(
                      child: _buildQuickActionButton(
                        'Tomorrow',
                        Icons.wb_sunny,
                        () => _selectTomorrow(),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          SizedBox(height: layoutSettings.paddingV),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Select Date',
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 5,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
          ),
          SizedBox(height: 12),
          Container(
            height: 320,
            padding: EdgeInsets.all(layoutSettings.paddingH),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.07),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withOpacity(0.12)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.15),
                  blurRadius: 10,
                  offset: Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      DateFormat.yMMMM().format(_calendarMonth),
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize + 5,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    Row(
                      children: [
                        IconButton(
                          onPressed: () => _changeMonth(-1),
                          icon: Icon(Icons.chevron_left, color: joviCoral),
                          constraints:
                              BoxConstraints(minWidth: 44, minHeight: 44),
                        ),
                        IconButton(
                          onPressed: () => _changeMonth(1),
                          icon: Icon(Icons.chevron_right, color: joviCoral),
                          constraints:
                              BoxConstraints(minWidth: 44, minHeight: 44),
                        ),
                      ],
                    ),
                  ],
                ),
                SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: ['M', 'T', 'W', 'T', 'F', 'S', 'S']
                      .map((day) => Container(
                            width: 36,
                            child: Text(
                              day,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: Colors.white.withOpacity(0.6),
                              ),
                            ),
                          ))
                      .toList(),
                ),
                SizedBox(height: 8),
                Expanded(
                  child: _buildCalendarGrid(),
                ),
              ],
            ),
          ),
          if (_selectedDate != null) ...[
            SizedBox(height: layoutSettings.paddingV),
            Row(
              children: [
                Text(
                  'Select Time',
                  style: TextStyle(
                    fontSize: layoutSettings.actionTextSize + 5,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                SizedBox(width: 12),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _availableTimeSlots.isEmpty
                        ? Color(0xFFE53935).withOpacity(0.2)
                        : joviMint.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    _availableTimeSlots.isEmpty
                        ? 'Fully Booked'
                        : '${_openSlotCount()} slots available',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: _availableTimeSlots.isEmpty
                          ? Color(0xFFE53935)
                          : joviMint,
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: layoutSettings.paddingV * 0.8),
            if (_availableTimeSlots.isEmpty)
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  color: joviGold.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: joviGold.withOpacity(0.4)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: joviGold),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        _selectedDate!.year == DateTime.now().year &&
                                _selectedDate!.month == DateTime.now().month &&
                                _selectedDate!.day == DateTime.now().day
                            ? 'No more appointments available today. Please select tomorrow.'
                            : 'All time slots are booked for this date. Please select another date.',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: layoutSettings.actionTextSize + 1,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            else if (_openSlotCount() == 0)
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  color: joviGold.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: joviGold.withOpacity(0.4)),
                ),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: joviGold),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'All time slots are booked for this date. Please select another date.',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: layoutSettings.actionTextSize + 1,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            else ...[
              Container(
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.06),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withOpacity(0.10)),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: _buildTimeGroupTab(
                        'Morning',
                        Icons.wb_sunny_outlined,
                        true,
                      ),
                    ),
                    Expanded(
                      child: _buildTimeGroupTab(
                        'Afternoon',
                        Icons.wb_twilight,
                        false,
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: layoutSettings.paddingV * 0.8),
              _buildTimeSlotGrid(),
            ],
          ] else ...[
            SizedBox(height: layoutSettings.paddingV * 0.8),
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                color: joviCoral.withOpacity(0.10),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: joviCoral.withOpacity(0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, color: joviCoral, size: 20),
                  SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Please select a date first',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: layoutSettings.actionTextSize + 1,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Note: We are closed on Sundays',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.65),
                            fontSize: layoutSettings.actionTextSize,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (_selectedDate != null && _selectedTimeSlot != null) ...[
            SizedBox(height: layoutSettings.paddingV),
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [joviCoral, joviCoralDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: joviCoral.withOpacity(0.35),
                    blurRadius: 16,
                    offset: Offset(0, 6),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Icon(Icons.check_circle, color: Colors.white, size: 24),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _isRescheduleMode
                              ? 'New Appointment Time'
                              : 'Appointment Scheduled',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: layoutSettings.actionTextSize + 1,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          '${DateFormat.MMMMEEEEd().format(_selectedDate!)} at $_selectedTimeSlot',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.95),
                            fontSize: layoutSettings.actionTextSize + 3,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
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

  Widget _buildConfirmationPage() {
    final isRefill = _isRefill();
    final timeStr = _selectedTimeSlot ??
        (_selectedTime != null ? _selectedTime!.format(context) : '');

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [joviNavy, joviNavyDark],
        ),
      ),
      child: SingleChildScrollView(
        padding: _getAdaptivePadding(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ScaleTransition(
              scale: _scaleAnim,
              child: Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [joviCoral, joviCoralDark],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: joviCoral.withOpacity(0.4),
                      blurRadius: 24,
                      offset: Offset(0, 10),
                    ),
                  ],
                ),
                child: Icon(
                  isRefill
                      ? Icons.medication
                      : _isRescheduleMode
                          ? Icons.schedule_send
                          : Icons.check_circle,
                  size: 60,
                  color: Colors.white,
                ),
              ),
            ),
            SizedBox(height: layoutSettings.paddingV * 1.6),
            Text(
              _isRescheduleMode ? 'Confirm Reschedule' : 'Review & Confirm',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: layoutSettings.wideMode ? 30 : 28,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            SizedBox(height: 8),
            Text(
              _isRescheduleMode
                  ? 'Please confirm your new appointment time'
                  : 'Please review your information before submitting',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 2,
                color: Colors.white.withOpacity(0.7),
              ),
            ),
            SizedBox(height: layoutSettings.paddingV),
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.07),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white.withOpacity(0.12)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.15),
                    blurRadius: 10,
                    offset: Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildConfirmationRow('Type:', _visitType ?? ''),
                  _buildConfirmationRow('Mode:', _visitMode ?? ''),
                  if (_selectedClinic != null)
                    _buildConfirmationRow('Clinic:', _selectedClinic!),
                  if (_selectedBeverage != null)
                    _buildConfirmationRow(
                      'Beverage:',
                      _selectedBeverage! +
                          (_selectedTeaType != null
                              ? ' ($_selectedTeaType)'
                              : ''),
                    ),
                  _buildConfirmationRow('Patient:', _selectedPatient ?? ''),
                  _buildConfirmationRow(
                    isRefill ? 'Medication:' : 'Reason:',
                    isRefill ? _medicationCtrl.text : _selectedSymptom ?? '',
                  ),
                  if (!isRefill && _selectedDate != null)
                    _buildConfirmationRow(
                        'Date:', DateFormat.yMMMMd().format(_selectedDate!)),
                  if (!isRefill && timeStr.isNotEmpty)
                    _buildConfirmationRow('Time:', timeStr),
                ],
              ),
            ),
            if (_visitMode == 'Clinic' &&
                _selectedBeverage != null &&
                !isRefill) ...[
              SizedBox(height: layoutSettings.paddingV),
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      joviCoral.withOpacity(0.14),
                      joviCoralLight.withOpacity(0.08),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: joviCoral.withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: joviCoral.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Icon(
                            _selectedBeverage == 'Premium Water'
                                ? Icons.water_drop
                                : Icons.local_cafe,
                            color: joviCoral,
                            size: layoutSettings.actionIconDimension,
                          ),
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Complimentary Beverage',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 3,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                'Your $_selectedBeverage${_selectedTeaType != null ? ' ($_selectedTeaType)' : ''} will be ready when you arrive',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 1,
                                  color: Colors.white.withOpacity(0.75),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
            if (!isRefill) ...[
              SizedBox(height: layoutSettings.paddingV),
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  color: joviMint.withOpacity(0.10),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: joviMint.withOpacity(0.35)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.medical_information,
                            color: joviMint,
                            size: layoutSettings.actionIconDimension),
                        SizedBox(width: 8),
                        Text(
                          'Health Information Summary',
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 3,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 12),
                    if (_allergiesCtrl.text.isNotEmpty) ...[
                      _buildHealthInfoRow('Allergies', _allergiesCtrl.text),
                      SizedBox(height: 8),
                    ],
                    if (_currentMedicationsCtrl.text.isNotEmpty) ...[
                      _buildHealthInfoRow(
                          'Medications', _currentMedicationsCtrl.text),
                      SizedBox(height: 8),
                    ],
                    if (_smokingStatus != null) ...[
                      _buildHealthInfoRow('Smoking', _smokingStatus!),
                      SizedBox(height: 8),
                    ],
                    if (_exerciseFrequency != null) ...[
                      _buildHealthInfoRow('Exercise', _exerciseFrequency!),
                    ],
                  ],
                ),
              ),
            ],
            if (_visitMode == 'Clinic' &&
                _selectedClinic != null &&
                !isRefill) ...[
              SizedBox(height: layoutSettings.paddingV),
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.07),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withOpacity(0.15)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: joviCoral.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Icon(
                            Icons.location_on,
                            color: joviCoral,
                            size: layoutSettings.actionIconDimension,
                          ),
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Clinic Location',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 3,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              SizedBox(height: 4),
                              Text(
                                _clinicLocations[_selectedClinic]![
                                    'fullAddress'] as String,
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 1,
                                  color: Colors.white.withOpacity(0.7),
                                ),
                              ),
                              if (_clinicLocations[_selectedClinic]!['phone'] !=
                                  null) ...[
                                SizedBox(height: 4),
                                Row(
                                  children: [
                                    Icon(Icons.phone,
                                        size: 14,
                                        color: Colors.white.withOpacity(0.6)),
                                    SizedBox(width: 4),
                                    Text(
                                      _clinicLocations[_selectedClinic]![
                                          'phone'] as String,
                                      style: TextStyle(
                                        fontSize:
                                            layoutSettings.actionTextSize + 1,
                                        color: Colors.white.withOpacity(0.7),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: layoutSettings.paddingV * 0.8),
                    InkWell(
                      onTap: () => _launchMapNavigation(),
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        padding: EdgeInsets.symmetric(
                            vertical: 10, horizontal: layoutSettings.paddingH),
                        decoration: BoxDecoration(
                          color: joviCoral.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: joviCoral.withOpacity(0.4)),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.directions, color: joviCoral, size: 20),
                            SizedBox(width: 8),
                            Text(
                              'Preview Directions',
                              style: TextStyle(
                                color: joviCoral,
                                fontWeight: FontWeight.w600,
                                fontSize: layoutSettings.actionTextSize + 1,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            SizedBox(height: layoutSettings.paddingV * 1.6),
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                color: joviGold.withOpacity(0.12),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: joviGold.withOpacity(0.4)),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline,
                      color: joviGold,
                      size: layoutSettings.actionIconDimension),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Ready to submit?',
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 2,
                            fontWeight: FontWeight.bold,
                            color: joviGold,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          isRefill
                              ? 'Tap "Submit Refill Request" below to send your refill request'
                              : _isRescheduleMode
                                  ? 'Tap "Confirm Reschedule" below to update your appointment'
                                  : 'Tap "Confirm Appointment" below to confirm your appointment',
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 1,
                            color: Colors.white.withOpacity(0.85),
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
    );
  }

  Widget _buildConfirmationRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: layoutSettings.actionTextSize + 1,
              color: Colors.white.withOpacity(0.6),
              fontWeight: FontWeight.w500,
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 3,
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHealthInfoRow(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 6,
          height: 6,
          margin: EdgeInsets.only(top: 6),
          decoration: BoxDecoration(
            color: joviMint,
            shape: BoxShape.circle,
          ),
        ),
        SizedBox(width: 8),
        Expanded(
          child: Text.rich(
            TextSpan(
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 1,
                color: Colors.white,
              ),
              children: [
                TextSpan(
                  text: '$label: ',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                TextSpan(
                  text: value,
                  style: TextStyle(color: Colors.white.withOpacity(0.85)),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTimeSlots() {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: _availableTimeSlots.map((slot) {
        final isBooked = _bookedTimeSlots.contains(slot);
        final isSelected = _selectedTimeSlot == slot;

        return _Pressable(
          onTap: isBooked
              ? null
              : () {
                  HapticFeedback.selectionClick();
                  setState(() {
                    _selectedTimeSlot = _selectedTimeSlot == slot ? null : slot;
                    _selectedTime = null;
                  });
                },
          child: AnimatedContainer(
            duration: _Motion.select,
            padding: EdgeInsets.symmetric(
                horizontal: layoutSettings.paddingH * 0.8, vertical: 12),
            decoration: BoxDecoration(
              gradient: isSelected
                  ? LinearGradient(
                      colors: [joviCoral, joviCoralDark],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    )
                  : null,
              color: isSelected
                  ? null
                  : isBooked
                      ? Colors.white.withOpacity(0.04)
                      : Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: isSelected
                    ? joviCoral
                    : isBooked
                        ? Colors.white.withOpacity(0.10)
                        : Colors.white.withOpacity(0.15),
                width: isSelected ? 2 : 1,
              ),
              boxShadow: isBooked
                  ? null
                  : [
                      BoxShadow(
                        color: (isSelected ? joviCoral : Colors.black)
                            .withOpacity(0.2),
                        blurRadius: 4,
                        offset: Offset(0, 2),
                      ),
                    ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  slot,
                  style: TextStyle(
                    color: isSelected
                        ? Colors.white
                        : isBooked
                            ? Colors.white.withOpacity(0.3)
                            : Colors.white,
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.normal,
                    decoration: isBooked ? TextDecoration.lineThrough : null,
                  ),
                ),
                if (isBooked) ...[
                  SizedBox(width: 4),
                  Icon(Icons.block,
                      size: 14, color: Colors.white.withOpacity(0.3)),
                ],
              ],
            ),
          ),
        );
      }).toList(),
    );
  }

  Widget _buildQuickActionButton(
      String label, IconData icon, VoidCallback onTap) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.08),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: joviCoral.withOpacity(0.4)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon,
                  color: joviCoral,
                  size: layoutSettings.actionIconDimension * 0.7),
              SizedBox(width: 8),
              Text(
                label,
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w600,
                  fontSize: layoutSettings.actionTextSize + 1,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _selectNextAvailable() {
    final now = DateTime.now();
    DateTime checkDate = now;

    for (int i = 0; i < 30; i++) {
      if (checkDate.weekday != DateTime.sunday) {
        setState(() {
          _selectedDate = checkDate;
          _calendarMonth = checkDate;
        });
        _generateAvailableTimeSlots();
        _loadBookedTimeSlots().then((_) {
          if (!mounted) return;
          if (_availableTimeSlots.isNotEmpty) {
            for (String slot in _availableTimeSlots) {
              if (!_bookedTimeSlots.contains(slot)) {
                setState(() {
                  _selectedTimeSlot = slot;
                });
                HapticFeedback.mediumImpact();
                return;
              }
            }
          }
        });

        if (_availableTimeSlots.isNotEmpty) {
          break;
        }
      }
      checkDate = checkDate.add(Duration(days: 1));
    }
  }

  void _selectTomorrow() {
    final tomorrow = DateTime.now().add(Duration(days: 1));
    if (tomorrow.weekday != DateTime.sunday) {
      setState(() {
        _selectedDate = tomorrow;
        _calendarMonth = tomorrow;
        _selectedTimeSlot = null;
      });
      _generateAvailableTimeSlots();
      _loadBookedTimeSlots();
      HapticFeedback.mediumImpact();
    } else {
      final monday = DateTime.now().add(Duration(days: 2));
      setState(() {
        _selectedDate = monday;
        _calendarMonth = monday;
        _selectedTimeSlot = null;
      });
      _generateAvailableTimeSlots();
      _loadBookedTimeSlots();
      HapticFeedback.mediumImpact();
    }
  }

  void _changeMonth(int direction) {
    setState(() {
      _calendarMonth = DateTime(
        _calendarMonth.year,
        _calendarMonth.month + direction,
        1,
      );
    });
    HapticFeedback.selectionClick();
  }

  Widget _buildCalendarGrid() {
    final firstDayOfMonth =
        DateTime(_calendarMonth.year, _calendarMonth.month, 1);
    final lastDayOfMonth =
        DateTime(_calendarMonth.year, _calendarMonth.month + 1, 0);
    final startingWeekday = firstDayOfMonth.weekday;
    final daysInMonth = lastDayOfMonth.day;

    final today = DateTime.now();
    final tomorrow = today.add(Duration(days: 1));

    List<Widget> dayWidgets = [];

    for (int i = 1; i < startingWeekday; i++) {
      dayWidgets.add(Container());
    }

    for (int day = 1; day <= daysInMonth; day++) {
      final date = DateTime(_calendarMonth.year, _calendarMonth.month, day);
      final isToday = date.year == today.year &&
          date.month == today.month &&
          date.day == today.day;
      final isTomorrow = date.year == tomorrow.year &&
          date.month == tomorrow.month &&
          date.day == tomorrow.day;
      final isSelected = _selectedDate != null &&
          date.year == _selectedDate!.year &&
          date.month == _selectedDate!.month &&
          date.day == _selectedDate!.day;
      final isSunday = date.weekday == DateTime.sunday;
      final isPast =
          date.isBefore(DateTime(today.year, today.month, today.day));
      final isDisabled = isSunday || isPast;

      dayWidgets.add(
        _Pressable(
          onTap: isDisabled
              ? null
              : () {
                  setState(() {
                    _selectedDate = date;
                    _selectedTimeSlot = null;
                  });
                  _generateAvailableTimeSlots();
                  _loadBookedTimeSlots();
                  HapticFeedback.selectionClick();
                },
          child: Container(
            margin: EdgeInsets.all(2),
            decoration: BoxDecoration(
              gradient: isSelected
                  ? LinearGradient(
                      colors: [joviCoral, joviCoralDark],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    )
                  : null,
              color: isSelected
                  ? null
                  : isToday
                      ? joviCoral.withOpacity(0.18)
                      : isDisabled
                          ? Colors.white.withOpacity(0.03)
                          : Colors.white.withOpacity(0.07),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: isSelected
                    ? joviCoral
                    : isToday
                        ? joviCoral.withOpacity(0.55)
                        : Colors.white.withOpacity(0.10),
                width: isSelected ? 2 : 1,
              ),
            ),
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    day.toString(),
                    style: TextStyle(
                      color: isSelected
                          ? Colors.white
                          : isDisabled
                              ? Colors.white.withOpacity(0.25)
                              : Colors.white,
                      fontWeight: isSelected || isToday
                          ? FontWeight.bold
                          : FontWeight.normal,
                      fontSize: layoutSettings.actionTextSize + 1,
                    ),
                  ),
                  if (isToday)
                    Container(
                      margin: EdgeInsets.only(top: 2),
                      width: 4,
                      height: 4,
                      decoration: BoxDecoration(
                        color: isSelected ? Colors.white : joviCoral,
                        shape: BoxShape.circle,
                      ),
                    ),
                  if (isTomorrow && !isSelected)
                    Container(
                      margin: EdgeInsets.only(top: 2),
                      padding: EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                      decoration: BoxDecoration(
                        color: joviMint.withOpacity(0.25),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'TOM',
                        style: TextStyle(
                          fontSize: 8,
                          color: joviMint,
                          fontWeight: FontWeight.bold,
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

    return GridView.count(
      shrinkWrap: true,
      physics: NeverScrollableScrollPhysics(),
      crossAxisCount: 7,
      childAspectRatio: 1,
      children: dayWidgets,
    );
  }

  Widget _buildTimeGroupTab(String label, IconData icon, bool isMorning) {
    final isSelected = _showMorningSlots == isMorning;
    return _Pressable(
      onTap: () {
        setState(() {
          _showMorningSlots = isMorning;
        });
        HapticFeedback.selectionClick();
      },
      child: Container(
        padding: EdgeInsets.symmetric(vertical: 12),
        constraints: const BoxConstraints(minHeight: 44),
        decoration: BoxDecoration(
          color: isSelected ? joviCoral : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              icon,
              color: isSelected ? Colors.white : Colors.white.withOpacity(0.6),
              size: layoutSettings.actionIconDimension * 0.8,
            ),
            SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color:
                    isSelected ? Colors.white : Colors.white.withOpacity(0.6),
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                fontSize: layoutSettings.actionTextSize + 1,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeSlotGrid() {
    final filteredSlots = _availableTimeSlots.where((slot) {
      final hour = int.parse(slot.split(':')[0]);
      final isPM = slot.contains('PM');
      final actualHour =
          isPM && hour != 12 ? hour + 12 : (hour == 12 && !isPM ? 0 : hour);

      if (_showMorningSlots) {
        return actualHour < 12;
      } else {
        return actualHour >= 12;
      }
    }).toList();

    if (filteredSlots.isEmpty) {
      return Container(
        padding: EdgeInsets.all(layoutSettings.paddingH),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.white.withOpacity(0.12)),
        ),
        child: Column(
          children: [
            Icon(Icons.schedule,
                size: 48, color: Colors.white.withOpacity(0.3)),
            SizedBox(height: 12),
            Text(
              _showMorningSlots
                  ? 'No morning appointments available'
                  : 'No afternoon appointments available',
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 3,
                fontWeight: FontWeight.w600,
                color: Colors.white.withOpacity(0.7),
              ),
            ),
            SizedBox(height: 4),
            Text(
              'Try selecting a different time period',
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 1,
                color: Colors.white.withOpacity(0.5),
              ),
            ),
          ],
        ),
      );
    }

    final crossAxisCount = layoutSettings.wideMode ? 4 : 3;

    return Container(
      child: GridView.count(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisCount: crossAxisCount,
        childAspectRatio: 2.5,
        mainAxisSpacing: 8,
        crossAxisSpacing: 8,
        children: filteredSlots.map((slot) {
          final isBooked = _bookedTimeSlots.contains(slot);
          final isSelected = _selectedTimeSlot == slot;

          final hour = int.parse(slot.split(':')[0]);
          final isPM = slot.contains('PM');
          final actualHour =
              isPM && hour != 12 ? hour + 12 : (hour == 12 && !isPM ? 0 : hour);
          final isBusyTime = actualHour >= 11 && actualHour <= 14;

          return _Pressable(
            onTap: isBooked
                ? null
                : () {
                    HapticFeedback.selectionClick();
                    setState(() {
                      _selectedTimeSlot =
                          _selectedTimeSlot == slot ? null : slot;
                      _selectedTime = null;
                    });
                  },
            child: AnimatedContainer(
              duration: _Motion.select,
              decoration: BoxDecoration(
                gradient: isSelected
                    ? LinearGradient(
                        colors: [joviCoral, joviCoralDark],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: isSelected
                    ? null
                    : isBooked
                        ? Colors.white.withOpacity(0.04)
                        : Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: isSelected
                      ? joviCoral
                      : isBooked
                          ? Colors.white.withOpacity(0.10)
                          : isBusyTime && !isBooked
                              ? joviGold.withOpacity(0.5)
                              : Colors.white.withOpacity(0.15),
                  width: isSelected ? 2 : 1,
                ),
                boxShadow: isBooked
                    ? null
                    : [
                        BoxShadow(
                          color: (isSelected ? joviCoral : Colors.black)
                              .withOpacity(0.2),
                          blurRadius: 4,
                          offset: Offset(0, 2),
                        ),
                      ],
              ),
              child: Stack(
                children: [
                  Center(
                    child: Text(
                      slot,
                      style: TextStyle(
                        color: isSelected
                            ? Colors.white
                            : isBooked
                                ? Colors.white.withOpacity(0.3)
                                : Colors.white,
                        fontWeight:
                            isSelected ? FontWeight.bold : FontWeight.normal,
                        fontSize: layoutSettings.actionTextSize,
                        decoration:
                            isBooked ? TextDecoration.lineThrough : null,
                      ),
                    ),
                  ),
                  if (isBusyTime && !isBooked && !isSelected)
                    Positioned(
                      top: 4,
                      right: 4,
                      child: Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: joviGold,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                  if (isBooked)
                    Positioned(
                      bottom: 4,
                      right: 4,
                      child: Icon(
                        Icons.block,
                        size: 12,
                        color: Colors.white.withOpacity(0.3),
                      ),
                    ),
                ],
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildSuggestedSymptomChip(String symptom) {
    final isSelected = _selectedSymptom == symptom;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _selectedSymptom = symptom);
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        padding: EdgeInsets.symmetric(
            horizontal: layoutSettings.paddingH * 0.8,
            vertical: layoutSettings.paddingV * 0.5),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [joviCoral, joviCoralDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : joviCoral.withOpacity(0.15),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? joviCoral : joviCoral.withOpacity(0.4),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Text(
          symptom,
          style: TextStyle(
            color: isSelected ? Colors.white : joviCoralLight,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildSymptomCard(String symptom) {
    final isSelected = _selectedSymptom == symptom;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _selectedSymptom = symptom);
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        margin: EdgeInsets.only(bottom: 12),
        padding: EdgeInsets.all(layoutSettings.paddingH),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [joviCoral, joviCoralDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? joviCoral : Colors.white.withOpacity(0.15),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                symptom,
                style: TextStyle(
                  fontSize: layoutSettings.actionTextSize + 3,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                  color: Colors.white,
                ),
              ),
            ),
            if (isSelected)
              Icon(Icons.check_circle, color: Colors.white, size: 20),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildRadioOptions(
    String groupName,
    List<String> options,
    String? selectedValue,
    Function(String?) onChanged,
  ) {
    return options.map((option) {
      final isSelected = selectedValue == option;
      return Padding(
        padding: EdgeInsets.only(bottom: 8),
        child: InkWell(
          onTap: () {
            HapticFeedback.selectionClick();
            onChanged(option);
          },
          borderRadius: BorderRadius.circular(12),
          child: Container(
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: isSelected
                  ? joviCoral.withOpacity(0.15)
                  : Colors.white.withOpacity(0.06),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isSelected ? joviCoral : Colors.white.withOpacity(0.15),
                width: isSelected ? 2 : 1,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isSelected
                          ? joviCoral
                          : Colors.white.withOpacity(0.4),
                      width: 2,
                    ),
                  ),
                  child: isSelected
                      ? Center(
                          child: Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: joviCoral,
                            ),
                          ),
                        )
                      : null,
                ),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    option,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 2,
                      fontWeight:
                          isSelected ? FontWeight.w600 : FontWeight.normal,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }).toList();
  }

  Widget _buildDurationCard(
      String duration, IconData icon, String description, Color color) {
    final isSelected = _symptomDuration == duration;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _symptomDuration = duration);
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        padding: EdgeInsets.all(layoutSettings.paddingH),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [color.withOpacity(0.8), color],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? color : Colors.white.withOpacity(0.15),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: isSelected
                  ? color.withOpacity(0.3)
                  : Colors.black.withOpacity(0.15),
              blurRadius: isSelected ? 20 : 10,
              offset: Offset(0, isSelected ? 8 : 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isSelected
                    ? Colors.white.withOpacity(0.2)
                    : color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon,
                  color: isSelected ? Colors.white : color,
                  size: layoutSettings.actionIconDimension),
            ),
            SizedBox(width: layoutSettings.paddingH * 0.8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    duration,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 5,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    description,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 1,
                      color: isSelected
                          ? Colors.white.withOpacity(0.9)
                          : Colors.white.withOpacity(0.65),
                    ),
                  ),
                ],
              ),
            ),
            if (isSelected)
              Icon(Icons.check_circle,
                  color: Colors.white,
                  size: layoutSettings.actionIconDimension),
          ],
        ),
      ),
    );
  }

  Widget _buildStyledTextField(
    TextEditingController controller,
    String label,
    String hint,
    IconData icon, {
    int maxLines = 1,
    bool isRequired = false,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.15),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: TextFormField(
        controller: controller,
        maxLines: maxLines,
        style: TextStyle(color: Colors.white),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: TextStyle(color: Colors.white.withOpacity(0.75)),
          floatingLabelStyle: TextStyle(color: joviCoral),
          hintText: hint,
          hintStyle: TextStyle(
            fontSize: layoutSettings.actionTextSize + 1,
            color: Colors.white.withOpacity(0.4),
          ),
          prefixIcon: Icon(icon, color: joviCoral),
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
            borderSide: BorderSide(color: joviCoral, width: 2),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Color(0xFFE53935), width: 2),
          ),
          filled: true,
          fillColor: Colors.white.withOpacity(0.06),
          contentPadding: EdgeInsets.all(layoutSettings.paddingH),
        ),
        onChanged: (value) {
          setState(() => _medicalDirty = true);
        },
      ),
    );
  }

  Widget _buildStep({
    Key? key,
    required IconData icon,
    required String title,
    required String subtitle,
    required Widget child,
  }) {
    return Container(
      key: key,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [joviNavy, joviNavy, joviNavyDark],
        ),
      ),
      child: wrapWithConstraints(
        child: SingleChildScrollView(
          padding: _getAdaptivePadding(context),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                padding: EdgeInsets.all(layoutSettings.paddingH),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.07),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white.withOpacity(0.12)),
                  boxShadow: [
                    BoxShadow(
                      color: joviCoral.withOpacity(0.18),
                      blurRadius: 30,
                      offset: Offset(0, 10),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    TweenAnimationBuilder<double>(
                      tween: Tween(begin: _reduceMotion ? 1.0 : 0.92, end: 1.0),
                      duration: _Motion.enter,
                      curve: _Motion.settle,
                      builder: (context, value, child) {
                        return Transform.scale(
                          scale: value,
                          child: Container(
                            width: 80,
                            height: 80,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  joviCoral.withOpacity(0.25),
                                  joviCoralDark.withOpacity(0.15),
                                ],
                              ),
                              borderRadius: BorderRadius.circular(50),
                              border: Border.all(
                                color: joviCoral.withOpacity(0.4),
                                width: 2,
                              ),
                            ),
                            child: Icon(icon,
                                size: layoutSettings.actionIconDimension + 8,
                                color: joviCoral),
                          ),
                        );
                      },
                    ),
                    SizedBox(height: layoutSettings.paddingV),
                    Text(
                      title,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: layoutSettings.wideMode ? 30 : 26,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: -0.5,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text(
                      subtitle,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: layoutSettings.wideMode ? 17 : 15,
                        color: Colors.white.withOpacity(0.7),
                        height: 1.5,
                      ),
                    ),
                  ],
                ),
              ),
              SizedBox(height: layoutSettings.paddingV * 1.4),
              child,
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildVisitTypeCard(
      String type, IconData icon, String description, Color color) {
    final isSelected = _visitType == type;

    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() {
          _visitType = type;
          _selectedSymptom = null;
          _symptomSearchQuery = '';
          _symptomSearchController.clear();
        });
        _loadSuggestedSymptoms();
      },
      child: AnimatedContainer(
              duration: _Motion.select,
              padding: EdgeInsets.all(layoutSettings.paddingH),
              decoration: BoxDecoration(
                gradient: isSelected
                    ? LinearGradient(
                        colors: [color.withOpacity(0.85), color],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      )
                    : null,
                color: isSelected ? null : Colors.white.withOpacity(0.07),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isSelected ? color : Colors.white.withOpacity(0.12),
                  width: isSelected ? 2.5 : 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: isSelected
                        ? color.withOpacity(0.45)
                        : Colors.black.withOpacity(0.2),
                    blurRadius: isSelected ? 25 : 15,
                    offset: Offset(0, isSelected ? 12 : 8),
                  ),
                ],
              ),
              child: Row(
                children: [
                  Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH * 0.7),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: isSelected
                            ? [
                                Colors.white.withOpacity(0.3),
                                Colors.white.withOpacity(0.1)
                              ]
                            : [
                                color.withOpacity(0.25),
                                color.withOpacity(0.15)
                              ],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(icon,
                        color: isSelected ? Colors.white : color,
                        size: layoutSettings.actionIconDimension + 2),
                  ),
                  SizedBox(width: layoutSettings.paddingH * 0.8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          type,
                          style: TextStyle(
                            fontSize: layoutSettings.wideMode ? 22 : 19,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          description,
                          style: TextStyle(
                            fontSize: layoutSettings.wideMode ? 15 : 13,
                            color: isSelected
                                ? Colors.white.withOpacity(0.95)
                                : Colors.white.withOpacity(0.65),
                            height: 1.3,
                          ),
                        ),
                      ],
                    ),
                  ),
                  AnimatedSwitcher(
                    duration: _Motion.select,
                    child: isSelected
                        ? Container(
                            key: ValueKey('selected'),
                            padding: EdgeInsets.all(6),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.25),
                              shape: BoxShape.circle,
                            ),
                            child: Icon(Icons.check,
                                color: Colors.white, size: 20),
                          )
                        : SizedBox(key: ValueKey('unselected'), width: 32),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildModeCard(
      String mode, IconData icon, String description, bool isClinic) {
    final isSelected = _visitMode == mode;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() {
          _visitMode = mode;
          if (mode == 'Virtual') {
            _selectedClinic = null;
            _selectedBeverage = null;
            _selectedTeaType = null;
          }
        });
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        padding: EdgeInsets.all(layoutSettings.paddingH),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [joviCoral, joviCoralDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? joviCoral : Colors.white.withOpacity(0.15),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: isSelected
                  ? joviCoral.withOpacity(0.4)
                  : Colors.black.withOpacity(0.15),
              blurRadius: isSelected ? 20 : 10,
              offset: Offset(0, isSelected ? 8 : 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isSelected
                    ? Colors.white.withOpacity(0.2)
                    : joviCoral.withOpacity(0.18),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon,
                  color: isSelected ? Colors.white : joviCoral,
                  size: layoutSettings.actionIconDimension),
            ),
            SizedBox(width: layoutSettings.paddingH * 0.8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    mode,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 5,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(height: 4),
                  Text(
                    description,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 1,
                      color: isSelected
                          ? Colors.white.withOpacity(0.9)
                          : Colors.white.withOpacity(0.65),
                    ),
                  ),
                ],
              ),
            ),
            if (isSelected)
              Icon(Icons.check_circle,
                  color: Colors.white,
                  size: layoutSettings.actionIconDimension),
          ],
        ),
      ),
    );
  }

  Widget _buildClinicCard(String name, Map<String, dynamic> info) {
    final isSelected = _selectedClinic == name;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _selectedClinic = name);
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        margin: EdgeInsets.only(bottom: layoutSettings.paddingV * 0.8),
        padding: EdgeInsets.all(layoutSettings.paddingH),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [joviCoral, joviCoralDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? joviCoral : Colors.white.withOpacity(0.15),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: isSelected
                  ? joviCoral.withOpacity(0.4)
                  : Colors.black.withOpacity(0.15),
              blurRadius: isSelected ? 20 : 10,
              offset: Offset(0, isSelected ? 8 : 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? Colors.white.withOpacity(0.2)
                        : joviCoral.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(Icons.location_on,
                      color: isSelected ? Colors.white : joviCoral,
                      size: layoutSettings.actionIconDimension),
                ),
                SizedBox(width: layoutSettings.paddingH * 0.8),
                Expanded(
                  child: Text(
                    name,
                    style: TextStyle(
                      fontSize: layoutSettings.actionTextSize + 5,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
                if (isSelected)
                  Icon(Icons.check_circle,
                      color: Colors.white,
                      size: layoutSettings.actionIconDimension),
              ],
            ),
            SizedBox(height: 12),
            Text(
              info['fullAddress'] as String,
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 1,
                color: isSelected
                    ? Colors.white.withOpacity(0.9)
                    : Colors.white.withOpacity(0.65),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Confirmation card shown on the patient step when a patient was
  /// pre-selected from the profile picker. Shows the name with a matching
  /// avatar + an Edit button that clears the selection and falls back to
  /// the full patient list (which re-renders in the same step).
  Widget _buildPreselectedPatientCard(String name) {
    // Pull the matching human's photo from the picker data (if available).
    String? photoUrl;
    for (final h in _accountHumans) {
      if ((h['name'] as String?) == name) {
        photoUrl = h['photoUrl'] as String?;
        break;
      }
    }
    final initial = name.trim().isNotEmpty ? name.trim()[0].toUpperCase() : '?';
    final hasPhoto = photoUrl != null && photoUrl.isNotEmpty;
    return Container(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [joviCoral, joviCoralDark],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: joviCoral.withOpacity(0.4),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Row(
        children: [
          // Avatar (photo or initial).
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white.withOpacity(0.22),
              border: Border.all(
                color: Colors.white.withOpacity(0.4),
                width: 1.5,
              ),
            ),
            child: ClipOval(
              child: hasPhoto
                  ? Image.network(
                      photoUrl,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Center(
                        child: Text(
                          initial,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                    )
                  : Center(
                      child: Text(
                        initial,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Visit for',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.82),
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.6,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.4,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          // Edit button — clears preselection and re-renders the same
          // step with the full patient selector list.
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
                HapticFeedback.selectionClick();
                setState(() => _selectedPatient = null);
              },
              borderRadius: BorderRadius.circular(11),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.22),
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.4),
                    width: 1,
                  ),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.edit_rounded, color: Colors.white, size: 13),
                    SizedBox(width: 5),
                    Text(
                      'Edit',
                      style: TextStyle(
                        color: Colors.white,
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
        ],
      ),
    );
  }

  Widget _buildPatientCard(String name) {
    final isSelected = _selectedPatient == name;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _selectedPatient = name);
      },
      child: AnimatedContainer(
        duration: _Motion.select,
        margin: EdgeInsets.only(bottom: 12),
        padding: EdgeInsets.all(layoutSettings.paddingH),
        decoration: BoxDecoration(
          gradient: isSelected
              ? LinearGradient(
                  colors: [joviCoral, joviCoralDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: isSelected ? null : Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? joviCoral : Colors.white.withOpacity(0.15),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: isSelected
                  ? joviCoral.withOpacity(0.4)
                  : Colors.black.withOpacity(0.15),
              blurRadius: isSelected ? 15 : 8,
              offset: Offset(0, isSelected ? 6 : 3),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: isSelected
                    ? Colors.white.withOpacity(0.2)
                    : joviCoral.withOpacity(0.18),
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text(
                  name.substring(0, 1).toUpperCase(),
                  style: TextStyle(
                    fontSize: layoutSettings.actionTextSize + 7,
                    fontWeight: FontWeight.bold,
                    color: isSelected ? Colors.white : joviCoral,
                  ),
                ),
              ),
            ),
            SizedBox(width: layoutSettings.paddingH * 0.8),
            Expanded(
              child: Text(
                name,
                style: TextStyle(
                  fontSize: layoutSettings.actionTextSize + 3,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                ),
              ),
            ),
            if (isSelected)
              Icon(Icons.check_circle,
                  color: Colors.white,
                  size: layoutSettings.actionIconDimension),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // FLOW CHOOSER LANDING
  // First screen a member sees (unless SharedPreferences has a saved
  // mode from last time). Two big tappable cards: Human vs Pet.
  // ═══════════════════════════════════════════════════════════════

  // ═══════════════════════════════════════════════════════════════════
  // VISUAL PROFILE PICKER — "Who\'s this for?"
  //
  // Replaces the old Pet-or-Human text chooser with a Netflix-style
  // grid of circular profile photos. People section on top (primary
  // user + dependents), Pets section below (dogs / cats / other).
  // Tapping a human enters the human flow with _selectedPatient
  // pre-populated; tapping a pet enters the pet flow with _selectedPet
  // pre-populated.
  // ═══════════════════════════════════════════════════════════════════

  Widget _buildFlowChooser() {
    final loading = !_petsLoaded || !_humansLoaded;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: Container(
        width: widget.width,
        height: widget.height,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [joviNavy, joviNavy, joviNavyDark],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              _buildPickerHeader(),
              Expanded(
                child: loading
                    ? _buildPickerSkeleton()
                    : SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _buildPickerIntro(),
                            const SizedBox(height: 22),
                            _buildPeopleSection(),
                            const SizedBox(height: 22),
                            _buildPetsSection(),
                          ],
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPickerHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 10, 20, 4),
      child: Row(
        children: [
          Material(
            color: Colors.transparent,
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
                  width: 40,
                  height: 40,
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
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              'Request Care',
              style: TextStyle(
                color: Colors.white,
                fontSize: 17,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPickerIntro() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          "Who\'s this for?",
          style: TextStyle(
            color: Colors.white,
            fontSize: 28,
            fontWeight: FontWeight.w900,
            letterSpacing: -0.8,
            height: 1.1,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Pick a profile to start a care request.',
          style: TextStyle(
            color: Colors.white.withOpacity(0.6),
            fontSize: 14,
            fontWeight: FontWeight.w500,
            height: 1.45,
          ),
        ),
      ],
    );
  }

  // ─── People section ─────────────────────────────────────────────────

  Widget _buildPeopleSection() {
    final tiles = <Widget>[
      for (final h in _accountHumans) _buildHumanTile(h),
      _buildAddTile(
        label: 'Add family',
        icon: Icons.group_add_rounded,
        accent: joviMint,
        onTap: _openDependentsEditor,
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionHeader(
          icon: Icons.people_alt_rounded,
          label: 'People',
          count: _accountHumans.length,
        ),
        const SizedBox(height: 14),
        _buildTileGrid(tiles),
      ],
    );
  }

  // ─── Pets section ───────────────────────────────────────────────────

  Widget _buildPetsSection() {
    final tiles = <Widget>[
      for (final p in _userPets) _buildPetTile(p),
      _buildAddTile(
        label: 'Add a pet',
        icon: Icons.add_rounded,
        accent: const Color(0xFFA78BFA),
        onTap: _openPetProfilesRoute,
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSectionHeader(
          icon: Icons.pets_rounded,
          label: 'Pets',
          count: _userPets.length,
        ),
        const SizedBox(height: 14),
        _buildTileGrid(tiles),
      ],
    );
  }

  Widget _buildSectionHeader({
    required IconData icon,
    required String label,
    required int count,
  }) {
    return Row(
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.08),
            borderRadius: BorderRadius.circular(9),
            border: Border.all(
              color: Colors.white.withOpacity(0.12),
              width: 0.8,
            ),
          ),
          child: Icon(icon, color: Colors.white.withOpacity(0.85), size: 15),
        ),
        const SizedBox(width: 10),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 13.5,
            fontWeight: FontWeight.w900,
            letterSpacing: 0.4,
          ),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.08),
            borderRadius: BorderRadius.circular(7),
          ),
          child: Text(
            '$count',
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 10.5,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.2,
            ),
          ),
        ),
      ],
    );
  }

  // ─── 2-column grid helper ───────────────────────────────────────────
  //
  // Using a simple Wrap + LayoutBuilder instead of GridView so the grid
  // plays nicely inside the parent SingleChildScrollView. Each tile gets
  // half the available width minus the gap.

  Widget _buildTileGrid(List<Widget> tiles) {
    const gap = 14.0;
    return LayoutBuilder(builder: (ctx, constraints) {
      final tileW = (constraints.maxWidth - gap) / 2;
      return Wrap(
        spacing: gap,
        runSpacing: gap,
        children: tiles.map((t) => SizedBox(width: tileW, child: t)).toList(),
      );
    });
  }

  // ─── Human tile (circular photo Netflix-style) ──────────────────────

  Widget _buildHumanTile(Map<String, dynamic> human) {
    final name = (human['name'] as String?) ?? 'Account';
    final photoUrl = human['photoUrl'] as String?;
    final kind = (human['kind'] as String?) ?? 'dependent';
    final subtitle = kind == 'primary' ? 'Primary account' : 'Family member';
    return _buildCircularProfileTile(
      name: name,
      subtitle: subtitle,
      photoUrl: photoUrl,
      ringGradient: kind == 'primary'
          ? const [joviCoral, joviCoralDark]
          : const [joviMint, joviMintDark],
      fallbackIcon: Icons.person_rounded,
      onTap: () => _pickHuman(human),
    );
  }

  // ─── Pet tile ───────────────────────────────────────────────────────

  Widget _buildPetTile(Map<String, dynamic> pet) {
    final name = (pet['name'] as String?) ?? 'Pet';
    final photoUrl =
        (pet['photo_url'] as String?) ?? (pet['photoUrl'] as String?);
    final type = _petTypeLabel(pet);
    final breed = (pet['breed'] as String?) ?? '';
    final subtitle = breed.isNotEmpty ? '$type · $breed' : type;
    return _buildCircularProfileTile(
      name: name,
      subtitle: subtitle,
      photoUrl: photoUrl,
      ringGradient: const [Color(0xFFA78BFA), Color(0xFF8B6EE8)],
      fallbackIcon: Icons.pets_rounded,
      onTap: () => _pickPet(pet),
    );
  }

  // ─── Shared circular tile primitive ─────────────────────────────────

  Widget _buildCircularProfileTile({
    required String name,
    required String subtitle,
    required String? photoUrl,
    required List<Color> ringGradient,
    required IconData fallbackIcon,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          onTap();
        },
        borderRadius: BorderRadius.circular(18),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Outer gradient ring + inner photo circle.
              Container(
                width: 108,
                height: 108,
                padding: const EdgeInsets.all(3),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(colors: ringGradient),
                  boxShadow: [
                    BoxShadow(
                      color: ringGradient.first.withOpacity(0.35),
                      blurRadius: 16,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),
                child: Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: joviNavyDark,
                  ),
                  child: ClipOval(
                    child: _buildProfileImage(
                      photoUrl: photoUrl,
                      name: name,
                      fallbackIcon: fallbackIcon,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                name,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Render the profile image. If photoUrl is present, use NetworkImage.
  /// Otherwise, fall back to initials (if name has letters) or an icon.
  Widget _buildProfileImage({
    required String? photoUrl,
    required String name,
    required IconData fallbackIcon,
  }) {
    final hasPhoto = photoUrl != null && photoUrl.isNotEmpty;
    if (hasPhoto) {
      return Image.network(
        photoUrl,
        fit: BoxFit.cover,
        width: double.infinity,
        height: double.infinity,
        errorBuilder: (_, __, ___) => _buildProfileFallback(name, fallbackIcon),
      );
    }
    return _buildProfileFallback(name, fallbackIcon);
  }

  Widget _buildProfileFallback(String name, IconData fallbackIcon) {
    final initial =
        name.trim().isNotEmpty ? name.trim()[0].toUpperCase() : null;
    return Container(
      color: joviNavyDark,
      alignment: Alignment.center,
      child: initial != null && RegExp(r'[A-Za-z]').hasMatch(initial)
          ? Text(
              initial,
              style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 36,
                fontWeight: FontWeight.w900,
                letterSpacing: -1,
              ),
            )
          : Icon(
              fallbackIcon,
              color: Colors.white.withOpacity(0.5),
              size: 40,
            ),
    );
  }

  // ─── "Add" tile (last item in each section) ─────────────────────────

  Widget _buildAddTile({
    required String label,
    required IconData icon,
    required Color accent,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          onTap();
        },
        borderRadius: BorderRadius.circular(18),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 108,
                height: 108,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white.withOpacity(0.04),
                  border: Border.all(
                    color: accent.withOpacity(0.45),
                    width: 1.4,
                    style: BorderStyle.solid,
                  ),
                ),
                child: Icon(icon, color: accent, size: 36),
              ),
              const SizedBox(height: 12),
              Text(
                label,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Tap to set up',
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.45),
                  fontSize: 11.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ─── Skeleton (while loading) ───────────────────────────────────────

  Widget _buildPickerSkeleton() {
    Widget dot() => Container(
          width: 108,
          height: 108,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: Colors.white.withOpacity(0.05),
            border: Border.all(
              color: Colors.white.withOpacity(0.08),
              width: 1,
            ),
          ),
        );
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildPickerIntro(),
          const SizedBox(height: 22),
          _buildSectionHeader(
              icon: Icons.people_alt_rounded, label: 'People', count: 0),
          const SizedBox(height: 14),
          Wrap(spacing: 14, runSpacing: 14, children: [dot(), dot()]),
          const SizedBox(height: 22),
          _buildSectionHeader(
              icon: Icons.pets_rounded, label: 'Pets', count: 0),
          const SizedBox(height: 14),
          Wrap(
              spacing: 14,
              runSpacing: 14,
              children: [dot(), dot(), dot(), dot()]),
        ],
      ),
    );
  }

  // ─── Selection handlers ─────────────────────────────────────────────

  /// User tapped a human profile. Pre-populate _selectedPatient and enter
  /// the human flow. The human flow\'s patient-selection step auto-advances
  /// past itself when a patient is already chosen.
  void _pickHuman(Map<String, dynamic> human) async {
    final name = (human['name'] as String?) ?? '';
    setState(() {
      _selectedPatient = name.isNotEmpty ? name : null;
    });
    await _setFlowMode('human');
  }

  /// User tapped a pet. Pre-populate the pet-flow state and enter the
  /// pet flow. The pet flow\'s pet-selection step (index 0) auto-advances
  /// when _selectedPet is already set.
  void _pickPet(Map<String, dynamic> pet) async {
    setState(() {
      _selectedPet = pet;
      _petPageIndex = 1; // skip past the pet-picker step
    });
    await _setFlowMode('pet');
  }

  /// Fallback navigation to Pet Profiles for the "Add a pet" tile.
  void _openPetProfilesRoute() {
    const routes = ['petPro', 'petProfiles', 'PetProfiles', 'pet_profiles'];
    for (final r in routes) {
      try {
        context.push('/$r');
        return;
      } catch (_) {
        continue;
      }
    }
  }

  /// Fallback navigation to the dependents/family editor. If the app
  /// doesn\'t have a dedicated route yet, falls back to the account menu.
  void _openDependentsEditor() {
    const routes = [
      'dependents',
      'familyMembers',
      'manageFamily',
      'accountMenu',
      'account',
    ];
    for (final r in routes) {
      try {
        context.push('/$r');
        return;
      } catch (_) {
        continue;
      }
    }
  }

  String _petsDisplayList() {
    if (_userPets.isEmpty) return 'your pet';
    final names = _userPets
        .map((p) => (p['name'] as String?)?.trim())
        .whereType<String>()
        .where((n) => n.isNotEmpty)
        .toList();
    if (names.isEmpty) return 'your pet';
    if (names.length == 1) return names[0];
    if (names.length == 2) return '${names[0]} or ${names[1]}';
    return '${names.take(names.length - 1).join(', ')}, or ${names.last}';
  }

  Widget _buildChooserCard({
    required IconData icon,
    required Color iconBgColor,
    required String title,
    required String subtitle,
    VoidCallback? onTap,
    required bool enabled,
  }) {
    return Opacity(
      opacity: enabled ? 1.0 : 0.55,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: enabled ? onTap : null,
          borderRadius: BorderRadius.circular(20),
          child: Semantics(
            label: enabled ? title : '$title — disabled',
            button: true,
            enabled: enabled,
            child: Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    iconBgColor.withOpacity(0.14),
                    iconBgColor.withOpacity(0.06),
                  ],
                ),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: iconBgColor.withOpacity(0.3),
                  width: 1,
                ),
                boxShadow: enabled
                    ? [
                        BoxShadow(
                          color: iconBgColor.withOpacity(0.15),
                          blurRadius: 18,
                          offset: const Offset(0, 6),
                        ),
                      ]
                    : null,
              ),
              child: Row(
                children: [
                  Container(
                    width: 58,
                    height: 58,
                    decoration: BoxDecoration(
                      color: iconBgColor,
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: enabled
                          ? [
                              BoxShadow(
                                color: iconBgColor.withOpacity(0.45),
                                blurRadius: 14,
                                offset: const Offset(0, 5),
                              ),
                            ]
                          : null,
                    ),
                    child: Icon(
                      icon,
                      color: Colors.white,
                      size: 28,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.3,
                            height: 1.2,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          subtitle,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.68),
                            fontSize: 12.5,
                            fontWeight: FontWeight.w500,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (enabled)
                    Icon(
                      Icons.chevron_right_rounded,
                      color: Colors.white.withOpacity(0.5),
                      size: 22,
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════
  // PET FLOW PLACEHOLDER
  // Shown when flow mode is 'pet'. For now, this is a stub that
  // tries to route to the forthcoming Request Vet Care widget.
  // If that route isn't wired yet, displays a friendly "coming
  // soon" card with a way back to the chooser.
  //
  // Once the real pet flow is built (next turns in this sequence),
  // this builder gets replaced with the full pet Request Vet Care
  // implementation.
  // ═══════════════════════════════════════════════════════════════

  // ═══════════════════════════════════════════════════════════════════
  // PET FLOW — Request Vet Care
  //
  // Mirrors the human flow structure exactly but with pet-specific content
  // and data model. Lives in the same widget so:
  //   - Design system is shared (colors, spacing, step card styling)
  //   - Flow chooser can hop between flows without losing state
  //   - Single Code Name in FF — one paste, one compile
  //
  // Steps (Phase 1 implements 1-2; Phase 2 adds 3-7; Phase 3 adds 8 + submit):
  //   1. Pet Selector        — pick which pet this is for
  //   2. Visit Type          — Wellness | Sick or Injured
  //   3. Clinic Selection    — reuses _clinicLocations
  //   4. Date & Time         — calendar + time slot
  //   5. Symptom / Reason    — species-aware chip grid with "Other"
  //   6. Duration            — how long has this been going on?
  //   7. Details             — optional free-text
  //   8. Confirmation + submit → users/{uid}/requests with audience: 'Pet'
  // ═══════════════════════════════════════════════════════════════════

  Widget _buildPetFlow() {
    // If we just successfully submitted, show the pet success screen.
    if (_showSuccess) {
      return _buildPetSuccessScreen();
    }
    // Guard: no pets on file should not reach here (the chooser gates it),
    // but if it does, bounce back to the chooser with a helpful message.
    if (_petsLoaded && _userPets.isEmpty) {
      return _buildPetFlowEmptyFallback();
    }
    // Loading pets: quiet spinner, navy bg — matches the rest of the widget.
    if (!_petsLoaded) {
      return _buildPetFlowLoading();
    }

    // If exactly one pet AND none selected yet, auto-select.
    if (_selectedPet == null && _userPets.length == 1) {
      // Defer to the next frame so we don't setState during build.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _selectedPet == null && _userPets.length == 1) {
          setState(() {
            _selectedPet = _userPets.first;
            // Skip past Step 1 since it's been auto-resolved.
            _petPageIndex = 1;
          });
        }
      });
    }

    final pages = _buildPetPages();
    // Clamp index in case pages list shrank (e.g., user went back and
    // deselected the pet — Step 1 is always present).
    final idx = _petPageIndex.clamp(0, pages.length - 1);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: wrapWithConstraints(
        child: Container(
          width: widget.width,
          height: widget.height,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [joviNavy, joviNavy, joviNavyDark],
            ),
          ),
          child: SafeArea(
            child: Column(
              children: [
                _buildPetHeader(idx, pages.length),
                Expanded(
                  child: AnimatedSwitcher(
                    duration: _reduceMotion ? Duration.zero : _Motion.select,
                    switchInCurve: Curves.easeOutCubic,
                    switchOutCurve: Curves.easeInCubic,
                    child: KeyedSubtree(
                      key: ValueKey('pet-page-$idx'),
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.fromLTRB(20, 6, 20, 24),
                        child: pages[idx],
                      ),
                    ),
                  ),
                ),
                _buildPetNavBar(idx, pages.length),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─── Pet flow: loading / empty fallbacks ─────────────────────────────

  Widget _buildPetFlowLoading() {
    return Container(
      width: widget.width,
      height: widget.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [joviNavy, joviNavyDark],
        ),
      ),
      child: const Center(
        child: SizedBox(
          width: 30,
          height: 30,
          child: CircularProgressIndicator(
            strokeWidth: 2.5,
            valueColor: AlwaysStoppedAnimation<Color>(Color(0xFFA78BFA)),
          ),
        ),
      ),
    );
  }

  Widget _buildPetFlowEmptyFallback() {
    return Container(
      width: widget.width,
      height: widget.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [joviNavy, joviNavyDark],
        ),
      ),
      child: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 82,
                  height: 82,
                  decoration: BoxDecoration(
                    color: const Color(0xFFA78BFA).withOpacity(0.12),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: const Color(0xFFA78BFA).withOpacity(0.3),
                      width: 1,
                    ),
                  ),
                  child: const Icon(Icons.pets_rounded,
                      color: Color(0xFFA78BFA), size: 38),
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
                  'Add a pet now to request a vet visit.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 13.5,
                    fontWeight: FontWeight.w500,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 20),
                _petAddPetButton(),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: _clearFlowMode,
                  child: Text(
                    'Back to chooser',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
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

  Widget _petAddPetButton() {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: _openPetProfilesFromPetFlow,
        borderRadius: BorderRadius.circular(13),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 13),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFA78BFA), Color(0xFF8B6EE8)],
            ),
            borderRadius: BorderRadius.circular(13),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFA78BFA).withOpacity(0.4),
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
    );
  }

  void _openPetProfilesFromPetFlow() {
    const routes = ['petPro', 'petProfiles', 'PetProfiles', 'pet_profiles'];
    for (final r in routes) {
      try {
        context.push('/$r');
        return;
      } catch (_) {
        continue;
      }
    }
  }

  // ─── Pet flow: header + nav bar (shared across all steps) ────────────

  Widget _buildPetHeader(int currentIdx, int totalPages) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 10, 20, 12),
      child: Row(
        children: [
          // Back/switch — returns to flow chooser.
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: _clearFlowMode,
              borderRadius: BorderRadius.circular(22),
              child: Semantics(
                label: 'Back',
                button: true,
                child: Container(
                  width: 40,
                  height: 40,
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
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Request Vet Care',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    const Icon(Icons.pets_rounded,
                        color: Color(0xFFA78BFA), size: 12),
                    const SizedBox(width: 5),
                    Text(
                      'Step ${currentIdx + 1} of $totalPages',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.2,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          // Progress pips (compact visual progress indicator).
          _buildPetProgressPips(currentIdx, totalPages),
        ],
      ),
    );
  }

  Widget _buildPetProgressPips(int currentIdx, int totalPages) {
    // Show at most 8 pips; collapse to a simple fraction beyond that.
    if (totalPages > 8) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: Colors.white.withOpacity(0.12),
            width: 0.8,
          ),
        ),
        child: Text(
          '${currentIdx + 1}/$totalPages',
          style: TextStyle(
            color: Colors.white.withOpacity(0.8),
            fontSize: 11,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.2,
          ),
        ),
      );
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(totalPages, (i) {
        final active = i == currentIdx;
        final done = i < currentIdx;
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 2),
          width: active ? 18 : 6,
          height: 6,
          decoration: BoxDecoration(
            color: active
                ? const Color(0xFFA78BFA)
                : (done
                    ? const Color(0xFFA78BFA).withOpacity(0.4)
                    : Colors.white.withOpacity(0.15)),
            borderRadius: BorderRadius.circular(3),
          ),
        );
      }),
    );
  }

  Widget _buildPetNavBar(int currentIdx, int totalPages) {
    final canGoBack = currentIdx > 0;
    final canGoNext = _petCanAdvance(currentIdx);
    final isLast = currentIdx == totalPages - 1;
    return Container(
      padding: EdgeInsets.fromLTRB(
        20,
        12,
        20,
        MediaQuery.of(context).padding.bottom > 0 ? 6 : 18,
      ),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(
            color: Colors.white.withOpacity(0.06),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          if (canGoBack)
            Expanded(
              child: _petNavSecondaryButton(
                label: 'Back',
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() => _petPageIndex--);
                },
              ),
            ),
          if (canGoBack) const SizedBox(width: 10),
          Expanded(
            flex: canGoBack ? 2 : 1,
            child: _petNavPrimaryButton(
              label: isLast ? 'Submit' : 'Continue',
              enabled: canGoNext,
              onTap: canGoNext
                  ? () {
                      HapticFeedback.selectionClick();
                      if (isLast) {
                        _submitPetRequest();
                      } else {
                        setState(() => _petPageIndex++);
                      }
                    }
                  : null,
            ),
          ),
        ],
      ),
    );
  }

  Widget _petNavSecondaryButton({
    required String label,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          height: 48,
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: Colors.white.withOpacity(0.14),
              width: 0.8,
            ),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.9),
              fontSize: 14,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.1,
            ),
          ),
        ),
      ),
    );
  }

  Widget _petNavPrimaryButton({
    required String label,
    required bool enabled,
    VoidCallback? onTap,
  }) {
    return Opacity(
      opacity: enabled ? 1.0 : 0.45,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(14),
          child: Container(
            height: 48,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFA78BFA), Color(0xFF8B6EE8)],
              ),
              borderRadius: BorderRadius.circular(14),
              boxShadow: enabled
                  ? [
                      BoxShadow(
                        color: const Color(0xFFA78BFA).withOpacity(0.4),
                        blurRadius: 14,
                        offset: const Offset(0, 5),
                      ),
                    ]
                  : null,
            ),
            alignment: Alignment.center,
            child: Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 14,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.2,
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// Returns whether the user has enough info to advance past the given step.
  bool _petCanAdvance(int stepIdx) {
    switch (stepIdx) {
      case 0: // Pet selector
        if (_selectedPet == null) return false;
        return _petMissingFields(_selectedPet!).isEmpty;
      case 1: // Visit type
        return _petVisitType != null;
      case 2: // Clinic
        return _petSelectedClinic != null;
      case 3: // Date + time
        return _petSelectedDate != null && _petSelectedTime != null;
      case 4: // Symptom
        if (_petSelectedSymptom == null) return false;
        if (_petSelectedSymptom == 'Other') {
          return _petSelectedSymptomOtherText != null &&
              _petSelectedSymptomOtherText!.trim().isNotEmpty;
        }
        return true;
      case 5: // Duration
        return _petSymptomDuration != null;
      case 6: // Details (optional; always allow advancing to confirmation)
        return true;
      case 7: // Confirmation — the submit button handles its own guard.
        // Return true so the Continue button renders as Submit (enabled).
        return !_petSubmitting;
      default:
        return false;
    }
  }

  /// Returns a list of missing required fields for this pet.
  /// Required: name (always), type (always), breed, weightLbs, dateOfBirth.
  List<String> _petMissingFields(Map<String, dynamic> pet) {
    final missing = <String>[];
    // Weight — check weightLbs OR weight_lbs OR weight (various field names).
    final w = pet['weightLbs'] ?? pet['weight_lbs'] ?? pet['weight'];
    if (w == null || (w is String && w.trim().isEmpty)) {
      missing.add('weight');
    }
    // DOB — multiple possible keys; any one of them counts.
    final dob = pet['dateOfBirth'] ??
        pet['date_of_birth'] ??
        pet['dob'] ??
        pet['birthdate'];
    if (dob == null || (dob is String && dob.trim().isEmpty)) {
      missing.add('date of birth');
    }
    // Breed.
    final breed = pet['breed'];
    if (breed == null || (breed is String && breed.trim().isEmpty)) {
      missing.add('breed');
    }
    return missing;
  }

  // ─── Pet flow: page builder ──────────────────────────────────────────

  List<Widget> _buildPetPages() {
    final pages = <Widget>[];

    // Step 1: Pet selector
    pages.add(_buildPetStepPetSelector());

    // Gate: need a complete pet profile before proceeding.
    final petReady =
        _selectedPet != null && _petMissingFields(_selectedPet!).isEmpty;
    if (!petReady) return pages;

    // Step 2: Visit type
    pages.add(_buildPetStepVisitType());
    if (_petVisitType == null) return pages;

    // Step 3: Clinic selection
    pages.add(_buildPetStepClinic());
    if (_petSelectedClinic == null) return pages;

    // Step 4: Date & time
    pages.add(_buildPetStepDateTime());
    if (_petSelectedDate == null || _petSelectedTime == null) return pages;

    // Step 5: Symptom / reason (species-aware)
    pages.add(_buildPetStepSymptom());
    if (_petSelectedSymptom == null) return pages;
    // If "Other" was picked, require free-text before advancing.
    if (_petSelectedSymptom == 'Other' &&
        (_petSelectedSymptomOtherText == null ||
            _petSelectedSymptomOtherText!.trim().isEmpty)) {
      return pages;
    }

    // Step 6: Duration
    pages.add(_buildPetStepDuration());
    if (_petSymptomDuration == null) return pages;

    // Step 7: Details (optional — no gate for advancing to confirmation)
    pages.add(_buildPetStepDetails());

    // Step 8: Confirmation / review — always shown last
    pages.add(_buildPetStepConfirmation());

    return pages;
  }

  // ─── Pet Step 1: Pet Selector ────────────────────────────────────────

  Widget _buildPetStepPetSelector() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildPetStepTitle(
          icon: Icons.pets_rounded,
          title: 'Which pet?',
          subtitle: 'Pick the pet this visit is for.',
        ),
        const SizedBox(height: 18),
        // List pets as tappable cards.
        ..._userPets.map((pet) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _buildPetSelectorCard(pet),
            )),
        const SizedBox(height: 8),
        // Add-a-pet affordance at the bottom for users who want another.
        Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: _openPetProfilesFromPetFlow,
            borderRadius: BorderRadius.circular(14),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.04),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: Colors.white.withOpacity(0.1),
                  width: 0.8,
                  style: BorderStyle.solid,
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      color: const Color(0xFFA78BFA).withOpacity(0.14),
                      borderRadius: BorderRadius.circular(11),
                    ),
                    child: const Icon(Icons.add_rounded,
                        color: Color(0xFFA78BFA), size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'Add another pet',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14.5,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.2,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Register a new pet to your account',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    Icons.chevron_right_rounded,
                    color: Colors.white.withOpacity(0.35),
                    size: 22,
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPetSelectorCard(Map<String, dynamic> pet) {
    final isSelected =
        _selectedPet != null && (_getPetId(pet) == _getPetId(_selectedPet!));
    final missing = _petMissingFields(pet);
    final hasGaps = missing.isNotEmpty;
    final name = (pet['name'] as String?) ?? 'Unnamed';
    final breed = (pet['breed'] as String?) ?? '';
    final type = _petTypeLabel(pet);
    final photoUrl = pet['photo_url'] as String? ?? pet['photoUrl'] as String?;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() {
            _selectedPet = pet;
            // If they tap a profile-complete pet, advance automatically
            // (one less tap for the happy path).
            if (missing.isEmpty) {
              // Don't auto-advance — respect the user's tempo. They'll
              // tap Continue when ready. Auto-advancing is too aggressive
              // for users who might be reviewing their pets first.
            }
          });
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isSelected
                ? const Color(0xFFA78BFA).withOpacity(0.14)
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isSelected
                  ? const Color(0xFFA78BFA).withOpacity(0.5)
                  : Colors.white.withOpacity(0.12),
              width: isSelected ? 1.5 : 1,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: const Color(0xFFA78BFA).withOpacity(0.2),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: Column(
            children: [
              Row(
                children: [
                  _buildPetAvatar(photoUrl, name, type),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          name,
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
                          breed.isNotEmpty ? '$type • $breed' : type,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                  if (isSelected)
                    const Icon(Icons.check_circle_rounded,
                        color: Color(0xFFA78BFA), size: 22)
                  else
                    Icon(
                      Icons.radio_button_unchecked_rounded,
                      color: Colors.white.withOpacity(0.25),
                      size: 22,
                    ),
                ],
              ),
              // Missing-profile warning shown on the selected pet.
              if (isSelected && hasGaps) ...[
                const SizedBox(height: 12),
                _buildPetProfileGapWarning(missing),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPetProfileGapWarning(List<String> missing) {
    final missingText = missing.length == 1
        ? missing.first
        : missing.length == 2
            ? '${missing[0]} and ${missing[1]}'
            : '${missing.sublist(0, missing.length - 1).join(', ')}, and ${missing.last}';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: joviGold.withOpacity(0.1),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: joviGold.withOpacity(0.35),
          width: 0.8,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline_rounded, color: joviGold, size: 15),
              const SizedBox(width: 6),
              const Text(
                'Profile needs a bit more info',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 12.5,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.1,
                ),
              ),
            ],
          ),
          const SizedBox(height: 5),
          Text(
            "Your vet needs $missingText before we can submit this request. It takes ~30 seconds to add.",
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 11.5,
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 10),
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: _openPetProfilesFromPetFlow,
              borderRadius: BorderRadius.circular(10),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(
                  color: joviGold.withOpacity(0.9),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.edit_rounded, color: joviNavy, size: 13),
                    SizedBox(width: 5),
                    Text(
                      'Complete profile',
                      style: TextStyle(
                        color: joviNavy,
                        fontSize: 12,
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
    );
  }

  Widget _buildPetAvatar(String? photoUrl, String name, String type) {
    final hasPhoto = photoUrl != null && photoUrl.isNotEmpty;
    return Container(
      width: 48,
      height: 48,
      decoration: BoxDecoration(
        color: const Color(0xFFA78BFA).withOpacity(0.18),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: const Color(0xFFA78BFA).withOpacity(0.3),
          width: 1,
        ),
        image: hasPhoto
            ? DecorationImage(
                image: NetworkImage(photoUrl),
                fit: BoxFit.cover,
                onError: (_, __) {},
              )
            : null,
      ),
      child: hasPhoto
          ? null
          : Center(
              child: Text(
                name.isNotEmpty ? name.substring(0, 1).toUpperCase() : '?',
                style: const TextStyle(
                  color: Color(0xFFA78BFA),
                  fontSize: 19,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
    );
  }

  String _petTypeLabel(Map<String, dynamic> pet) {
    final raw = (pet['type'] as String?)?.toLowerCase() ??
        (pet['species'] as String?)?.toLowerCase();
    switch (raw) {
      case 'dog':
        return 'Dog';
      case 'cat':
        return 'Cat';
      case 'other':
      case null:
      case '':
        return 'Pet';
      default:
        // Capitalize unknown values gracefully.
        return '${raw![0].toUpperCase()}${raw.substring(1)}';
    }
  }

  String _getPetId(Map<String, dynamic> pet) {
    return (pet['petId'] as String?) ??
        (pet['id'] as String?) ??
        'legacy_${pet['name'] ?? 'unnamed'}';
  }

  /// Shared step header (icon + title + subtitle) — matches the human
  /// flow's `_buildStep` visual treatment.
  Widget _buildPetStepTitle({
    required IconData icon,
    required String title,
    required String subtitle,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFA78BFA), Color(0xFF8B6EE8)],
            ),
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFA78BFA).withOpacity(0.35),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Icon(icon, color: Colors.white, size: 22),
        ),
        const SizedBox(height: 14),
        Text(
          title,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 22,
            fontWeight: FontWeight.w900,
            letterSpacing: -0.5,
            height: 1.1,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: TextStyle(
            color: Colors.white.withOpacity(0.6),
            fontSize: 13.5,
            fontWeight: FontWeight.w500,
            height: 1.45,
          ),
        ),
      ],
    );
  }

  // ─── Pet Step 2: Visit Type ──────────────────────────────────────────

  Widget _buildPetStepVisitType() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildPetStepTitle(
          icon: Icons.medical_services_rounded,
          title: 'What kind of visit?',
          subtitle: 'We will use this to route your request to the right vet.',
        ),
        const SizedBox(height: 18),
        _buildPetVisitTypeCard(
          type: 'Wellness',
          icon: Icons.spa_rounded,
          title: 'Wellness visit',
          subtitle:
              'Routine care, vaccinations, diagnostics, and chronic-condition check-ins.',
          accent: joviMint,
          accentDark: joviMintDark,
        ),
        const SizedBox(height: 10),
        _buildPetVisitTypeCard(
          type: 'Sick or Injured',
          icon: Icons.healing_rounded,
          title: 'Sick or injured',
          subtitle:
              'Urgent concerns: vomiting, diarrhea, pain, behavior changes, or injuries.',
          accent: joviCoral,
          accentDark: joviCoralDark,
        ),
      ],
    );
  }

  Widget _buildPetVisitTypeCard({
    required String type,
    required IconData icon,
    required String title,
    required String subtitle,
    required Color accent,
    required Color accentDark,
  }) {
    final isSelected = _petVisitType == type;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() {
            _petVisitType = type;
          });
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isSelected
                ? accent.withOpacity(0.14)
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isSelected
                  ? accent.withOpacity(0.55)
                  : Colors.white.withOpacity(0.12),
              width: isSelected ? 1.5 : 1,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: accent.withOpacity(0.22),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: [accent, accentDark]),
                  borderRadius: BorderRadius.circular(13),
                  boxShadow: [
                    BoxShadow(
                      color: accent.withOpacity(0.35),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Icon(icon, color: Colors.white, size: 22),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      subtitle,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.6),
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              if (isSelected)
                Icon(Icons.check_circle_rounded, color: accent, size: 22)
              else
                Icon(
                  Icons.radio_button_unchecked_rounded,
                  color: Colors.white.withOpacity(0.25),
                  size: 22,
                ),
            ],
          ),
        ),
      ),
    );
  }

  // ─── Pet Step 3: Clinic Selection ────────────────────────────────────

  Widget _buildPetStepClinic() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildPetStepTitle(
          icon: Icons.place_rounded,
          title: 'Which clinic?',
          subtitle: 'Pick the location closest to you.',
        ),
        const SizedBox(height: 18),
        ..._clinicLocations.entries.map((entry) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _buildPetClinicCard(entry.key, entry.value),
            )),
      ],
    );
  }

  Widget _buildPetClinicCard(String name, Map<String, dynamic> info) {
    final isSelected = _petSelectedClinic == name;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() => _petSelectedClinic = name);
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isSelected
                ? const Color(0xFFA78BFA).withOpacity(0.14)
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isSelected
                  ? const Color(0xFFA78BFA).withOpacity(0.55)
                  : Colors.white.withOpacity(0.12),
              width: isSelected ? 1.5 : 1,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: const Color(0xFFA78BFA).withOpacity(0.22),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: isSelected
                          ? const Color(0xFFA78BFA).withOpacity(0.25)
                          : const Color(0xFFA78BFA).withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(
                      Icons.location_on_rounded,
                      color: Color(0xFFA78BFA),
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.3,
                      ),
                    ),
                  ),
                  if (isSelected)
                    const Icon(Icons.check_circle_rounded,
                        color: Color(0xFFA78BFA), size: 22)
                  else
                    Icon(
                      Icons.radio_button_unchecked_rounded,
                      color: Colors.white.withOpacity(0.25),
                      size: 22,
                    ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                info['fullAddress'] as String? ?? '',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.65),
                  fontSize: 12.5,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              ),
              if ((info['phone'] as String?)?.isNotEmpty == true) ...[
                const SizedBox(height: 4),
                Text(
                  info['phone'] as String,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.2,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  // ─── Pet Step 4: Date & Time ─────────────────────────────────────────
  //
  // Premium-feeling picker: horizontal scrollable date rail (next 14 days,
  // weekdays only unless we're inside a weekend) + a grid of 30-min time
  // slots from 8:00 to 17:30. Intentionally simpler than the human flow's
  // calendar — most vet appointments get scheduled within a 2-week window
  // and the full calendar would be overkill for the pet use case.

  Widget _buildPetStepDateTime() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildPetStepTitle(
          icon: Icons.calendar_today_rounded,
          title: 'When?',
          subtitle: 'Pick a preferred date and time. The clinic will confirm.',
        ),
        const SizedBox(height: 20),
        _buildPetDateRail(),
        const SizedBox(height: 18),
        if (_petSelectedDate != null) _buildPetTimeGrid(),
      ],
    );
  }

  Widget _buildPetDateRail() {
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day);
    final dates =
        List<DateTime>.generate(14, (i) => start.add(Duration(days: i)));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Date',
          style: TextStyle(
            color: Colors.white.withOpacity(0.85),
            fontSize: 12.5,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.6,
          ),
        ),
        const SizedBox(height: 10),
        SizedBox(
          height: 78,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: dates.length,
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemBuilder: (ctx, i) => _buildPetDateChip(dates[i]),
          ),
        ),
      ],
    );
  }

  Widget _buildPetDateChip(DateTime date) {
    final isSelected = _petSelectedDate != null &&
        _petSelectedDate!.year == date.year &&
        _petSelectedDate!.month == date.month &&
        _petSelectedDate!.day == date.day;
    const weekdayNames = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
    final dow = weekdayNames[date.weekday - 1];
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() {
            _petSelectedDate = date;
            // Clear previously selected time if they change dates.
            _petSelectedTime = null;
          });
        },
        borderRadius: BorderRadius.circular(14),
        child: Container(
          width: 62,
          decoration: BoxDecoration(
            color: isSelected
                ? const Color(0xFFA78BFA).withOpacity(0.18)
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isSelected
                  ? const Color(0xFFA78BFA).withOpacity(0.6)
                  : Colors.white.withOpacity(0.12),
              width: isSelected ? 1.5 : 1,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: const Color(0xFFA78BFA).withOpacity(0.25),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                dow,
                style: TextStyle(
                  color: isSelected
                      ? const Color(0xFFA78BFA)
                      : Colors.white.withOpacity(0.55),
                  fontSize: 10.5,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.8,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                '${date.day}',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                _petMonthAbbrev(date.month),
                style: TextStyle(
                  color: Colors.white.withOpacity(0.5),
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _petMonthAbbrev(int m) {
    const months = [
      'JAN',
      'FEB',
      'MAR',
      'APR',
      'MAY',
      'JUN',
      'JUL',
      'AUG',
      'SEP',
      'OCT',
      'NOV',
      'DEC',
    ];
    if (m < 1 || m > 12) return '';
    return months[m - 1];
  }

  Widget _buildPetTimeGrid() {
    // Generate half-hour slots from 8:00 to 17:30 inclusive.
    final slots = <String>[];
    for (int h = 8; h <= 17; h++) {
      slots.add(_formatTimeSlot(h, 0));
      slots.add(_formatTimeSlot(h, 30));
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Time',
          style: TextStyle(
            color: Colors.white.withOpacity(0.85),
            fontSize: 12.5,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.6,
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: slots.map(_buildPetTimeChip).toList(),
        ),
      ],
    );
  }

  String _formatTimeSlot(int hour24, int minute) {
    final hour12 = hour24 == 0 ? 12 : (hour24 > 12 ? hour24 - 12 : hour24);
    final ampm = hour24 < 12 ? 'AM' : 'PM';
    final mm = minute.toString().padLeft(2, '0');
    return '$hour12:$mm $ampm';
  }

  Widget _buildPetTimeChip(String time) {
    final isSelected = _petSelectedTime == time;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() => _petSelectedTime = time);
        },
        borderRadius: BorderRadius.circular(11),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
          decoration: BoxDecoration(
            color: isSelected
                ? const Color(0xFFA78BFA).withOpacity(0.18)
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(11),
            border: Border.all(
              color: isSelected
                  ? const Color(0xFFA78BFA).withOpacity(0.6)
                  : Colors.white.withOpacity(0.12),
              width: isSelected ? 1.5 : 1,
            ),
          ),
          child: Text(
            time,
            style: TextStyle(
              color: isSelected ? Colors.white : Colors.white.withOpacity(0.8),
              fontSize: 12.5,
              fontWeight: isSelected ? FontWeight.w800 : FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
        ),
      ),
    );
  }

  // ─── Pet Step 5: Symptom / Reason (species-aware) ────────────────────

  Widget _buildPetStepSymptom() {
    final species = _currentPetSpecies();
    final key = '$_petVisitType|$species';
    final symptoms = _petSymptomsByKey[key] ?? [];
    final isWellness = _petVisitType == 'Wellness';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildPetStepTitle(
          icon: isWellness
              ? Icons.check_circle_outline_rounded
              : Icons.healing_rounded,
          title: isWellness ? 'What is the visit for?' : 'What is going on?',
          subtitle: isWellness
              ? 'Pick the wellness reason closest to your need.'
              : 'Pick what best describes the concern.',
        ),
        const SizedBox(height: 18),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: symptoms.map((s) => _buildPetSymptomChip(s)).toList(),
        ),
        // "Other" reveals a text field.
        if (_petSelectedSymptom == 'Other') ...[
          const SizedBox(height: 14),
          _buildPetOtherSymptomField(),
        ],
      ],
    );
  }

  String _currentPetSpecies() {
    final pet = _selectedPet;
    if (pet == null) return 'other';
    final raw = (pet['type'] as String?)?.toLowerCase() ??
        (pet['species'] as String?)?.toLowerCase();
    if (raw == 'dog' || raw == 'cat') return raw!;
    return 'other';
  }

  Widget _buildPetSymptomChip(String symptom) {
    final isSelected = _petSelectedSymptom == symptom;
    final isOther = symptom == 'Other';
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() {
            _petSelectedSymptom = symptom;
            // Clear the "Other" free-text if the user switches away from Other.
            if (!isOther) {
              _petSelectedSymptomOtherText = null;
              _petOtherSymptomCtrl.clear();
            }
          });
        },
        borderRadius: BorderRadius.circular(11),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
          decoration: BoxDecoration(
            color: isSelected
                ? const Color(0xFFA78BFA).withOpacity(0.2)
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(11),
            border: Border.all(
              color: isSelected
                  ? const Color(0xFFA78BFA).withOpacity(0.6)
                  : Colors.white.withOpacity(0.12),
              width: isSelected ? 1.4 : 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (isSelected) ...[
                const Icon(Icons.check_rounded,
                    color: Color(0xFFA78BFA), size: 14),
                const SizedBox(width: 5),
              ],
              Text(
                symptom,
                style: TextStyle(
                  color:
                      isSelected ? Colors.white : Colors.white.withOpacity(0.8),
                  fontSize: 12.5,
                  fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                  letterSpacing: 0.1,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPetOtherSymptomField() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(
          color: const Color(0xFFA78BFA).withOpacity(0.4),
          width: 1,
        ),
      ),
      child: TextField(
        controller: _petOtherSymptomCtrl,
        onChanged: (v) {
          setState(() => _petSelectedSymptomOtherText = v);
        },
        maxLines: 3,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontWeight: FontWeight.w500,
          height: 1.4,
        ),
        cursorColor: const Color(0xFFA78BFA),
        decoration: InputDecoration(
          hintText: 'Tell us what is going on in a few words…',
          hintStyle: TextStyle(
            color: Colors.white.withOpacity(0.4),
            fontSize: 13.5,
            fontWeight: FontWeight.w500,
          ),
          border: InputBorder.none,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        ),
      ),
    );
  }

  // ─── Pet Step 6: Duration ────────────────────────────────────────────

  Widget _buildPetStepDuration() {
    final isWellness = _petVisitType == 'Wellness';
    final title = isWellness
        ? 'How soon is this needed?'
        : 'How long has this been going on?';
    final subtitle = isWellness
        ? 'We will prioritize urgency where we can.'
        : 'Timing helps the vet triage properly.';
    final options = isWellness
        ? [
            _PetDurationOption('Within a week', Icons.hourglass_top_rounded,
                'Flexible timing', joviMint),
            _PetDurationOption(
                'Within 2-4 weeks',
                Icons.hourglass_bottom_rounded,
                'Routine scheduling',
                joviMintDark),
            _PetDurationOption(
                'Next available', Icons.schedule_rounded, 'No rush', joviGold),
          ]
        : [
            _PetDurationOption('Less than 24 hours',
                Icons.hourglass_top_rounded, 'Just started', joviGold),
            _PetDurationOption('1-3 days', Icons.hourglass_bottom_rounded,
                'Ongoing', joviCoralLight),
            _PetDurationOption('More than 3 days', Icons.schedule_rounded,
                'Has been persisting', joviCoral),
          ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildPetStepTitle(
          icon: Icons.schedule_rounded,
          title: title,
          subtitle: subtitle,
        ),
        const SizedBox(height: 18),
        ...options.map((o) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _buildPetDurationCard(o),
            )),
      ],
    );
  }

  Widget _buildPetDurationCard(_PetDurationOption opt) {
    final isSelected = _petSymptomDuration == opt.label;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() => _petSymptomDuration = opt.label);
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: isSelected
                ? opt.accent.withOpacity(0.14)
                : Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isSelected
                  ? opt.accent.withOpacity(0.55)
                  : Colors.white.withOpacity(0.12),
              width: isSelected ? 1.5 : 1,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: opt.accent.withOpacity(0.25),
                      blurRadius: 14,
                      offset: const Offset(0, 4),
                    ),
                  ]
                : null,
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: opt.accent.withOpacity(isSelected ? 0.22 : 0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(opt.icon, color: opt.accent, size: 20),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      opt.label,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.3,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      opt.caption,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              if (isSelected)
                Icon(Icons.check_circle_rounded, color: opt.accent, size: 22)
              else
                Icon(
                  Icons.radio_button_unchecked_rounded,
                  color: Colors.white.withOpacity(0.25),
                  size: 22,
                ),
            ],
          ),
        ),
      ),
    );
  }

  // ─── Pet Step 7: Details (free-text, optional) ───────────────────────

  Widget _buildPetStepDetails() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildPetStepTitle(
          icon: Icons.edit_note_rounded,
          title: 'Anything else?',
          subtitle:
              'Optional: add any context that might help the vet (changes in diet, recent events, other pets affected, etc.).',
        ),
        const SizedBox(height: 18),
        Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: Colors.white.withOpacity(0.12),
              width: 1,
            ),
          ),
          child: TextField(
            controller: _petDetailsCtrl,
            maxLines: 6,
            minLines: 4,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.w500,
              height: 1.4,
            ),
            cursorColor: const Color(0xFFA78BFA),
            decoration: InputDecoration(
              hintText:
                  'For example: "Started limping after a walk yesterday. No visible wound. Eating normally."',
              hintStyle: TextStyle(
                color: Colors.white.withOpacity(0.4),
                fontSize: 13,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
              border: InputBorder.none,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          'This field is optional. Tap Continue to review your request.',
          style: TextStyle(
            color: Colors.white.withOpacity(0.45),
            fontSize: 11.5,
            fontWeight: FontWeight.w600,
            fontStyle: FontStyle.italic,
          ),
        ),
      ],
    );
  }

  // ─── Pet Step 8: Confirmation / Review ───────────────────────────────
  //
  // Final screen before submission. Shows a neat summary of every choice
  // the user made, lets them tap any section to jump back and edit, and
  // presents the Submit button (wired in the nav bar).

  Widget _buildPetStepConfirmation() {
    final pet = _selectedPet;
    final petName = (pet?['name'] as String?) ?? 'Your pet';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildPetStepTitle(
          icon: Icons.check_circle_outline_rounded,
          title: 'Review and submit',
          subtitle:
              'Confirm these details. We will send the request to the vet on your behalf.',
        ),
        const SizedBox(height: 18),
        // Pet summary hero — visually anchors who this is for.
        _buildPetConfirmationHero(pet),
        const SizedBox(height: 12),
        _buildPetConfirmationRow(
          icon: Icons.medical_services_rounded,
          label: 'Visit type',
          value: _petVisitType ?? '—',
          jumpToStep: 1,
        ),
        _buildPetConfirmationRow(
          icon: Icons.place_rounded,
          label: 'Clinic',
          value: _petSelectedClinic ?? '—',
          valueSecondary: _petSelectedClinic != null
              ? (_clinicLocations[_petSelectedClinic!]?['fullAddress']
                  as String?)
              : null,
          jumpToStep: 2,
        ),
        _buildPetConfirmationRow(
          icon: Icons.calendar_today_rounded,
          label: 'Date & time',
          value: _formatPetDateTime(),
          jumpToStep: 3,
        ),
        _buildPetConfirmationRow(
          icon: _petVisitType == 'Wellness'
              ? Icons.spa_rounded
              : Icons.healing_rounded,
          label: _petVisitType == 'Wellness' ? 'Reason' : 'Concern',
          value: _petSelectedSymptom == 'Other'
              ? (_petSelectedSymptomOtherText ?? 'Other')
              : (_petSelectedSymptom ?? '—'),
          jumpToStep: 4,
        ),
        _buildPetConfirmationRow(
          icon: Icons.schedule_rounded,
          label: _petVisitType == 'Wellness' ? 'Timing' : 'Duration',
          value: _petSymptomDuration ?? '—',
          jumpToStep: 5,
        ),
        if (_petDetailsCtrl.text.trim().isNotEmpty)
          _buildPetConfirmationRow(
            icon: Icons.edit_note_rounded,
            label: 'Additional details',
            value: _petDetailsCtrl.text.trim(),
            jumpToStep: 6,
            isLongText: true,
          ),
        const SizedBox(height: 14),
        // Friendly reassurance before the submit button.
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFFA78BFA).withOpacity(0.08),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: const Color(0xFFA78BFA).withOpacity(0.25),
              width: 0.8,
            ),
          ),
          child: Row(
            children: [
              const Icon(Icons.lock_rounded,
                  color: Color(0xFFA78BFA), size: 15),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Your request goes directly to the clinic. ${petName.isNotEmpty ? petName + "'s" : "Your pet\'s"} info stays private to your vet team.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.72),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w500,
                    height: 1.35,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPetConfirmationHero(Map<String, dynamic>? pet) {
    if (pet == null) return const SizedBox.shrink();
    final name = (pet['name'] as String?) ?? 'Unnamed';
    final breed = (pet['breed'] as String?) ?? '';
    final type = _petTypeLabel(pet);
    final photoUrl = pet['photo_url'] as String? ?? pet['photoUrl'] as String?;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            const Color(0xFFA78BFA).withOpacity(0.18),
            const Color(0xFF8B6EE8).withOpacity(0.1),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFFA78BFA).withOpacity(0.35),
          width: 1,
        ),
      ),
      child: Row(
        children: [
          _buildPetAvatar(photoUrl, name, type),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w900,
                    letterSpacing: -0.4,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  breed.isNotEmpty ? '$type • $breed' : type,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.7),
                    fontSize: 12.5,
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

  Widget _buildPetConfirmationRow({
    required IconData icon,
    required String label,
    required String value,
    String? valueSecondary,
    required int jumpToStep,
    bool isLongText = false,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            HapticFeedback.selectionClick();
            setState(() => _petPageIndex = jumpToStep);
          },
          borderRadius: BorderRadius.circular(13),
          child: Container(
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(13),
              border: Border.all(
                color: Colors.white.withOpacity(0.1),
                width: 0.8,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: const Color(0xFFA78BFA).withOpacity(0.14),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(icon, color: const Color(0xFFA78BFA), size: 16),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        label,
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.5),
                          fontSize: 10.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.6,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        value,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2,
                          height: 1.3,
                        ),
                        maxLines: isLongText ? 4 : 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (valueSecondary != null &&
                          valueSecondary.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          valueSecondary,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 11.5,
                            fontWeight: FontWeight.w500,
                            height: 1.3,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Icon(
                  Icons.edit_rounded,
                  color: Colors.white.withOpacity(0.35),
                  size: 14,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _formatPetDateTime() {
    if (_petSelectedDate == null) return '—';
    final d = _petSelectedDate!;
    const weekday = [
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
      'Sunday',
    ];
    const months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December',
    ];
    final dateText =
        '${weekday[d.weekday - 1]}, ${months[d.month - 1]} ${d.day}';
    final timeText = _petSelectedTime ?? '';
    return timeText.isEmpty ? dateText : '$dateText · $timeText';
  }

  // ─── Pet Flow: Firestore Submission ─────────────────────────────────

  Future<void> _submitPetRequest() async {
    if (_petSubmitting) return; // prevent double-submit
    HapticFeedback.mediumImpact();
    setState(() => _petSubmitting = true);
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        throw Exception('Not signed in. Please log in and try again.');
      }
      final pet = _selectedPet;
      if (pet == null) {
        throw Exception('No pet selected.');
      }

      // Build the scheduled ISO date (YYYY-MM-DDT00:00:00) to match the
      // human flow's `appointmentDate` field convention.
      final d = _petSelectedDate!;
      final dateString =
          '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}T00:00:00';

      // Pull pet fields defensively — different sources use different keys.
      final petId = _getPetId(pet);
      final petName = (pet['name'] as String?) ?? '';
      final petType =
          (pet['type'] as String?) ?? (pet['species'] as String?) ?? '';
      final petBreed = (pet['breed'] as String?) ?? '';
      final petWeight = pet['weightLbs'] ?? pet['weight_lbs'] ?? pet['weight'];
      final petDob = pet['dateOfBirth'] ??
          pet['date_of_birth'] ??
          pet['dob'] ??
          pet['birthdate'];
      final petPhotoUrl =
          (pet['photo_url'] as String?) ?? (pet['photoUrl'] as String?) ?? '';

      final symptomText = _petSelectedSymptom == 'Other'
          ? (_petSelectedSymptomOtherText ?? 'Other')
          : (_petSelectedSymptom ?? '');

      final requestData = <String, dynamic>{
        'id': _uuid.v4(),
        'userId': user.uid,
        'timezone': _localTimezoneId(),
        'audience': 'Pet',
        'visitType': _petVisitType ?? '',
        'visitMode': 'Clinic',
        'clinic': _petSelectedClinic ?? '',
        // Pet identity fields
        'petId': petId,
        'petName': petName,
        'petSpecies': petType.toString().toLowerCase(),
        'petBreed': petBreed,
        'petWeightLbs': petWeight,
        'petDateOfBirth': petDob,
        'petPhotoUrl': petPhotoUrl,
        // Visit-specific fields (match human schema names so admin tooling
        // can reuse the same queries/UI components).
        'patientName': petName, // for admin UIs that read patientName
        'symptom': symptomText,
        'symptomDuration': _petSymptomDuration ?? '',
        'details': _petDetailsCtrl.text.trim(),
        'appointmentDate': dateString,
        'appointmentTime': _petSelectedTime ?? '',
        'status': 'pending',
        'createdAt': FieldValue.serverTimestamp(),
      };

      // Remove empty-string and null values for cleaner docs.
      requestData
          .removeWhere((k, v) => v == null || (v is String && v.isEmpty));

      final docRef = await FirebaseFirestore.instance
          .collection('requests')
          .add(requestData);

      debugPrint('[PET REQUEST] Saved with ID: ${docRef.id}');

      if (!mounted) return;
      setState(() {
        _petSubmitting = false;
        _showSuccess = true;
      });
      // Reuse the human flow's animations so the success visual feels
      // consistent across the app.
      _animController.forward(from: 0);
    } catch (e) {
      debugPrint('Pet request submission failed: $e');
      if (!mounted) return;
      setState(() => _petSubmitting = false);
      _toastError('Could not submit request: ${e.toString()}');
    }
  }

  // ─── Pet Flow: Success Screen ───────────────────────────────────────

  Widget _buildPetSuccessScreen() {
    final pet = _selectedPet;
    final petName = (pet?['name'] as String?) ?? 'your pet';
    final dateStr = _formatPetDateTime();
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: wrapWithConstraints(
        child: Container(
          width: widget.width,
          height: widget.height,
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [joviNavy, joviNavy, joviNavyDark],
            ),
          ),
          child: SafeArea(
            child: FadeTransition(
              opacity: _fadeAnim,
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(28, 32, 28, 28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const SizedBox(height: 20),
                    ScaleTransition(
                      scale: _scaleAnim,
                      child: Container(
                        width: 120,
                        height: 120,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: LinearGradient(
                            colors: [joviMint, joviMintDark],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: joviMint.withOpacity(0.4),
                              blurRadius: 30,
                              offset: const Offset(0, 15),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.check_rounded,
                          size: 72,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    const SizedBox(height: 26),
                    Text(
                      'Request sent',
                      style: TextStyle(
                        color: joviMint,
                        fontSize: 32,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.8,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      "We have sent $petName's vet care request to the clinic. They will confirm your appointment shortly.",
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.8),
                        fontSize: 14.5,
                        fontWeight: FontWeight.w500,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 22),
                    // Summary card
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.06),
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: Colors.white.withOpacity(0.12),
                          width: 1,
                        ),
                      ),
                      child: Column(
                        children: [
                          _petSuccessRow(
                            Icons.pets_rounded,
                            'Pet',
                            petName,
                          ),
                          const SizedBox(height: 10),
                          _petSuccessRow(
                            Icons.place_rounded,
                            'Clinic',
                            _petSelectedClinic ?? '—',
                          ),
                          const SizedBox(height: 10),
                          _petSuccessRow(
                            Icons.calendar_today_rounded,
                            'Scheduled for',
                            dateStr,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                    // Primary action: back to home/dashboard
                    Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: () {
                          HapticFeedback.lightImpact();
                          if (Navigator.of(context).canPop()) {
                            Navigator.of(context).pop();
                          }
                        },
                        borderRadius: BorderRadius.circular(14),
                        child: Container(
                          width: double.infinity,
                          height: 52,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [Color(0xFFA78BFA), Color(0xFF8B6EE8)],
                            ),
                            borderRadius: BorderRadius.circular(14),
                            boxShadow: [
                              BoxShadow(
                                color:
                                    const Color(0xFFA78BFA).withOpacity(0.45),
                                blurRadius: 18,
                                offset: const Offset(0, 6),
                              ),
                            ],
                          ),
                          alignment: Alignment.center,
                          child: const Text(
                            'Done',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 15,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.3,
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    // Secondary: submit another request (reset pet flow)
                    TextButton(
                      onPressed: () {
                        HapticFeedback.selectionClick();
                        setState(() {
                          _resetPetFlowState();
                        });
                      },
                      child: Text(
                        'Submit another request',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.65),
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
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

  Widget _petSuccessRow(IconData icon, String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: const Color(0xFFA78BFA), size: 15),
        const SizedBox(width: 10),
        SizedBox(
          width: 88,
          child: Text(
            label,
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 11.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.4,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13.5,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.2,
            ),
          ),
        ),
      ],
    );
  }

  /// Reset the pet flow to a clean state (after successful submission, if
  /// the user wants to file another request).
  void _resetPetFlowState() {
    _selectedPet = null;
    _petVisitType = null;
    _petSelectedClinic = null;
    _petSelectedDate = null;
    _petSelectedTime = null;
    _petSelectedSymptom = null;
    _petSelectedSymptomOtherText = null;
    _petSymptomDuration = null;
    _petDetailsCtrl.clear();
    _petOtherSymptomCtrl.clear();
    _petPageIndex = 0;
    _petSubmitting = false;
    _showSuccess = false;
    // Reset animation so next submission's success screen animates fresh.
    _animController.reset();
  }

  Widget _buildHeader(int pageCount) {
    final statusBarHeight = MediaQuery.of(context).padding.top;

    return Container(
      padding: EdgeInsets.fromLTRB(
          layoutSettings.paddingH,
          statusBarHeight + 12,
          layoutSettings.paddingH,
          layoutSettings.paddingV * 0.8),
      decoration: BoxDecoration(
        color: joviNavy,
        border: Border(
          bottom: BorderSide(
            color: Colors.white.withOpacity(0.08),
            width: 1,
          ),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.15),
            blurRadius: 10,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              // Switch-to-chooser affordance — only shown when the user
              // has at least one pet registered AND isn't mid-reschedule.
              // Rescheduling is bound to an existing human request, so
              // flow-swap would discard in-progress edits.
              if (!_isRescheduleMode && _petsLoaded && _userPets.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: _clearFlowMode,
                      borderRadius: BorderRadius.circular(11),
                      child: Tooltip(
                        message: 'Switch between human and pet care',
                        child: Semantics(
                          label: 'Switch flow',
                          button: true,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 7),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.06),
                              borderRadius: BorderRadius.circular(11),
                              border: Border.all(
                                color: Colors.white.withOpacity(0.14),
                                width: 0.8,
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.swap_horiz_rounded,
                                  color: Colors.white.withOpacity(0.75),
                                  size: 14,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  'Switch',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.85),
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
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
                ),
              Expanded(
                child: Text(
                  _isRescheduleMode ? 'Reschedule Appointment' : 'Request Care',
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                    letterSpacing: -0.4,
                  ),
                ),
              ),
              Container(
                padding: EdgeInsets.symmetric(
                    horizontal: 12, vertical: layoutSettings.paddingV * 0.3),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      joviCoral.withOpacity(0.25),
                      joviCoralDark.withOpacity(0.15),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: joviCoral.withOpacity(0.4),
                    width: 1,
                  ),
                ),
                child: Text(
                  '${_pageIndex + 1}/$pageCount',
                  style: TextStyle(
                    color: joviCoral,
                    fontWeight: FontWeight.w600,
                    fontSize: layoutSettings.actionTextSize,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: 12),
          Container(
            height: 8,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(10),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(10),
              child: Stack(
                children: [
                  AnimatedFractionallySizedBox(
                    duration: _Motion.select,
                    curve: _Motion.settle,
                    alignment: Alignment.centerLeft,
                    heightFactor: 1.0,
                    widthFactor: pageCount > 0
                        ? ((_pageIndex + 1) / pageCount).clamp(0.0, 1.0)
                        : 0.0,
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [joviCoral, joviCoralDark],
                          begin: Alignment.centerLeft,
                          end: Alignment.centerRight,
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

  @override
  Widget build(BuildContext context) {
    // Until flow mode has resolved (pref read or reschedule init),
    // show a transparent loading sliver so we don't flash a wrong UI.
    if (!_flowModeInitialized) {
      return Container(
        width: widget.width,
        height: widget.height,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [joviNavy, joviNavy, joviNavyDark],
          ),
        ),
        child: const Center(
          child: SizedBox(
            width: 34,
            height: 34,
            child: CircularProgressIndicator(
              strokeWidth: 2.8,
              valueColor: AlwaysStoppedAnimation<Color>(joviCoral),
            ),
          ),
        ),
      );
    }

    // Chooser landing — user hasn't picked a flow yet (first visit,
    // or they tapped the switch affordance to come back here).
    if (_flowMode == null) {
      return _buildFlowChooser();
    }

    // Pet flow — Request Vet Care. Same structure as the human flow
    // (pet selector → visit type → clinic → date/time → symptom →
    // duration → details → confirmation) but with pet-specific content.
    if (_flowMode == 'pet') {
      return _buildPetFlow();
    }

    // Human flow — the existing Request Care pipeline.
    return _buildHumanFlow();
  }

  Widget _buildHumanFlow() {
    final pages = _buildPages();

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: wrapWithConstraints(
        child: Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [joviNavy, joviNavy, joviNavyDark],
            ),
          ),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            body: Stack(
              children: [
                Column(
                  children: [
                    _buildHeader(pages.length),
                    Expanded(
                      child: pages.isNotEmpty
                          ? PageView(
                              controller: _pageController,
                              physics: NeverScrollableScrollPhysics(),
                              onPageChanged: (i) {
                                setState(() => _pageIndex = i);
                                if (i == pages.length - 1) {
                                  _animController.forward(from: 0);
                                }
                              },
                              children: pages,
                            )
                          : Center(
                              child: CircularProgressIndicator(
                                color: joviCoral,
                              ),
                            ),
                    ),
                    Container(
                      decoration: BoxDecoration(
                        color: joviNavy,
                        border: Border(
                          top: BorderSide(
                            color: Colors.white.withOpacity(0.08),
                            width: 1,
                          ),
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.2),
                            blurRadius: 10,
                            offset: Offset(0, -2),
                          ),
                        ],
                      ),
                      padding: EdgeInsets.symmetric(
                          vertical: 12, horizontal: layoutSettings.paddingH),
                      child: SafeArea(
                        top: false,
                        child: Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: _prevPage,
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(
                                      vertical: layoutSettings.paddingV * 0.7),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  side: BorderSide(
                                      color: Colors.white.withOpacity(0.3)),
                                ),
                                child: Text(
                                  _pageIndex == 0 ? 'Cancel' : 'Back',
                                  style: TextStyle(
                                      fontSize:
                                          layoutSettings.actionTextSize + 3,
                                      color: Colors.white),
                                ),
                              ),
                            ),
                            SizedBox(width: layoutSettings.paddingH * 0.8),
                            Expanded(
                              flex: 2,
                              child: ElevatedButton(
                                onPressed: _nextPage,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: joviCoral,
                                  foregroundColor: Colors.white,
                                  padding: EdgeInsets.symmetric(
                                      vertical: layoutSettings.paddingV * 0.7),
                                  elevation: 3,
                                  shadowColor: joviCoral.withOpacity(0.5),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    if (_pageIndex == pages.length - 1)
                                      Icon(Icons.check_circle,
                                          color: Colors.white, size: 20),
                                    if (_pageIndex == pages.length - 1)
                                      SizedBox(width: 8),
                                    Text(
                                      _pageIndex == pages.length - 1
                                          ? (_isRefill()
                                              ? 'Submit Refill Request'
                                              : _isRescheduleMode
                                                  ? 'Confirm Reschedule'
                                                  : 'Confirm Appointment')
                                          : 'Continue',
                                      style: TextStyle(
                                        fontSize:
                                            layoutSettings.actionTextSize + 3,
                                        fontWeight: FontWeight.w600,
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
                  ],
                ),
                if (_isLoading)
                  Container(
                    color: Colors.black.withOpacity(0.6),
                    child: Center(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: BackdropFilter(
                          filter:
                              ui_dart.ImageFilter.blur(sigmaX: 16, sigmaY: 16),
                          child: Container(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 1.6),
                            decoration: BoxDecoration(
                              color: joviNavy.withOpacity(0.92),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: Colors.white.withOpacity(0.15),
                                width: 1,
                              ),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.35),
                                  blurRadius: 30,
                                  offset: Offset(0, 15),
                                ),
                              ],
                            ),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                CircularProgressIndicator(color: joviCoral),
                                SizedBox(height: layoutSettings.paddingV),
                                Text(
                                  _isRescheduleMode
                                      ? 'Rescheduling your appointment…'
                                      : 'Submitting your request…',
                                  style: TextStyle(
                                      fontSize:
                                          layoutSettings.actionTextSize + 3,
                                      color: Colors.white),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                if (_showSuccess)
                  Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [joviNavy, joviNavy, joviNavyDark],
                      ),
                    ),
                    child: wrapWithConstraints(
                      child: FadeTransition(
                        opacity: _fadeAnim,
                        child: SingleChildScrollView(
                          padding: _getAdaptivePadding(context),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              ScaleTransition(
                                scale: _scaleAnim,
                                child: Container(
                                  padding: EdgeInsets.all(
                                      layoutSettings.paddingH * 1.6),
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    gradient: LinearGradient(
                                      colors: [joviMint, joviMintDark],
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                    ),
                                    boxShadow: [
                                      BoxShadow(
                                        color: joviMint.withOpacity(0.4),
                                        blurRadius: 30,
                                        offset: Offset(0, 15),
                                      ),
                                    ],
                                  ),
                                  child: Icon(
                                    Icons.check,
                                    size: 80,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                              SizedBox(height: layoutSettings.paddingV * 1.6),
                              Text(
                                'Success!',
                                style: TextStyle(
                                  fontSize: layoutSettings.wideMode ? 42 : 36,
                                  fontWeight: FontWeight.bold,
                                  color: joviMint,
                                ),
                              ),
                              SizedBox(height: 12),
                              Text(
                                _isRefill()
                                    ? 'Your refill request has been submitted'
                                    : _isRescheduleMode
                                        ? 'Your appointment has been rescheduled'
                                        : 'Your appointment is confirmed',
                                style: TextStyle(
                                  fontSize: layoutSettings.wideMode ? 20 : 18,
                                  color: Colors.white.withOpacity(0.8),
                                ),
                              ),
                              if (!_isRefill() && _selectedDate != null) ...[
                                SizedBox(height: layoutSettings.paddingV),
                                Container(
                                  margin: EdgeInsets.symmetric(
                                      horizontal:
                                          layoutSettings.wideMode ? 0 : 40),
                                  padding:
                                      EdgeInsets.all(layoutSettings.paddingH),
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: [
                                        joviCoral.withOpacity(0.14),
                                        joviCoralDark.withOpacity(0.08),
                                      ],
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                    ),
                                    borderRadius: BorderRadius.circular(16),
                                    border: Border.all(
                                      color: joviCoral.withOpacity(0.35),
                                    ),
                                  ),
                                  child: Column(
                                    children: [
                                      Icon(Icons.event_available,
                                          color: joviCoral,
                                          size: layoutSettings
                                                  .actionIconDimension +
                                              4),
                                      SizedBox(height: 12),
                                      Text(
                                        DateFormat.MMMMEEEEd()
                                            .format(_selectedDate!),
                                        style: TextStyle(
                                          fontSize:
                                              layoutSettings.actionTextSize + 5,
                                          fontWeight: FontWeight.bold,
                                          color: Colors.white,
                                        ),
                                      ),
                                      SizedBox(height: 4),
                                      Text(
                                        _selectedTimeSlot ?? '',
                                        style: TextStyle(
                                          fontSize:
                                              layoutSettings.actionTextSize + 3,
                                          fontWeight: FontWeight.w600,
                                          color: joviCoral,
                                        ),
                                      ),
                                      if (_visitMode == 'Clinic' &&
                                          _selectedClinic != null) ...[
                                        SizedBox(height: 12),
                                        Divider(
                                            color: joviCoral.withOpacity(0.25)),
                                        SizedBox(height: 12),
                                        Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            Icon(Icons.location_on,
                                                color: joviCoral, size: 20),
                                            SizedBox(width: 8),
                                            Flexible(
                                              child: Text(
                                                _selectedClinic!,
                                                style: TextStyle(
                                                  fontSize: layoutSettings
                                                          .actionTextSize +
                                                      2,
                                                  fontWeight: FontWeight.w600,
                                                  color: Colors.white,
                                                ),
                                                textAlign: TextAlign.center,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                      if (_selectedBeverage != null) ...[
                                        SizedBox(height: 12),
                                        Divider(
                                            color: joviCoral.withOpacity(0.25)),
                                        SizedBox(height: 12),
                                        Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            Icon(
                                                _selectedBeverage ==
                                                        'Premium Water'
                                                    ? Icons.water_drop
                                                    : Icons.local_cafe,
                                                color: joviCoral,
                                                size: 20),
                                            SizedBox(width: 8),
                                            Flexible(
                                              child: Text(
                                                'Beverage: $_selectedBeverage${_selectedTeaType != null ? ' ($_selectedTeaType)' : ''}',
                                                style: TextStyle(
                                                  fontSize: layoutSettings
                                                          .actionTextSize +
                                                      2,
                                                  fontWeight: FontWeight.w600,
                                                  color: joviCoral,
                                                ),
                                                textAlign: TextAlign.center,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                              ],
                              if (!_isRefill() &&
                                  _selectedDate != null &&
                                  _selectedTimeSlot != null) ...[
                                SizedBox(height: layoutSettings.paddingV),
                                Padding(
                                  padding: EdgeInsets.symmetric(
                                      horizontal:
                                          layoutSettings.wideMode ? 0 : 40),
                                  child: Material(
                                    color: Colors.transparent,
                                    child: InkWell(
                                      onTap: () => _showCalendarInstructions(),
                                      borderRadius: BorderRadius.circular(12),
                                      child: Container(
                                        padding: EdgeInsets.symmetric(
                                            horizontal: layoutSettings.paddingH,
                                            vertical:
                                                layoutSettings.paddingV * 0.7),
                                        decoration: BoxDecoration(
                                          gradient: LinearGradient(
                                            colors: [joviMint, joviMintDark],
                                            begin: Alignment.centerLeft,
                                            end: Alignment.centerRight,
                                          ),
                                          borderRadius:
                                              BorderRadius.circular(12),
                                          boxShadow: [
                                            BoxShadow(
                                              color: joviMint.withOpacity(0.35),
                                              blurRadius: 10,
                                              offset: Offset(0, 5),
                                            ),
                                          ],
                                        ),
                                        child: Row(
                                          mainAxisAlignment:
                                              MainAxisAlignment.center,
                                          children: [
                                            Icon(Icons.calendar_today,
                                                color: Colors.white, size: 20),
                                            SizedBox(width: 8),
                                            Text(
                                              'Add to Calendar',
                                              style: TextStyle(
                                                color: Colors.white,
                                                fontWeight: FontWeight.bold,
                                                fontSize: layoutSettings
                                                        .actionTextSize +
                                                    2,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                              if (_visitMode == 'Clinic' &&
                                  _selectedClinic != null &&
                                  !_isRefill()) ...[
                                SizedBox(height: layoutSettings.paddingV),
                                Padding(
                                  padding: EdgeInsets.symmetric(
                                      horizontal:
                                          layoutSettings.wideMode ? 0 : 40),
                                  child: Column(
                                    children: [
                                      Material(
                                        color: Colors.transparent,
                                        child: InkWell(
                                          onTap: () => _launchMapNavigation(),
                                          borderRadius:
                                              BorderRadius.circular(12),
                                          child: Container(
                                            padding: EdgeInsets.symmetric(
                                                horizontal:
                                                    layoutSettings.paddingH,
                                                vertical:
                                                    layoutSettings.paddingV *
                                                        0.7),
                                            decoration: BoxDecoration(
                                              gradient: LinearGradient(
                                                colors: [
                                                  joviCoral,
                                                  joviCoralDark
                                                ],
                                                begin: Alignment.centerLeft,
                                                end: Alignment.centerRight,
                                              ),
                                              borderRadius:
                                                  BorderRadius.circular(12),
                                              boxShadow: [
                                                BoxShadow(
                                                  color: joviCoral
                                                      .withOpacity(0.4),
                                                  blurRadius: 10,
                                                  offset: Offset(0, 5),
                                                ),
                                              ],
                                            ),
                                            child: Row(
                                              mainAxisAlignment:
                                                  MainAxisAlignment.center,
                                              children: [
                                                Icon(Icons.navigation,
                                                    color: Colors.white,
                                                    size: 20),
                                                SizedBox(width: 8),
                                                Text(
                                                  'Start Navigation',
                                                  style: TextStyle(
                                                    color: Colors.white,
                                                    fontWeight: FontWeight.bold,
                                                    fontSize: layoutSettings
                                                            .actionTextSize +
                                                        2,
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ),
                                      ),
                                      SizedBox(height: 12),
                                      Text(
                                        _clinicLocations[_selectedClinic]![
                                            'fullAddress'] as String,
                                        style: TextStyle(
                                          fontSize:
                                              layoutSettings.actionTextSize,
                                          color: Colors.white.withOpacity(0.65),
                                        ),
                                        textAlign: TextAlign.center,
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                              if (_userHasKurvPass && !_isRescheduleMode) ...[
                                SizedBox(height: layoutSettings.paddingV),
                                Container(
                                  margin: EdgeInsets.symmetric(
                                      horizontal:
                                          layoutSettings.wideMode ? 0 : 40),
                                  padding: EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: joviGold.withOpacity(0.14),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(
                                        color: joviGold.withOpacity(0.4)),
                                  ),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(Icons.flash_on,
                                          color: joviGold,
                                          size: layoutSettings
                                              .actionIconDimension),
                                      SizedBox(width: 8),
                                      Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'Jovi Pass Active',
                                            style: TextStyle(
                                              fontSize: layoutSettings
                                                      .actionTextSize +
                                                  1,
                                              fontWeight: FontWeight.bold,
                                              color: joviGold,
                                            ),
                                          ),
                                          Text(
                                            'Skip the wait at your appointment',
                                            style: TextStyle(
                                              fontSize:
                                                  layoutSettings.actionTextSize,
                                              color: Colors.white
                                                  .withOpacity(0.75),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                              SizedBox(height: layoutSettings.paddingV * 1.6),
                              Padding(
                                padding: EdgeInsets.symmetric(
                                    horizontal:
                                        layoutSettings.wideMode ? 0 : 40),
                                child: Material(
                                  color: Colors.transparent,
                                  child: InkWell(
                                    onTap: () {
                                      HapticFeedback.mediumImpact();
                                      context.pushNamed('myAppointment');
                                    },
                                    borderRadius: BorderRadius.circular(12),
                                    child: Container(
                                      padding: EdgeInsets.symmetric(
                                          vertical:
                                              layoutSettings.paddingV * 0.8),
                                      decoration: BoxDecoration(
                                        gradient: LinearGradient(
                                          colors: [joviCoral, joviCoralDark],
                                          begin: Alignment.centerLeft,
                                          end: Alignment.centerRight,
                                        ),
                                        borderRadius: BorderRadius.circular(12),
                                        boxShadow: [
                                          BoxShadow(
                                            color: joviCoral.withOpacity(0.4),
                                            blurRadius: 10,
                                            offset: Offset(0, 5),
                                          ),
                                        ],
                                      ),
                                      child: Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.center,
                                        children: [
                                          Icon(Icons.done_all,
                                              color: Colors.white, size: 22),
                                          SizedBox(width: 10),
                                          Text(
                                            'Done',
                                            style: TextStyle(
                                              color: Colors.white,
                                              fontWeight: FontWeight.bold,
                                              fontSize: layoutSettings
                                                      .actionTextSize +
                                                  5,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                              SizedBox(height: layoutSettings.paddingV),
                            ],
                          ),
                        ),
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
}

// ════════════════════════════════════════════════════════════════
// _PetDurationOption — describes a single duration choice in the
// pet flow's Step 6. Tiny value class so the step builder can
// enumerate its options cleanly.
// ════════════════════════════════════════════════════════════════
class _PetDurationOption {
  final String label;
  final IconData icon;
  final String caption;
  final Color accent;
  const _PetDurationOption(this.label, this.icon, this.caption, this.accent);
}

// ════════════════════════════════════════════════════════════════
// Card Input Dialog - Navy + Glass
// ════════════════════════════════════════════════════════════════
class _CardInputDialog extends StatefulWidget {
  @override
  _CardInputDialogState createState() => _CardInputDialogState();
}

class _CardInputDialogState extends State<_CardInputDialog> {
  final _cardNumberController = TextEditingController();
  final _expMonthController = TextEditingController();
  final _expYearController = TextEditingController();
  final _cvvController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  // Jovi brand constants
  static const Color joviCoral = Color(0xFFFF6B4A);
  static const Color joviCoralDark = Color(0xFFE5583A);
  static const Color joviNavy = Color(0xFF1A2744);
  static const Color joviMint = Color(0xFF00D4AA);

  bool _isLargeScreen(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    return screenWidth > 600;
  }

  static bool _luhnValid(String digits) {
    int sum = 0;
    bool alt = false;
    for (int i = digits.length - 1; i >= 0; i--) {
      int n = int.tryParse(digits[i]) ?? -1;
      if (n < 0) return false;
      if (alt) {
        n *= 2;
        if (n > 9) n -= 9;
      }
      sum += n;
      alt = !alt;
    }
    return sum % 10 == 0;
  }

  InputDecoration _glassFieldDecoration({
    required String label,
    required String hint,
    Widget? prefixIcon,
  }) {
    return InputDecoration(
      labelText: label,
      labelStyle: TextStyle(color: Colors.white.withOpacity(0.75)),
      floatingLabelStyle: TextStyle(color: joviCoral),
      hintText: hint,
      hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
      prefixIcon: prefixIcon,
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
        borderSide: BorderSide(color: joviCoral, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Color(0xFFE53935), width: 2),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Color(0xFFE53935), width: 2),
      ),
      filled: true,
      fillColor: Colors.white.withOpacity(0.08),
      errorStyle: TextStyle(color: Color(0xFFFF8A80)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isLarge = _isLargeScreen(context);

    return Dialog(
      backgroundColor: Colors.transparent,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ui_dart.ImageFilter.blur(sigmaX: 24, sigmaY: 24),
          child: Container(
            constraints: BoxConstraints(
              maxWidth: isLarge ? 600 : double.infinity,
            ),
            padding: EdgeInsets.all(24),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              color: joviNavy.withOpacity(0.92),
              border: Border.all(
                color: Colors.white.withOpacity(0.12),
                width: 1,
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.35),
                  blurRadius: 30,
                  offset: Offset(0, 15),
                ),
              ],
            ),
            child: Form(
              key: _formKey,
              child: AutofillGroup(
                  child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Header
                    Container(
                      padding: EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            joviCoral.withOpacity(0.18),
                            joviCoralDark.withOpacity(0.10)
                          ],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: joviCoral.withOpacity(0.3)),
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: joviCoral.withOpacity(0.25),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(Icons.lock, color: joviCoral, size: 24),
                          ),
                          SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Secure Payment',
                                  style: TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                  ),
                                ),
                                Text(
                                  'Jovi Pass - \$49.00',
                                  style: TextStyle(
                                    fontSize: 14,
                                    color: Colors.white.withOpacity(0.7),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(height: 24),

                    // Card Number
                    TextFormField(
                      controller: _cardNumberController,
                      style: TextStyle(color: Colors.white),
                      decoration: _glassFieldDecoration(
                        label: 'Card Number',
                        hint: '1234 5678 9012 3456',
                        prefixIcon: Icon(Icons.credit_card, color: joviCoral),
                      ),
                      keyboardType: TextInputType.number,
                      autofillHints: const [AutofillHints.creditCardNumber],
                      textInputAction: TextInputAction.next,
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                        LengthLimitingTextInputFormatter(19),
                      ],
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Please enter card number';
                        }
                        final digits = value.replaceAll(' ', '');
                        if (digits.length < 13 || !_luhnValid(digits)) {
                          return 'Check the card number';
                        }
                        return null;
                      },
                      onChanged: (value) {
                        final text = value.replaceAll(' ', '');
                        final buffer = StringBuffer();
                        for (int i = 0; i < text.length; i++) {
                          buffer.write(text[i]);
                          if ((i + 1) % 4 == 0 && i + 1 != text.length) {
                            buffer.write(' ');
                          }
                        }
                        if (buffer.toString() != value) {
                          _cardNumberController.value = TextEditingValue(
                            text: buffer.toString(),
                            selection:
                                TextSelection.collapsed(offset: buffer.length),
                          );
                        }
                      },
                    ),
                    SizedBox(height: 16),

                    // Expiry and CVV Row
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _expMonthController,
                            style: TextStyle(color: Colors.white),
                            decoration: _glassFieldDecoration(
                              label: 'MM',
                              hint: '12',
                              prefixIcon: Icon(Icons.calendar_today,
                                  color: joviCoral, size: 20),
                            ),
                            keyboardType: TextInputType.number,
                            autofillHints: const [
                              AutofillHints.creditCardExpirationMonth
                            ],
                            textInputAction: TextInputAction.next,
                            inputFormatters: [
                              FilteringTextInputFormatter.digitsOnly,
                              LengthLimitingTextInputFormatter(2),
                            ],
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Required';
                              }
                              final month = int.tryParse(value);
                              if (month == null || month < 1 || month > 12) {
                                return 'Invalid';
                              }
                              return null;
                            },
                          ),
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _expYearController,
                            style: TextStyle(color: Colors.white),
                            decoration: _glassFieldDecoration(
                              label: 'YY',
                              hint: '27',
                            ),
                            keyboardType: TextInputType.number,
                            autofillHints: const [
                              AutofillHints.creditCardExpirationYear
                            ],
                            textInputAction: TextInputAction.next,
                            inputFormatters: [
                              FilteringTextInputFormatter.digitsOnly,
                              LengthLimitingTextInputFormatter(2),
                            ],
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Required';
                              }
                              final year = int.tryParse(value);
                              final now = DateTime.now();
                              final currentYear = now.year % 100;
                              final month =
                                  int.tryParse(_expMonthController.text) ?? 0;
                              if (year == null || year < currentYear) {
                                return 'Invalid';
                              }
                              if (year == currentYear && month < now.month) {
                                return 'Expired';
                              }
                              return null;
                            },
                          ),
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _cvvController,
                            style: TextStyle(color: Colors.white),
                            decoration: _glassFieldDecoration(
                              label: 'CVV',
                              hint: '123',
                              prefixIcon: Icon(Icons.lock_outline,
                                  color: joviCoral, size: 20),
                            ),
                            keyboardType: TextInputType.number,
                            autofillHints: const [
                              AutofillHints.creditCardSecurityCode
                            ],
                            textInputAction: TextInputAction.done,
                            obscureText: true,
                            inputFormatters: [
                              FilteringTextInputFormatter.digitsOnly,
                              LengthLimitingTextInputFormatter(4),
                            ],
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Required';
                              }
                              if (value.length < 3) {
                                return 'Invalid';
                              }
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 20),

                    // Security Badge
                    Container(
                      padding: EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: joviMint.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: joviMint.withOpacity(0.4)),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.verified_user, color: joviMint, size: 20),
                          SizedBox(width: 8),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Secure & Encrypted',
                                  style: TextStyle(
                                    color: joviMint,
                                    fontSize: 14,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                Text(
                                  'Your payment info is protected with bank-level security',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.75),
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(height: 24),

                    // Action Buttons
                    Row(
                      children: [
                        Expanded(
                          child: TextButton(
                            onPressed: () => Navigator.of(context).pop(),
                            style: TextButton.styleFrom(
                              padding: EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                            ),
                            child: Text(
                              'Cancel',
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.7),
                                fontSize: 16,
                              ),
                            ),
                          ),
                        ),
                        SizedBox(width: 16),
                        Expanded(
                          flex: 2,
                          child: ElevatedButton(
                            onPressed: () {
                              if (_formKey.currentState!.validate()) {
                                Navigator.of(context).pop({
                                  'cardNumber': _cardNumberController.text
                                      .replaceAll(' ', ''),
                                  'expMonth': _expMonthController.text,
                                  'expYear': _expYearController.text,
                                  'cvv': _cvvController.text,
                                });
                              }
                            },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: joviCoral,
                              foregroundColor: Colors.white,
                              padding: EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              elevation: 3,
                              shadowColor: joviCoral.withOpacity(0.4),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.lock, size: 18),
                                SizedBox(width: 8),
                                Text(
                                  'Pay \$49.00',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              )),
            ),
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _cardNumberController.dispose();
    _expMonthController.dispose();
    _expYearController.dispose();
    _cvvController.dispose();
    super.dispose();
  }
}
