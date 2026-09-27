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
// JOVI HEALTH — DRUG SAFETY CHECK
// Version: 2026.09.22 (Apple HIG pass: painted glass instead of per-card
//          blur, press feedback, no looping motion, keyboard-aware sheets,
//          navy toasts)
// Base:    2026.04.17 (comprehensive rebuild)
//
// Features:
// • Drug-drug, food, supplement, alcohol interaction detection
// • Duplicate therapy detection
// • Pregnancy/breastfeeding safety flags
// • Kidney/liver dose-adjustment flags
// • Taper/withdrawal warnings
// • Missed dose guidance
// • Timing-optimized daily schedule suggestions
// • Interaction heat map visualization
// • FDA API integration (supplementary)
// • Doctor-ready report generation (text + shareable)
// • Half-Life DB cross-linking
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;
import 'dart:ui' as ui;
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:http/http.dart' as http;

// ─── Enums ──────────────────────────────────────────────────────────────────

enum ScreenType { compact, medium, expanded, large }

enum InteractionSeverity {
  minor('Minor', 'Monitor for effects'),
  moderate('Moderate', 'Use caution; may need adjustment'),
  major('Major', 'Avoid combination if possible'),
  contraindicated('Contraindicated', 'Do not combine');

  const InteractionSeverity(this.label, this.description);
  final String label;
  final String description;

  static InteractionSeverity fromString(String s) {
    switch (s.toLowerCase()) {
      case 'contraindicated':
        return InteractionSeverity.contraindicated;
      case 'major':
        return InteractionSeverity.major;
      case 'moderate':
        return InteractionSeverity.moderate;
      case 'minor':
        return InteractionSeverity.minor;
      default:
        return InteractionSeverity.moderate;
    }
  }
}

enum InteractionKind {
  drugDrug('Drug–Drug', Icons.medication_rounded),
  drugFood('Drug–Food', Icons.restaurant_rounded),
  drugSupplement('Drug–Supplement', Icons.spa_rounded),
  drugAlcohol('Drug–Alcohol', Icons.local_bar_rounded),
  duplicateTherapy('Duplicate Therapy', Icons.copy_all_rounded),
  pregnancy('Pregnancy Risk', Icons.pregnant_woman_rounded),
  renal('Kidney Adjustment', Icons.water_drop_rounded),
  hepatic('Liver Adjustment', Icons.monitor_heart_rounded),
  taper('Taper Required', Icons.trending_down_rounded),
  allergy('Allergy Alert', Icons.dangerous_rounded);

  const InteractionKind(this.label, this.icon);
  final String label;
  final IconData icon;
}

enum _Tab { interactions, schedule, safety, sideEffects, education }

enum _PregnancyState { none, pregnant, breastfeeding, both }

// ─── Responsive config ──────────────────────────────────────────────────────

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

// ─── Brand palette ──────────────────────────────────────────────────────────

class _Jovi {
  static const Color coral = Color(0xFFFF6B4A);
  static const Color coralLight = Color(0xFFFF8F73);
  static const Color coralDark = Color(0xFFE5583A);
  static const Color navy = Color(0xFF1A2744);
  static const Color navyDark = Color(0xFF0F1A2E);
  static const Color navyMid = Color(0xFF1F2B47);
  static const Color mint = Color(0xFF00D4AA);
  static const Color mintDark = Color(0xFF00B894);
  static const Color gold = Color(0xFFFFD166);
  static const Color goldDark = Color(0xFFE6B84D);
  static const Color errorRed = Color(0xFFE53935);
  static const Color softRed = Color(0xFFFF8A80);

  static LinearGradient get coralGradient => LinearGradient(
        colors: [coral, coralDark],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
  static LinearGradient get navyGradient => LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [navy, navy, navyDark],
      );

  /// Color for a given interaction severity
  static Color severityColor(InteractionSeverity s) {
    switch (s) {
      case InteractionSeverity.contraindicated:
        return errorRed;
      case InteractionSeverity.major:
        return errorRed;
      case InteractionSeverity.moderate:
        return gold;
      case InteractionSeverity.minor:
        return mint;
    }
  }
}

// ─── Data Models ────────────────────────────────────────────────────────────

class UserMedication {
  final String id;
  final String name;
  final String dosage;
  final String strength;
  final bool isAsNeeded;
  final String? frequency; // e.g., "twice daily", "every 8 hours"

  UserMedication({
    required this.id,
    required this.name,
    this.dosage = '',
    this.strength = '',
    this.isAsNeeded = false,
    this.frequency,
  });

  String get displayName => name.isEmpty ? 'Unknown' : name;
}

class SafetyFinding {
  final InteractionKind kind;
  final InteractionSeverity severity;
  final String title;
  final String description;
  final List<String> affectedMeds; // names involved
  final String? recommendation;
  final String? source; // "FDA" | "Jovi DB" | "Clinical Reference"

  SafetyFinding({
    required this.kind,
    required this.severity,
    required this.title,
    required this.description,
    this.affectedMeds = const [],
    this.recommendation,
    this.source,
  });
}

class ReportedSideEffect {
  final String id;
  final String medicationId;
  final String medicationName;
  final String severity; // mild | moderate | severe
  final String description;
  final List<String> symptoms;
  final DateTime reportedAt;

  ReportedSideEffect({
    required this.id,
    required this.medicationId,
    required this.medicationName,
    required this.severity,
    required this.description,
    required this.symptoms,
    required this.reportedAt,
  });
}

class TimingSuggestion {
  final String time; // e.g. "6:00 AM"
  final String medicationName;
  final String note; // e.g. "Take on empty stomach, wait 30 min before food"
  final IconData icon;
  final Color accentColor;

  TimingSuggestion({
    required this.time,
    required this.medicationName,
    required this.note,
    required this.icon,
    required this.accentColor,
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// CLINICAL KNOWLEDGE BASE
// These are the reference datasets the safety checker uses to find issues.
// Scoped to common/critical interactions — not comprehensive drug info (that
// lives in the Half-Life widget's database).
// ═══════════════════════════════════════════════════════════════════════════

class _ClinicalRefs {
  // ─── Drug–Drug Interactions ───────────────────────────────────────────────
  /// Map of drug name (lowercase) to list of {drug2, severity, mechanism}
  static final Map<String, List<_DrugInteraction>> drugDrug = {
    'warfarin': [
      _DrugInteraction('aspirin', InteractionSeverity.major,
          'Increased bleeding risk — additive anticoagulation'),
      _DrugInteraction('ibuprofen', InteractionSeverity.major,
          'NSAIDs increase bleeding risk and displace warfarin from albumin'),
      _DrugInteraction('naproxen', InteractionSeverity.major,
          'NSAIDs increase bleeding risk'),
      _DrugInteraction('amiodarone', InteractionSeverity.major,
          'Amiodarone inhibits CYP2C9, increasing warfarin levels'),
      _DrugInteraction('fluconazole', InteractionSeverity.major,
          'Fluconazole inhibits CYP2C9 — major INR increase'),
      _DrugInteraction('metronidazole', InteractionSeverity.major,
          'Metronidazole significantly increases INR'),
      _DrugInteraction(
          'trimethoprim-sulfamethoxazole',
          InteractionSeverity.major,
          'Major INR increase — often requires warfarin dose reduction'),
      _DrugInteraction('ciprofloxacin', InteractionSeverity.moderate,
          'Fluoroquinolones can increase INR'),
      _DrugInteraction(
          'clopidogrel', InteractionSeverity.major, 'Additive bleeding risk'),
      _DrugInteraction('apixaban', InteractionSeverity.contraindicated,
          'Dual anticoagulation — severe bleeding risk'),
      _DrugInteraction('rivaroxaban', InteractionSeverity.contraindicated,
          'Dual anticoagulation — severe bleeding risk'),
    ],
    'aspirin': [
      _DrugInteraction(
          'warfarin', InteractionSeverity.major, 'Additive bleeding risk'),
      _DrugInteraction('ibuprofen', InteractionSeverity.moderate,
          'Ibuprofen may block aspirin cardioprotective effect'),
      _DrugInteraction('clopidogrel', InteractionSeverity.moderate,
          'Dual antiplatelet therapy — increased bleeding risk (may be intentional post-stent)'),
      _DrugInteraction('methotrexate', InteractionSeverity.major,
          'Reduces methotrexate clearance — toxicity risk'),
    ],
    'metformin': [
      _DrugInteraction('contrast dye', InteractionSeverity.major,
          'Hold metformin 48h around IV contrast — lactic acidosis risk'),
      _DrugInteraction('cimetidine', InteractionSeverity.moderate,
          'Reduces metformin clearance'),
    ],
    'simvastatin': [
      _DrugInteraction('amiodarone', InteractionSeverity.major,
          'Limit simvastatin to 20 mg daily — rhabdomyolysis risk'),
      _DrugInteraction('diltiazem', InteractionSeverity.major,
          'Limit simvastatin to 10 mg daily — rhabdomyolysis risk'),
      _DrugInteraction('verapamil', InteractionSeverity.major,
          'Limit simvastatin to 10 mg daily'),
      _DrugInteraction('clarithromycin', InteractionSeverity.contraindicated,
          'Do not combine — severe rhabdomyolysis risk'),
      _DrugInteraction('itraconazole', InteractionSeverity.contraindicated,
          'Do not combine — severe rhabdomyolysis risk'),
      _DrugInteraction('gemfibrozil', InteractionSeverity.contraindicated,
          'Do not combine — severe rhabdomyolysis risk'),
    ],
    'atorvastatin': [
      _DrugInteraction('clarithromycin', InteractionSeverity.major,
          'Significantly increases atorvastatin levels'),
      _DrugInteraction('gemfibrozil', InteractionSeverity.major,
          'Increased rhabdomyolysis risk'),
    ],
    'sildenafil': [
      _DrugInteraction('nitroglycerin', InteractionSeverity.contraindicated,
          'Severe hypotension — absolute contraindication'),
      _DrugInteraction(
          'isosorbide mononitrate',
          InteractionSeverity.contraindicated,
          'Severe hypotension — absolute contraindication'),
      _DrugInteraction(
          'isosorbide dinitrate',
          InteractionSeverity.contraindicated,
          'Severe hypotension — absolute contraindication'),
      _DrugInteraction('tamsulosin', InteractionSeverity.moderate,
          'Additive hypotensive effect'),
    ],
    'tadalafil': [
      _DrugInteraction('nitroglycerin', InteractionSeverity.contraindicated,
          'Severe hypotension — absolute contraindication'),
      _DrugInteraction(
          'isosorbide mononitrate',
          InteractionSeverity.contraindicated,
          'Severe hypotension — absolute contraindication'),
    ],
    'sertraline': [
      _DrugInteraction(
          'tramadol', InteractionSeverity.major, 'Serotonin syndrome risk'),
      _DrugInteraction('linezolid', InteractionSeverity.contraindicated,
          'Serotonin syndrome — do not combine'),
      _DrugInteraction('warfarin', InteractionSeverity.moderate,
          'May increase bleeding risk'),
    ],
    'fluoxetine': [
      _DrugInteraction(
          'tramadol', InteractionSeverity.major, 'Serotonin syndrome risk'),
      _DrugInteraction('linezolid', InteractionSeverity.contraindicated,
          'Serotonin syndrome — do not combine'),
      _DrugInteraction('metoprolol', InteractionSeverity.moderate,
          'Fluoxetine inhibits CYP2D6, increasing metoprolol'),
    ],
    'paroxetine': [
      _DrugInteraction('tamoxifen', InteractionSeverity.major,
          'Paroxetine blocks tamoxifen activation — reduces efficacy'),
      _DrugInteraction(
          'tramadol', InteractionSeverity.major, 'Serotonin syndrome risk'),
    ],
    'lisinopril': [
      _DrugInteraction('spironolactone', InteractionSeverity.moderate,
          'Hyperkalemia risk — monitor potassium'),
      _DrugInteraction('potassium chloride', InteractionSeverity.moderate,
          'Additive hyperkalemia risk'),
      _DrugInteraction('ibuprofen', InteractionSeverity.moderate,
          'NSAIDs reduce ACE inhibitor effect and increase renal risk'),
      _DrugInteraction('losartan', InteractionSeverity.major,
          'Dual RAAS blockade — avoid combination'),
    ],
    'losartan': [
      _DrugInteraction(
          'spironolactone', InteractionSeverity.moderate, 'Hyperkalemia risk'),
      _DrugInteraction('lisinopril', InteractionSeverity.major,
          'Dual RAAS blockade — avoid'),
    ],
    'digoxin': [
      _DrugInteraction('amiodarone', InteractionSeverity.major,
          'Reduce digoxin dose by 50% — toxicity risk'),
      _DrugInteraction(
          'verapamil', InteractionSeverity.major, 'Increases digoxin levels'),
      _DrugInteraction('clarithromycin', InteractionSeverity.major,
          'Significantly increases digoxin levels'),
      _DrugInteraction('furosemide', InteractionSeverity.moderate,
          'Hypokalemia increases digoxin toxicity risk'),
    ],
    'methotrexate': [
      _DrugInteraction(
          'trimethoprim-sulfamethoxazole',
          InteractionSeverity.major,
          'Additive antifolate effect — pancytopenia risk'),
      _DrugInteraction('ibuprofen', InteractionSeverity.major,
          'NSAIDs reduce methotrexate clearance'),
      _DrugInteraction('aspirin', InteractionSeverity.major,
          'Reduces methotrexate clearance'),
    ],
    'lithium': [
      _DrugInteraction('ibuprofen', InteractionSeverity.major,
          'NSAIDs significantly increase lithium levels'),
      _DrugInteraction('lisinopril', InteractionSeverity.major,
          'ACE inhibitors increase lithium levels'),
      _DrugInteraction('hydrochlorothiazide', InteractionSeverity.major,
          'Thiazides significantly increase lithium levels'),
    ],
    'clopidogrel': [
      _DrugInteraction('omeprazole', InteractionSeverity.moderate,
          'Omeprazole reduces clopidogrel activation — consider pantoprazole'),
      _DrugInteraction('esomeprazole', InteractionSeverity.moderate,
          'Reduces clopidogrel effectiveness'),
      _DrugInteraction(
          'warfarin', InteractionSeverity.major, 'Additive bleeding risk'),
    ],
    'levothyroxine': [
      _DrugInteraction('calcium carbonate', InteractionSeverity.moderate,
          'Separate by 4 hours — calcium binds levothyroxine'),
      _DrugInteraction('iron (ferrous sulfate)', InteractionSeverity.moderate,
          'Separate by 4 hours — iron binds levothyroxine'),
      _DrugInteraction('omeprazole', InteractionSeverity.moderate,
          'PPIs reduce levothyroxine absorption'),
    ],
    'ciprofloxacin': [
      _DrugInteraction('calcium carbonate', InteractionSeverity.moderate,
          'Separate by 2 hours — chelation reduces absorption'),
      _DrugInteraction('iron (ferrous sulfate)', InteractionSeverity.moderate,
          'Separate by 2 hours — chelation'),
      _DrugInteraction('theophylline', InteractionSeverity.major,
          'Ciprofloxacin significantly increases theophylline'),
      _DrugInteraction('tizanidine', InteractionSeverity.contraindicated,
          'Severe hypotension and sedation'),
    ],
    'tramadol': [
      _DrugInteraction(
          'sertraline', InteractionSeverity.major, 'Serotonin syndrome risk'),
      _DrugInteraction(
          'fluoxetine', InteractionSeverity.major, 'Serotonin syndrome risk'),
      _DrugInteraction(
          'paroxetine', InteractionSeverity.major, 'Serotonin syndrome risk'),
      _DrugInteraction(
          'lorazepam', InteractionSeverity.major, 'CNS depression risk'),
    ],
    'alprazolam': [
      _DrugInteraction('oxycodone', InteractionSeverity.major,
          'Respiratory depression risk — FDA black box'),
      _DrugInteraction('hydrocodone', InteractionSeverity.major,
          'Respiratory depression risk — FDA black box'),
      _DrugInteraction(
          'morphine', InteractionSeverity.major, 'Respiratory depression risk'),
    ],
    'gabapentin': [
      _DrugInteraction('morphine', InteractionSeverity.moderate,
          'Additive sedation and respiratory depression'),
      _DrugInteraction(
          'oxycodone', InteractionSeverity.moderate, 'Additive CNS depression'),
    ],
    'amiodarone': [
      _DrugInteraction('warfarin', InteractionSeverity.major,
          'Reduce warfarin 30-50% — major INR increase'),
      _DrugInteraction(
          'digoxin', InteractionSeverity.major, 'Reduce digoxin 50%'),
      _DrugInteraction('simvastatin', InteractionSeverity.major,
          'Limit simvastatin to 20 mg'),
    ],
  };

  // ─── Drug–Food Interactions ───────────────────────────────────────────────
  static final Map<String, List<_FoodInteraction>> drugFood = {
    'warfarin': [
      _FoodInteraction(
          'Green leafy vegetables (kale, spinach)',
          'Keep vitamin K intake consistent — sudden changes affect INR',
          InteractionSeverity.moderate),
      _FoodInteraction(
          'Grapefruit', 'May modestly affect INR', InteractionSeverity.minor),
      _FoodInteraction('Cranberry juice (large amounts)', 'May increase INR',
          InteractionSeverity.moderate),
    ],
    'simvastatin': [
      _FoodInteraction(
          'Grapefruit/grapefruit juice',
          'Significantly increases statin levels — avoid',
          InteractionSeverity.major),
    ],
    'atorvastatin': [
      _FoodInteraction('Grapefruit (large amounts)',
          'May increase statin levels', InteractionSeverity.moderate),
    ],
    'amiodarone': [
      _FoodInteraction(
          'Grapefruit/grapefruit juice',
          'Significantly increases amiodarone levels — avoid',
          InteractionSeverity.major),
    ],
    'amlodipine': [
      _FoodInteraction('Grapefruit (large amounts)',
          'May increase amlodipine levels', InteractionSeverity.minor),
    ],
    'levothyroxine': [
      _FoodInteraction('Soy products', 'Reduces absorption — take separately',
          InteractionSeverity.moderate),
      _FoodInteraction('Coffee', 'Take levothyroxine 1 hour before coffee',
          InteractionSeverity.moderate),
      _FoodInteraction(
          'High-fiber meals', 'Reduces absorption', InteractionSeverity.minor),
    ],
    'ciprofloxacin': [
      _FoodInteraction(
          'Dairy products (milk, yogurt)',
          'Separate by 2 hours — chelation reduces absorption',
          InteractionSeverity.moderate),
      _FoodInteraction('Calcium-fortified juices', 'Separate by 2 hours',
          InteractionSeverity.moderate),
    ],
    'tetracycline': [
      _FoodInteraction(
          'Dairy products',
          'Separate by 2 hours — reduces absorption significantly',
          InteractionSeverity.major),
    ],
    'doxycycline': [
      _FoodInteraction('Dairy products', 'Separate by 1-2 hours',
          InteractionSeverity.moderate),
    ],
    'metformin': [
      _FoodInteraction('Alcohol', 'Increases lactic acidosis risk',
          InteractionSeverity.moderate),
    ],
    'sertraline': [
      _FoodInteraction('Grapefruit (large amounts)',
          'May modestly increase levels', InteractionSeverity.minor),
    ],
    'linezolid': [
      _FoodInteraction('Tyramine-rich foods (aged cheese, cured meats, wine)',
          'Hypertensive crisis risk', InteractionSeverity.major),
    ],
    'maoi': [
      _FoodInteraction(
          'Tyramine-rich foods',
          'Hypertensive crisis risk — strict avoidance required',
          InteractionSeverity.major),
    ],
    'tacrolimus': [
      _FoodInteraction('Grapefruit', 'Significantly increases levels — avoid',
          InteractionSeverity.major),
    ],
    'cyclosporine': [
      _FoodInteraction('Grapefruit', 'Significantly increases levels — avoid',
          InteractionSeverity.major),
    ],
  };

  // ─── Alcohol Interactions ─────────────────────────────────────────────────
  /// Meds that significantly interact with alcohol
  static final Map<String, _AlcoholInteraction> alcohol = {
    'acetaminophen': _AlcoholInteraction(InteractionSeverity.major,
        'Chronic alcohol use significantly increases liver damage risk from acetaminophen.'),
    'metronidazole': _AlcoholInteraction(InteractionSeverity.major,
        'Disulfiram-like reaction — severe nausea, vomiting, headache.'),
    'warfarin': _AlcoholInteraction(InteractionSeverity.major,
        'Alcohol affects INR unpredictably and increases bleeding risk.'),
    'lorazepam': _AlcoholInteraction(InteractionSeverity.major,
        'Severe CNS depression and respiratory depression risk.'),
    'alprazolam': _AlcoholInteraction(InteractionSeverity.major,
        'Severe CNS depression — potentially fatal.'),
    'clonazepam': _AlcoholInteraction(
        InteractionSeverity.major, 'Severe CNS and respiratory depression.'),
    'diazepam': _AlcoholInteraction(
        InteractionSeverity.major, 'Severe CNS and respiratory depression.'),
    'oxycodone': _AlcoholInteraction(InteractionSeverity.major,
        'Fatal respiratory depression risk — FDA black box.'),
    'hydrocodone': _AlcoholInteraction(
        InteractionSeverity.major, 'Fatal respiratory depression risk.'),
    'morphine': _AlcoholInteraction(
        InteractionSeverity.major, 'Fatal respiratory depression risk.'),
    'tramadol': _AlcoholInteraction(InteractionSeverity.major,
        'Increased seizure and CNS depression risk.'),
    'fentanyl': _AlcoholInteraction(InteractionSeverity.contraindicated,
        'Fatal respiratory depression — avoid entirely.'),
    'zolpidem': _AlcoholInteraction(InteractionSeverity.major,
        'Increased sedation, complex sleep behaviors.'),
    'metformin': _AlcoholInteraction(
        InteractionSeverity.moderate, 'Increased risk of lactic acidosis.'),
    'disulfiram': _AlcoholInteraction(InteractionSeverity.contraindicated,
        'Severe reaction by design — avoid all alcohol including hidden sources.'),
    'sertraline': _AlcoholInteraction(InteractionSeverity.moderate,
        'Increased drowsiness; may worsen depression.'),
    'fluoxetine': _AlcoholInteraction(InteractionSeverity.moderate,
        'Increased drowsiness; may worsen depression.'),
    'bupropion': _AlcoholInteraction(InteractionSeverity.moderate,
        'Lowers seizure threshold — avoid excessive alcohol.'),
    'lithium': _AlcoholInteraction(InteractionSeverity.moderate,
        'Dehydration can raise lithium to toxic levels.'),
    'methotrexate': _AlcoholInteraction(
        InteractionSeverity.major, 'Significantly increases hepatotoxicity.'),
    'isotretinoin':
        _AlcoholInteraction(InteractionSeverity.major, 'Liver toxicity risk.'),
    'gabapentin': _AlcoholInteraction(
        InteractionSeverity.moderate, 'Additive CNS depression.'),
    'pregabalin': _AlcoholInteraction(
        InteractionSeverity.moderate, 'Additive CNS depression.'),
    'cyclobenzaprine': _AlcoholInteraction(
        InteractionSeverity.moderate, 'Significant drowsiness and impairment.'),
    'baclofen': _AlcoholInteraction(
        InteractionSeverity.moderate, 'Significant drowsiness.'),
    'doxycycline': _AlcoholInteraction(
        InteractionSeverity.minor, 'May reduce antibiotic effectiveness.'),
    'sildenafil': _AlcoholInteraction(
        InteractionSeverity.moderate, 'Additive hypotension.'),
  };

  // ─── Duplicate Therapy Classes ────────────────────────────────────────────
  /// Drug class → list of medications in that class
  static final Map<String, List<String>> therapyClasses = {
    'NSAID': [
      'ibuprofen',
      'naproxen',
      'aspirin',
      'celecoxib',
      'diclofenac',
      'ketorolac',
      'meloxicam',
      'ketoprofen',
      'indomethacin'
    ],
    'SSRI': [
      'sertraline',
      'fluoxetine',
      'escitalopram',
      'citalopram',
      'paroxetine'
    ],
    'SNRI': ['venlafaxine', 'duloxetine'],
    'Benzodiazepine': ['lorazepam', 'alprazolam', 'clonazepam', 'diazepam'],
    'Opioid': [
      'morphine',
      'oxycodone',
      'hydrocodone',
      'tramadol',
      'fentanyl',
      'codeine',
      'methadone'
    ],
    'Beta-blocker': [
      'metoprolol',
      'atenolol',
      'carvedilol',
      'propranolol',
      'bisoprolol'
    ],
    'ACE inhibitor': [
      'lisinopril',
      'enalapril',
      'ramipril',
      'benazepril',
      'captopril'
    ],
    'ARB': ['losartan', 'valsartan', 'olmesartan', 'irbesartan', 'telmisartan'],
    'Statin': [
      'atorvastatin',
      'simvastatin',
      'rosuvastatin',
      'pravastatin',
      'lovastatin'
    ],
    'PPI': [
      'omeprazole',
      'esomeprazole',
      'pantoprazole',
      'lansoprazole',
      'rabeprazole',
      'dexlansoprazole'
    ],
    'Calcium Channel Blocker': [
      'amlodipine',
      'diltiazem',
      'verapamil',
      'nifedipine',
      'felodipine'
    ],
    'Loop Diuretic': ['furosemide', 'bumetanide', 'torsemide'],
    'Thiazide Diuretic': [
      'hydrochlorothiazide',
      'chlorthalidone',
      'indapamide'
    ],
    'Fluoroquinolone': [
      'ciprofloxacin',
      'levofloxacin',
      'moxifloxacin',
      'ofloxacin'
    ],
    'Anticoagulant (DOAC)': [
      'apixaban',
      'rivaroxaban',
      'dabigatran',
      'edoxaban'
    ],
    'Antiplatelet': ['clopidogrel', 'ticagrelor', 'prasugrel', 'aspirin'],
    'Z-drug (hypnotic)': ['zolpidem', 'eszopiclone', 'zaleplon'],
    'Stimulant': [
      'methylphenidate',
      'amphetamine/dextroamphetamine',
      'lisdexamfetamine'
    ],
    'Triptan': ['sumatriptan', 'rizatriptan', 'zolmitriptan', 'eletriptan'],
    'Antihistamine (1st gen)': [
      'diphenhydramine',
      'hydroxyzine',
      'chlorpheniramine'
    ],
    'Antihistamine (2nd gen)': ['cetirizine', 'loratadine', 'fexofenadine'],
  };

  // ─── Taper-Required Medications ───────────────────────────────────────────
  /// Meds that should not be stopped abruptly
  static final Map<String, _TaperInfo> taperRequired = {
    'sertraline': _TaperInfo('SSRI',
        'Abrupt discontinuation causes flu-like symptoms, dizziness, irritability. Taper over weeks.'),
    'fluoxetine': _TaperInfo('SSRI',
        'Long half-life makes self-tapering somewhat safer but taper is still advised.'),
    'escitalopram':
        _TaperInfo('SSRI', 'Taper slowly to avoid discontinuation syndrome.'),
    'citalopram':
        _TaperInfo('SSRI', 'Taper slowly to avoid discontinuation syndrome.'),
    'paroxetine': _TaperInfo(
        'SSRI', 'Severe discontinuation syndrome — taper very slowly.'),
    'venlafaxine': _TaperInfo('SNRI',
        'Particularly notorious discontinuation syndrome — taper slowly.'),
    'duloxetine':
        _TaperInfo('SNRI', 'Taper slowly to avoid discontinuation syndrome.'),
    'lorazepam': _TaperInfo('Benzodiazepine',
        'Abrupt discontinuation causes seizures, severe anxiety, insomnia.'),
    'alprazolam': _TaperInfo('Benzodiazepine',
        'Severe withdrawal including seizures — taper very slowly.'),
    'clonazepam': _TaperInfo('Benzodiazepine',
        'Taper very slowly to avoid seizures and severe withdrawal.'),
    'diazepam': _TaperInfo('Benzodiazepine',
        'Taper slowly — long half-life helps but withdrawal still possible.'),
    'metoprolol': _TaperInfo('Beta-blocker',
        'Abrupt discontinuation causes rebound hypertension, angina, or MI.'),
    'atenolol': _TaperInfo(
        'Beta-blocker', 'Abrupt discontinuation causes rebound hypertension.'),
    'carvedilol': _TaperInfo('Beta-blocker',
        'Abrupt discontinuation causes rebound hypertension and tachycardia.'),
    'clonidine': _TaperInfo('Alpha-2 agonist',
        'Severe rebound hypertension — very slow taper required.'),
    'prednisone': _TaperInfo('Corticosteroid',
        'HPA axis suppression — taper required after >1-2 weeks of use.'),
    'dexamethasone':
        _TaperInfo('Corticosteroid', 'HPA axis suppression — taper required.'),
    'gabapentin': _TaperInfo('Anticonvulsant',
        'Abrupt discontinuation can cause seizures — taper over at least 1 week.'),
    'pregabalin': _TaperInfo(
        'Anticonvulsant', 'Taper slowly to avoid seizures and withdrawal.'),
    'lamotrigine': _TaperInfo(
        'Anticonvulsant', 'Abrupt discontinuation can trigger seizures.'),
    'levetiracetam':
        _TaperInfo('Anticonvulsant', 'Taper gradually to avoid seizures.'),
    'tramadol': _TaperInfo('Opioid/SNRI',
        'Dual mechanism — taper required to avoid opioid AND SSRI-like withdrawal.'),
    'oxycodone':
        _TaperInfo('Opioid', 'Taper to avoid opioid withdrawal syndrome.'),
    'morphine':
        _TaperInfo('Opioid', 'Taper to avoid opioid withdrawal syndrome.'),
    'hydrocodone':
        _TaperInfo('Opioid', 'Taper to avoid opioid withdrawal syndrome.'),
    'fentanyl':
        _TaperInfo('Opioid', 'Taper required — withdrawal can be severe.'),
    'baclofen': _TaperInfo('Muscle relaxant',
        'Abrupt discontinuation can cause hallucinations, seizures; intrathecal baclofen withdrawal is life-threatening.'),
    'proton pump inhibitor (general)': _TaperInfo('PPI',
        'Rebound acid hypersecretion — step down gradually if used >8 weeks.'),
  };

  // ─── Renal Dose Adjustment Flags ──────────────────────────────────────────
  /// Meds with significant renal considerations
  static final Map<String, String> renalAdjust = {
    'metformin': 'Contraindicated if eGFR <30; dose-reduce if eGFR 30-45.',
    'gabapentin':
        'Dose-adjust based on eGFR — significant accumulation in CKD.',
    'pregabalin': 'Dose-adjust based on eGFR.',
    'digoxin': 'Reduce dose in renal impairment — narrow therapeutic index.',
    'lithium': 'Nephrotoxic and heavily renally cleared — monitor closely.',
    'enoxaparin': 'Dose-adjust if CrCl <30.',
    'apixaban': 'Adjust for age ≥80, weight ≤60 kg, and creatinine ≥1.5.',
    'rivaroxaban': 'Avoid if CrCl <15; dose-adjust if CrCl 15-50.',
    'dabigatran': 'Contraindicated if CrCl <30.',
    'ciprofloxacin': 'Dose-adjust in significant renal impairment.',
    'levofloxacin': 'Dose-adjust in significant renal impairment.',
    'trimethoprim-sulfamethoxazole': 'Dose-adjust if CrCl <30.',
    'vancomycin': 'Heavily renally cleared — TDM and adjustment required.',
    'nitrofurantoin': 'Avoid if CrCl <30 — ineffective and toxic.',
    'allopurinol': 'Dose-adjust in renal impairment — toxicity risk.',
    'methotrexate': 'Heavily renally cleared — nephrotoxic.',
    'sotalol': 'Dose-adjust in renal impairment — QT prolongation risk.',
    'lisinopril':
        'Monitor renal function; often used in CKD but requires caution.',
    'spironolactone': 'Hyperkalemia risk in CKD — monitor.',
  };

  // ─── Hepatic Dose Adjustment Flags ────────────────────────────────────────
  static final Map<String, String> hepaticAdjust = {
    'acetaminophen': 'Reduce max dose to 2 g/day in chronic liver disease.',
    'statins': 'Avoid in active liver disease; monitor LFTs.',
    'atorvastatin': 'Contraindicated in active liver disease.',
    'simvastatin': 'Contraindicated in active liver disease.',
    'methotrexate': 'Contraindicated in significant hepatic impairment.',
    'isotretinoin': 'Monitor LFTs; avoid in liver disease.',
    'amiodarone': 'Hepatotoxic — monitor LFTs.',
    'valproic acid': 'Black box hepatotoxicity — avoid in liver disease.',
    'rifampin': 'Hepatotoxic — monitor LFTs.',
    'isoniazid': 'Hepatotoxic — monitor LFTs.',
    'ketoconazole': 'Black box hepatotoxicity.',
    'warfarin':
        'Reduced synthesis of clotting factors in liver disease — complex dosing.',
  };

  // ─── Pregnancy-Risk Medications (Category D/X) ────────────────────────────
  /// Meds that are pregnancy Cat D or X
  static final Set<String> pregnancyCatD = {
    'aspirin',
    'methotrexate',
    'warfarin',
    'lisinopril',
    'losartan',
    'valsartan',
    'atenolol',
    'amiodarone',
    'carbamazepine',
    'phenytoin',
    'valproic acid',
    'topiramate',
    'lithium',
    'paroxetine',
    'lorazepam',
    'alprazolam',
    'clonazepam',
    'diazepam',
    'doxycycline',
    'aminocaproic acid',
    'phenobarbital',
    'tamoxifen',
    'hydrochlorothiazide',
  };

  static final Set<String> pregnancyCatX = {
    'methotrexate',
    'isotretinoin',
    'finasteride',
    'dutasteride',
    'simvastatin',
    'atorvastatin',
    'rosuvastatin',
    'pravastatin',
    'lovastatin',
    'warfarin',
    'mifepristone',
    'estradiol',
    'testosterone',
    'medroxyprogesterone',
    'letrozole',
    'anastrozole',
    'semaglutide',
    'levonorgestrel',
    'ethinyl estradiol/norethindrone',
  };

  // ─── Breastfeeding Risk ───────────────────────────────────────────────────
  static final Map<String, String> breastfeedingCaution = {
    'lithium': 'Use alternative if possible — concentrates in breastmilk.',
    'methotrexate': 'Contraindicated during breastfeeding.',
    'isotretinoin': 'Contraindicated during breastfeeding.',
    'amiodarone': 'Contraindicated — thyroid effects in infant.',
    'fluoxetine': 'Use with caution — long half-life metabolite.',
    'paroxetine': 'Generally preferred SSRI for breastfeeding.',
    'codeine': 'Avoid — ultra-rapid metabolizers risk infant death.',
    'oxycodone': 'Use with caution — monitor infant for sedation.',
    'aspirin': 'Avoid regular use — Reye syndrome risk.',
    'warfarin': 'Compatible with breastfeeding (minimal transfer).',
    'doxycycline': 'Avoid prolonged use — tooth discoloration risk.',
    'tetracycline': 'Avoid — tooth discoloration risk.',
  };

  // ─── Supplement Interactions ──────────────────────────────────────────────
  static final Map<String, List<String>> supplementInteractions = {
    'warfarin': [
      'Vitamin K (antagonizes warfarin)',
      'St. John\'s Wort (reduces warfarin effect)',
      'Ginkgo biloba (increases bleeding risk)',
      'Ginger (increases bleeding risk)',
      'Garlic (increases bleeding risk)',
      'Fish oil, high-dose (increases bleeding risk)',
    ],
    'sertraline': [
      'St. John\'s Wort (serotonin syndrome risk)',
      '5-HTP (serotonin syndrome risk)',
      'SAM-e (serotonin syndrome risk)',
    ],
    'fluoxetine': [
      'St. John\'s Wort (serotonin syndrome risk)',
      '5-HTP (serotonin syndrome risk)',
    ],
    'lithium': [
      'Sodium supplements (affect lithium levels)',
    ],
    'lisinopril': [
      'Potassium supplements (hyperkalemia risk)',
      'Licorice (may reduce antihypertensive effect)',
    ],
    'levothyroxine': [
      'Calcium (reduces absorption)',
      'Iron (reduces absorption)',
      'Magnesium (reduces absorption)',
      'Biotin (may affect thyroid lab tests)',
    ],
    'digoxin': [
      'St. John\'s Wort (reduces digoxin levels)',
      'Licorice (hypokalemia worsens toxicity)',
    ],
    'alprazolam': [
      'Kava (additive sedation, hepatotoxicity)',
      'Valerian root (additive sedation)',
    ],
    'metformin': [
      'Vitamin B12 (metformin depletes B12)',
    ],
    'birth control pills': [
      'St. John\'s Wort (reduces contraceptive effectiveness)',
    ],
    'cyclosporine': [
      'St. John\'s Wort (reduces levels — transplant rejection)',
      'Grapefruit (increases levels)',
    ],
  };

  // ─── Timing Rules for Schedule Optimizer ──────────────────────────────────
  static final Map<String, _TimingRule> timingRules = {
    'levothyroxine': _TimingRule(
      preferredTime: '6:00 AM',
      note:
          'Take on empty stomach, wait 30-60 min before food, coffee, calcium, or iron',
      icon: Icons.wb_twilight_rounded,
    ),
    'metformin': _TimingRule(
      preferredTime: 'With meals',
      note: 'Take with food to reduce GI upset',
      icon: Icons.restaurant_rounded,
    ),
    'simvastatin': _TimingRule(
      preferredTime: '9:00 PM',
      note: 'Evening dosing — cholesterol synthesis peaks overnight',
      icon: Icons.nights_stay_rounded,
    ),
    'atorvastatin': _TimingRule(
      preferredTime: 'Any time',
      note: 'Long half-life — can be taken at any consistent time',
      icon: Icons.schedule_rounded,
    ),
    'rosuvastatin': _TimingRule(
      preferredTime: 'Any time',
      note: 'Long half-life — can be taken at any consistent time',
      icon: Icons.schedule_rounded,
    ),
    'omeprazole': _TimingRule(
      preferredTime: '30 min before breakfast',
      note: 'Most effective when taken before first meal of the day',
      icon: Icons.coffee_rounded,
    ),
    'pantoprazole': _TimingRule(
      preferredTime: '30 min before breakfast',
      note: 'Take before first meal for best acid suppression',
      icon: Icons.coffee_rounded,
    ),
    'alendronate': _TimingRule(
      preferredTime: '6:00 AM (upright, empty stomach)',
      note:
          'Take with plain water; remain upright 30+ min; separate from all food/meds',
      icon: Icons.wb_twilight_rounded,
    ),
    'calcium carbonate': _TimingRule(
      preferredTime: 'With meals',
      note:
          'Better absorbed with food; separate from thyroid meds and quinolones',
      icon: Icons.restaurant_rounded,
    ),
    'iron (ferrous sulfate)': _TimingRule(
      preferredTime: 'Between meals if tolerated',
      note:
          'Better absorbed without food but often taken with food for tolerance; separate from thyroid meds and quinolones',
      icon: Icons.medication_rounded,
    ),
    'hydrochlorothiazide': _TimingRule(
      preferredTime: 'Morning',
      note: 'Avoid late dosing — diuresis affects sleep',
      icon: Icons.wb_sunny_rounded,
    ),
    'furosemide': _TimingRule(
      preferredTime: 'Morning (and early afternoon for BID)',
      note: 'Avoid evening — nocturia',
      icon: Icons.wb_sunny_rounded,
    ),
    'sertraline': _TimingRule(
      preferredTime: 'Morning',
      note: 'May cause insomnia if taken late',
      icon: Icons.wb_sunny_rounded,
    ),
    'bupropion': _TimingRule(
      preferredTime: 'Morning',
      note: 'Activating — avoid evening dosing',
      icon: Icons.wb_sunny_rounded,
    ),
    'mirtazapine': _TimingRule(
      preferredTime: 'Bedtime',
      note: 'Sedating — take at bedtime',
      icon: Icons.nights_stay_rounded,
    ),
    'trazodone': _TimingRule(
      preferredTime: 'Bedtime',
      note: 'Sedating — typically used for sleep',
      icon: Icons.nights_stay_rounded,
    ),
    'zolpidem': _TimingRule(
      preferredTime: 'Bedtime',
      note: 'Only take if you can stay in bed 7-8 hours',
      icon: Icons.nights_stay_rounded,
    ),
    'amlodipine': _TimingRule(
      preferredTime: 'Any time',
      note: 'Long half-life — any consistent time works',
      icon: Icons.schedule_rounded,
    ),
    'lisinopril': _TimingRule(
      preferredTime: 'Any time',
      note: 'Consistent timing matters more than specific time',
      icon: Icons.schedule_rounded,
    ),
    'metoprolol': _TimingRule(
      preferredTime: 'With meals',
      note: 'Bioavailability slightly improved with food',
      icon: Icons.restaurant_rounded,
    ),
    'ciprofloxacin': _TimingRule(
      preferredTime: 'Between meals',
      note: 'Separate from dairy, calcium, iron, antacids by 2+ hours',
      icon: Icons.schedule_rounded,
    ),
    'doxycycline': _TimingRule(
      preferredTime: 'With food (upright)',
      note:
          'Take with water; stay upright 30 min; separate from dairy by 1-2 hours',
      icon: Icons.restaurant_rounded,
    ),
  };

  // ─── Missed Dose Guidance ─────────────────────────────────────────────────
  static final Map<String, String> missedDoseGuidance = {
    'warfarin':
        'If <8 hours late, take missed dose. Otherwise skip and resume tomorrow. Never double.',
    'levothyroxine':
        'If <12 hours late, take it. If later, skip. Never double. Consider a morning reminder.',
    'sertraline':
        'Take as soon as you remember unless close to next dose. Never double.',
    'fluoxetine':
        'Long half-life — if you miss a dose, skip it and take next scheduled dose.',
    'escitalopram':
        'Take as soon as you remember unless next dose is close. Never double.',
    'metformin':
        'Take with your next meal. If >6 hours late to a scheduled dose, skip it.',
    'lisinopril':
        'Take as soon as you remember same day. If near next dose, skip.',
    'losartan':
        'Take as soon as you remember same day. If near next dose, skip.',
    'amlodipine':
        'Take as soon as you remember. Long half-life — missed dose usually okay.',
    'metoprolol':
        'Take as soon as you remember. If near next dose, skip — doubling causes bradycardia.',
    'simvastatin':
        'Take as soon as you remember that evening. If morning, skip and resume evening dose.',
    'atorvastatin':
        'Take as soon as you remember (long half-life tolerates this).',
    'omeprazole': 'Take when remembered on same day. If near next dose, skip.',
    'oral contraceptives':
        'Follow package insert — depends on how late and which week of pack.',
    'insulin': 'Never double. Check blood sugar; call prescriber if unsure.',
    'inhaled corticosteroids':
        'Take as soon as remembered. If close to next dose, skip — do not double.',
    'alprazolam':
        'Take if remembered promptly. If near next dose, skip — never double (sedation).',
    'anticoagulants (DOACs)':
        'Apixaban/rivaroxaban: take if same day. Dabigatran: take if >6h until next dose.',
    'antiretrovirals':
        'Take as soon as remembered — adherence is critical to prevent resistance.',
    'immunosuppressants':
        'Call prescriber promptly — timing is critical for transplant and autoimmune disease.',
  };
}

// ─── Small data classes ────────────────────────────────────────────────────

class _DrugInteraction {
  final String otherDrug;
  final InteractionSeverity severity;
  final String mechanism;
  _DrugInteraction(this.otherDrug, this.severity, this.mechanism);
}

class _FoodInteraction {
  final String food;
  final String advice;
  final InteractionSeverity severity;
  _FoodInteraction(this.food, this.advice, this.severity);
}

class _AlcoholInteraction {
  final InteractionSeverity severity;
  final String description;
  _AlcoholInteraction(this.severity, this.description);
}

class _TaperInfo {
  final String drugClass;
  final String guidance;
  const _TaperInfo(this.drugClass, this.guidance);
}

class _TimingRule {
  final String preferredTime;
  final String note;
  final IconData icon;
  _TimingRule({
    required this.preferredTime,
    required this.note,
    required this.icon,
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// WIDGET
// ═══════════════════════════════════════════════════════════════════════════

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration select = Duration(milliseconds: 220);
  static const Curve settle = Curves.easeOutCubic;
}

/// Press feedback that lives on pointer-down, not on release. Scales the
/// child down the instant a finger lands, releases when it lifts, and
/// springs back early if the finger travels ~10 px (a scroll, not a tap).
/// Honors the system Reduce Motion setting.
class _Pressable extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final double pressedScale;

  const _Pressable({
    Key? key,
    required this.child,
    this.onTap,
    this.onLongPress,
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
    final interactive = widget.onTap != null || widget.onLongPress != null;
    final scale = (_down && interactive && !reduce) ? widget.pressedScale : 1.0;
    final scaled = AnimatedScale(
      scale: scale,
      duration: _down ? _Motion.pressIn : _Motion.pressOut,
      curve: _down ? Curves.easeOut : _Motion.settle,
      child: widget.child,
    );
    return Semantics(
      button: interactive,
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
                onLongPress: widget.onLongPress,
                child: scaled,
              ),
      ),
    );
  }
}

class DrugInteractionCheckerWidget extends StatefulWidget {
  const DrugInteractionCheckerWidget({
    super.key,
    this.width,
    this.height,
  });

  final double? width;
  final double? height;

  @override
  State<DrugInteractionCheckerWidget> createState() =>
      _DrugInteractionCheckerWidgetState();
}

class _DrugInteractionCheckerWidgetState
    extends State<DrugInteractionCheckerWidget> with TickerProviderStateMixin {
  // ─── Tab & view state ────────────────────────────────────────────────────
  _Tab _tab = _Tab.interactions;
  bool _isLoading = true;
  bool _isCheckingNewDrug = false;
  String _searchQuery = '';
  final _searchController = TextEditingController();
  final _newDrugController = TextEditingController();

  // ─── Data state ──────────────────────────────────────────────────────────
  List<UserMedication> _meds = [];
  List<SafetyFinding> _findings = [];
  List<ReportedSideEffect> _sideEffects = [];
  List<String> _allergies = [];
  _PregnancyState _pregnancyState = _PregnancyState.none;
  bool _drinksAlcohol = false;
  String? _renalStatus; // null | 'mild' | 'moderate' | 'severe'
  String? _hepaticStatus; // null | 'mild' | 'moderate' | 'severe'

  // ─── Firestore refs ──────────────────────────────────────────────────────
  late String _uid;
  late CollectionReference _medsRef;
  late CollectionReference _sideEffectsRef;
  late DocumentReference _userRef;

  // ─── Animations ──────────────────────────────────────────────────────────
  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();

    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );
    _fadeController.forward();

    // No longer loops. An endlessly breathing icon is the kind of ambient
    // motion Apple asks apps to avoid; the alert colour and copy already
    // carry the urgency. Parked at rest (scale 1.0).
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..value = 1.0;
    _pulseAnimation = Tween<double>(
      begin: 0.92,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _pulseController,
      curve: Curves.easeInOut,
    ));

    _initFirestore();
  }

  @override
  void dispose() {
    _fadeController.dispose();
    _pulseController.dispose();
    _searchController.dispose();
    _newDrugController.dispose();
    super.dispose();
  }

  void _initFirestore() {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        if (mounted) setState(() => _isLoading = false);
        return;
      }
      _uid = user.uid;
      _userRef = FirebaseFirestore.instance.collection('users').doc(_uid);
      _medsRef =
          _userRef.collection('members').doc('self').collection('medications');
      _sideEffectsRef = _userRef.collection('side_effects');
      _loadData();
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadData() async {
    if (!mounted) return;
    setState(() => _isLoading = true);

    try {
      // Load medications
      final medsSnap = await _medsRef.get();
      _meds = medsSnap.docs.map((d) {
        final data = d.data() as Map<String, dynamic>;
        return UserMedication(
          id: d.id,
          name: (data['name'] ?? '').toString(),
          dosage: (data['dosage'] ?? '').toString(),
          strength: (data['strength'] ?? '').toString(),
          isAsNeeded: data['isAsNeeded'] == true,
          frequency: data['frequency']?.toString(),
        );
      }).toList();

      // Load user profile (allergies, pregnancy, alcohol, organ status)
      final userDoc = await _userRef.get();
      if (userDoc.exists) {
        final data = userDoc.data() as Map<String, dynamic>;
        _allergies = List<String>.from(data['allergies'] ?? []);

        final pregnant = data['isPregnant'] == true;
        final breastfeeding = data['isBreastfeeding'] == true;
        if (pregnant && breastfeeding) {
          _pregnancyState = _PregnancyState.both;
        } else if (pregnant) {
          _pregnancyState = _PregnancyState.pregnant;
        } else if (breastfeeding) {
          _pregnancyState = _PregnancyState.breastfeeding;
        } else {
          _pregnancyState = _PregnancyState.none;
        }

        _drinksAlcohol = data['drinksAlcohol'] == true;
        _renalStatus = data['renalImpairment'] as String?;
        _hepaticStatus = data['hepaticImpairment'] as String?;
      }

      // Load side effects
      try {
        final se = await _sideEffectsRef
            .orderBy('reportedAt', descending: true)
            .limit(30)
            .get();
        _sideEffects = se.docs.map((d) {
          final data = d.data() as Map<String, dynamic>;
          final ts = data['reportedAt'];
          DateTime when = DateTime.now();
          if (ts is Timestamp) when = ts.toDate();
          return ReportedSideEffect(
            id: d.id,
            medicationId: (data['medicationId'] ?? '').toString(),
            medicationName: (data['medicationName'] ?? '').toString(),
            severity: (data['severity'] ?? 'mild').toString(),
            description: (data['description'] ?? '').toString(),
            symptoms: List<String>.from(data['symptoms'] ?? []),
            reportedAt: when,
          );
        }).toList();
      } catch (_) {
        _sideEffects = [];
      }

      // Run safety analysis
      _runSafetyAnalysis();

      if (!mounted) return;
      setState(() => _isLoading = false);
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  // ═════════════════════════════════════════════════════════════════════════
  // SAFETY ANALYSIS ENGINE
  // ═════════════════════════════════════════════════════════════════════════

  void _runSafetyAnalysis() {
    final findings = <SafetyFinding>[];
    final medNames = _meds.map((m) => m.name.toLowerCase().trim()).toList();

    // 1. Drug-drug interactions
    for (int i = 0; i < medNames.length; i++) {
      final m1 = medNames[i];
      final list = _ClinicalRefs.drugDrug[_normalizeKey(m1)];
      if (list == null) continue;
      for (int j = 0; j < medNames.length; j++) {
        if (i == j) continue;
        final m2 = medNames[j];
        for (final inter in list) {
          if (_fuzzyMatch(m2, inter.otherDrug)) {
            // Avoid duplicate (since we iterate both directions)
            final existing = findings.any((f) =>
                f.kind == InteractionKind.drugDrug &&
                f.affectedMeds
                    .toSet()
                    .containsAll([_meds[i].name, _meds[j].name].toSet()));
            if (existing) continue;
            findings.add(SafetyFinding(
              kind: InteractionKind.drugDrug,
              severity: inter.severity,
              title: '${_meds[i].name} + ${_meds[j].name}',
              description: inter.mechanism,
              affectedMeds: [_meds[i].name, _meds[j].name],
              recommendation: _defaultRecommendation(inter.severity),
              source: 'Jovi Clinical DB',
            ));
          }
        }
      }
    }

    // 2. Drug-food interactions
    for (final med in _meds) {
      final key = _normalizeKey(med.name);
      final list = _ClinicalRefs.drugFood[key];
      if (list == null) continue;
      for (final fi in list) {
        findings.add(SafetyFinding(
          kind: InteractionKind.drugFood,
          severity: fi.severity,
          title: '${med.name} + ${fi.food}',
          description: fi.advice,
          affectedMeds: [med.name],
          source: 'Jovi Clinical DB',
        ));
      }
    }

    // 3. Drug-alcohol interactions
    if (_drinksAlcohol) {
      for (final med in _meds) {
        final key = _normalizeKey(med.name);
        final ai = _ClinicalRefs.alcohol[key];
        if (ai == null) continue;
        findings.add(SafetyFinding(
          kind: InteractionKind.drugAlcohol,
          severity: ai.severity,
          title: '${med.name} + Alcohol',
          description: ai.description,
          affectedMeds: [med.name],
          recommendation: 'Consider avoiding alcohol while on this medication.',
          source: 'Jovi Clinical DB',
        ));
      }
    }

    // 4. Drug-supplement interactions
    for (final med in _meds) {
      final key = _normalizeKey(med.name);
      final sups = _ClinicalRefs.supplementInteractions[key];
      if (sups == null) continue;
      for (final s in sups) {
        findings.add(SafetyFinding(
          kind: InteractionKind.drugSupplement,
          severity: InteractionSeverity.moderate,
          title: '${med.name} + $s',
          description:
              'Known supplement interaction. Discuss with pharmacist before combining.',
          affectedMeds: [med.name],
          source: 'Jovi Clinical DB',
        ));
      }
    }

    // 5. Duplicate therapy detection
    _ClinicalRefs.therapyClasses.forEach((className, drugs) {
      final matches = <String>[];
      for (final med in _meds) {
        final k = _normalizeKey(med.name);
        for (final d in drugs) {
          if (_fuzzyMatch(k, d)) {
            matches.add(med.name);
            break;
          }
        }
      }
      if (matches.length >= 2) {
        findings.add(SafetyFinding(
          kind: InteractionKind.duplicateTherapy,
          severity: className == 'NSAID' ||
                  className == 'Benzodiazepine' ||
                  className == 'Opioid' ||
                  className == 'SSRI' ||
                  className == 'SNRI'
              ? InteractionSeverity.major
              : InteractionSeverity.moderate,
          title: 'Duplicate $className therapy',
          description:
              'You appear to be taking multiple $className medications: ${matches.join(", ")}. This may be intentional but is often unintended.',
          affectedMeds: matches,
          recommendation:
              'Confirm with your prescriber this combination is intentional.',
          source: 'Jovi Clinical DB',
        ));
      }
    });

    // 6. Pregnancy safety
    if (_pregnancyState == _PregnancyState.pregnant ||
        _pregnancyState == _PregnancyState.both) {
      for (final med in _meds) {
        final key = _normalizeKey(med.name);
        if (_ClinicalRefs.pregnancyCatX.any((d) => _fuzzyMatch(key, d))) {
          findings.add(SafetyFinding(
            kind: InteractionKind.pregnancy,
            severity: InteractionSeverity.contraindicated,
            title: '${med.name}: Pregnancy Category X',
            description:
                'This medication is contraindicated in pregnancy. Talk to your prescriber immediately.',
            affectedMeds: [med.name],
            recommendation: 'Contact prescriber before taking another dose.',
            source: 'FDA',
          ));
        } else if (_ClinicalRefs.pregnancyCatD
            .any((d) => _fuzzyMatch(key, d))) {
          findings.add(SafetyFinding(
            kind: InteractionKind.pregnancy,
            severity: InteractionSeverity.major,
            title: '${med.name}: Pregnancy Category D',
            description:
                'Evidence of fetal risk. Use only if benefits outweigh risks.',
            affectedMeds: [med.name],
            recommendation: 'Discuss risk-benefit with your OB/prescriber.',
            source: 'FDA',
          ));
        }
      }
    }
    if (_pregnancyState == _PregnancyState.breastfeeding ||
        _pregnancyState == _PregnancyState.both) {
      for (final med in _meds) {
        final key = _normalizeKey(med.name);
        final note = _ClinicalRefs.breastfeedingCaution.entries.firstWhere(
            (e) => _fuzzyMatch(key, e.key),
            orElse: () => const MapEntry('', ''));
        if (note.value.isNotEmpty) {
          findings.add(SafetyFinding(
            kind: InteractionKind.pregnancy,
            severity: note.value.toLowerCase().contains('contraindicated')
                ? InteractionSeverity.contraindicated
                : InteractionSeverity.moderate,
            title: '${med.name}: Breastfeeding caution',
            description: note.value,
            affectedMeds: [med.name],
            source: 'LactMed',
          ));
        }
      }
    }

    // 7. Renal adjustment
    if (_renalStatus != null && _renalStatus!.isNotEmpty) {
      for (final med in _meds) {
        final key = _normalizeKey(med.name);
        final note = _ClinicalRefs.renalAdjust.entries.firstWhere(
            (e) => _fuzzyMatch(key, e.key),
            orElse: () => const MapEntry('', ''));
        if (note.value.isNotEmpty) {
          findings.add(SafetyFinding(
            kind: InteractionKind.renal,
            severity: _renalStatus == 'severe'
                ? InteractionSeverity.major
                : InteractionSeverity.moderate,
            title: '${med.name}: Kidney adjustment',
            description: note.value,
            affectedMeds: [med.name],
            recommendation:
                'Confirm dose is appropriate for your kidney function.',
            source: 'Jovi Clinical DB',
          ));
        }
      }
    }

    // 8. Hepatic adjustment
    if (_hepaticStatus != null && _hepaticStatus!.isNotEmpty) {
      for (final med in _meds) {
        final key = _normalizeKey(med.name);
        final note = _ClinicalRefs.hepaticAdjust.entries.firstWhere(
            (e) => _fuzzyMatch(key, e.key),
            orElse: () => const MapEntry('', ''));
        if (note.value.isNotEmpty) {
          findings.add(SafetyFinding(
            kind: InteractionKind.hepatic,
            severity: _hepaticStatus == 'severe'
                ? InteractionSeverity.major
                : InteractionSeverity.moderate,
            title: '${med.name}: Liver adjustment',
            description: note.value,
            affectedMeds: [med.name],
            recommendation:
                'Confirm dose is appropriate for your liver function.',
            source: 'Jovi Clinical DB',
          ));
        }
      }
    }

    // 9. Taper warnings (informational — not based on user state, shown in Safety tab)
    for (final med in _meds) {
      final key = _normalizeKey(med.name);
      final taper = _ClinicalRefs.taperRequired.entries.firstWhere(
          (e) => _fuzzyMatch(key, e.key),
          orElse: () => const MapEntry('', _TaperInfo('', '')));
      if (taper.key.isNotEmpty) {
        findings.add(SafetyFinding(
          kind: InteractionKind.taper,
          severity: InteractionSeverity.minor, // informational
          title: '${med.name}: Do not stop abruptly',
          description: taper.value.guidance,
          affectedMeds: [med.name],
          recommendation:
              'If you need to stop, talk to your prescriber about a taper plan.',
          source: 'Jovi Clinical DB',
        ));
      }
    }

    // 10. Allergy cross-reference (basic — exact match)
    for (final med in _meds) {
      for (final allergy in _allergies) {
        if (_fuzzyMatch(med.name.toLowerCase(), allergy.toLowerCase())) {
          findings.add(SafetyFinding(
            kind: InteractionKind.allergy,
            severity: InteractionSeverity.contraindicated,
            title: '${med.name}: Listed allergy',
            description:
                'You have $allergy listed as an allergy. This medication may match that class.',
            affectedMeds: [med.name],
            recommendation: 'STOP and contact your prescriber immediately.',
            source: 'Your Allergy List',
          ));
        }
      }
    }

    // Sort by severity (worst first)
    findings.sort((a, b) {
      final order = {
        InteractionSeverity.contraindicated: 0,
        InteractionSeverity.major: 1,
        InteractionSeverity.moderate: 2,
        InteractionSeverity.minor: 3,
      };
      return order[a.severity]!.compareTo(order[b.severity]!);
    });

    _findings = findings;
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  String _normalizeKey(String s) {
    return s
        .toLowerCase()
        .trim()
        .replaceAll(
            RegExp(r'\s+\(.*?\)'), '') // strip parenthetical brand names
        .trim();
  }

  bool _fuzzyMatch(String a, String b) {
    final x = a.toLowerCase().trim();
    final y = b.toLowerCase().trim();
    if (x == y) return true;
    if (x.contains(y) || y.contains(x)) return true;
    return false;
  }

  String _defaultRecommendation(InteractionSeverity s) {
    switch (s) {
      case InteractionSeverity.contraindicated:
        return 'Do not combine. Contact your prescriber immediately.';
      case InteractionSeverity.major:
        return 'Significant risk — discuss with prescriber or pharmacist before continuing.';
      case InteractionSeverity.moderate:
        return 'May require dose adjustment or monitoring — discuss with your provider.';
      case InteractionSeverity.minor:
        return 'Monitor for symptoms; usually manageable.';
    }
  }

  // ─── FDA API (supplementary) ──────────────────────────────────────────────

  Future<Map<String, dynamic>?> _fetchFDAData(String drugName) async {
    try {
      final encoded = Uri.encodeComponent(drugName.toLowerCase().trim());
      final url =
          'https://api.fda.gov/drug/label.json?search=openfda.brand_name:"$encoded"+OR+openfda.generic_name:"$encoded"&limit=1';
      final resp =
          await http.get(Uri.parse(url)).timeout(const Duration(seconds: 6));
      if (resp.statusCode == 200) {
        final data = json.decode(resp.body);
        if (data['results'] != null && (data['results'] as List).isNotEmpty) {
          return (data['results'] as List).first as Map<String, dynamic>;
        }
      }
    } catch (_) {}
    return null;
  }

  // ─── Summary helpers ──────────────────────────────────────────────────────

  int _severityCount(InteractionSeverity s) =>
      _findings.where((f) => f.severity == s).length;

  int _kindCount(InteractionKind k) =>
      _findings.where((f) => f.kind == k).length;

  InteractionSeverity get _worstSeverity {
    if (_findings.isEmpty) return InteractionSeverity.minor;
    return _findings.first.severity;
  }

  // ─── Responsive config ────────────────────────────────────────────────────
  ResponsiveConfig _config(BoxConstraints c) {
    final w = c.maxWidth;
    final h = c.maxHeight;
    final isTwoColumn = w > 800 && w / h > 0.9;
    return ResponsiveConfig(
      paddingH: w < 400 ? 16 : 20,
      paddingV: 16,
      contentMax: isTwoColumn ? 1000 : 680,
      actionColumns: w < 400 ? 2 : (w < 700 ? 3 : 4),
      actionItemHeight: 88,
      actionIconDimension: 24,
      actionTextSize: 12,
      wideMode: w > 700,
      hasHinge: false,
      useTwoColumnLayout: isTwoColumn,
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GLASS HELPERS
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _glassCard({
    required Widget child,
    double radius = 18,
    EdgeInsets padding = const EdgeInsets.all(16),
    Color? tintColor,
    double tintOpacity = 0.10,
    double blur = 14,
  }) {
    // Painted glass, not a BackdropFilter: dozens of live blur layers inside
    // a scroll view were the single biggest GPU cost on this screen, and the
    // background is an opaque navy gradient so the blur had nothing to show.
    // Blur is kept for the real modals (dialogs and bottom sheets).
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: Container(
        decoration: BoxDecoration(
          color: tintColor != null
              ? tintColor.withOpacity(tintOpacity + 0.02)
              : Colors.white.withOpacity(0.09),
          borderRadius: BorderRadius.circular(radius),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1),
        ),
        padding: padding,
        child: child,
      ),
    );
  }

  Widget _glassPill({
    required Widget child,
    EdgeInsets? padding,
    Color? tint,
  }) {
    return Container(
      padding:
          padding ?? const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: tint?.withOpacity(0.18) ?? Colors.white.withOpacity(0.1),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(
          color: tint?.withOpacity(0.35) ?? Colors.white.withOpacity(0.14),
          width: 1,
        ),
      ),
      child: child,
    );
  }

  Widget _coralGradientIcon(IconData icon, {double size = 22}) {
    return ShaderMask(
      shaderCallback: (r) => _Jovi.coralGradient.createShader(r),
      child: Icon(icon, size: size, color: Colors.white),
    );
  }

  Widget _sectionHeader(
    String label, {
    IconData? icon,
    Widget? trailing,
  }) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 10, 4, 12),
      child: Row(
        children: [
          if (icon != null) ...[
            _coralGradientIcon(icon, size: 16),
            const SizedBox(width: 8),
          ],
          Expanded(
            child: Text(
              label.toUpperCase(),
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w700,
                fontSize: 11.5,
                letterSpacing: 1.2,
              ),
            ),
          ),
          if (trailing != null) trailing,
        ],
      ),
    );
  }

  Widget _emptyState({
    required IconData icon,
    required String title,
    required String subtitle,
    Widget? action,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.06),
                shape: BoxShape.circle,
                border:
                    Border.all(color: Colors.white.withOpacity(0.12), width: 1),
              ),
              child:
                  Icon(icon, color: Colors.white.withOpacity(0.65), size: 30),
            ),
            const SizedBox(height: 16),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              subtitle,
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: Colors.white.withOpacity(0.65),
                  fontSize: 13,
                  height: 1.4),
            ),
            if (action != null) ...[
              const SizedBox(height: 16),
              action,
            ],
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // NAVY GLASS DIALOG HELPERS
  // ═══════════════════════════════════════════════════════════════════════════

  void _showNavyDialog({
    required Widget child,
    EdgeInsets insetPadding = const EdgeInsets.symmetric(horizontal: 28),
  }) {
    showDialog(
      context: context,
      barrierColor: Colors.black.withOpacity(0.5),
      builder: (_) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: insetPadding,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(24),
          child: BackdropFilter(
            filter: ui.ImageFilter.blur(sigmaX: 18, sigmaY: 18),
            child: Container(
              decoration: BoxDecoration(
                color: _Jovi.navy.withOpacity(0.92),
                borderRadius: BorderRadius.circular(24),
                border:
                    Border.all(color: Colors.white.withOpacity(0.12), width: 1),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.5),
                    blurRadius: 40,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              padding: const EdgeInsets.all(22),
              child: child,
            ),
          ),
        ),
      ),
    );
  }

  void _showNavyBottomSheet({required Widget child, double? heightFactor}) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.5),
      isScrollControlled: true,
      // Rises with the keyboard so the primary button is never hidden.
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: FractionallySizedBox(
        heightFactor: heightFactor ?? 0.86,
        child: ClipRRect(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(26)),
          child: BackdropFilter(
            filter: ui.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
            child: Container(
              decoration: BoxDecoration(
                gradient: _Jovi.navyGradient,
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(26)),
                border: Border(
                  top: BorderSide(
                      color: Colors.white.withOpacity(0.12), width: 1),
                ),
              ),
              child: child,
            ),
          ),
        ),
      )),
    );
  }

  Widget _sheetHandle() {
    return Center(
      child: Container(
        margin: const EdgeInsets.only(top: 10, bottom: 8),
        width: 36,
        height: 4,
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.25),
          borderRadius: BorderRadius.circular(100),
        ),
      ),
    );
  }

  Widget _primaryButton({
    required String label,
    required VoidCallback onTap,
    IconData? icon,
    bool loading = false,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: loading ? null : onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          decoration: BoxDecoration(
            gradient: _Jovi.coralGradient,
            borderRadius: BorderRadius.circular(14),
            boxShadow: [
              BoxShadow(
                color: _Jovi.coral.withOpacity(0.35),
                blurRadius: 14,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (loading)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation(Colors.white),
                  ),
                )
              else if (icon != null) ...[
                Icon(icon, color: Colors.white, size: 16),
                const SizedBox(width: 8),
              ],
              if (!loading)
                Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
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
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.08),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: Colors.white.withOpacity(0.18),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, color: Colors.white, size: 16),
                const SizedBox(width: 8),
              ],
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
    );
  }

  void _showSnack(String message, {bool isError = false}) {
    if (!mounted) return;
    final accent = isError ? _Jovi.errorRed : _Jovi.mint;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              isError
                  ? CupertinoIcons.exclamationmark_circle
                  : CupertinoIcons.checkmark_circle,
              color: accent,
              size: 20,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.2),
              ),
            ),
          ],
        ),
        backgroundColor: _Jovi.navyMid,
        elevation: 0,
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
        duration: Duration(milliseconds: isError ? 3600 : 2600),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: accent.withOpacity(0.35)),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SEVERITY BADGE / CHIPS
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _severityBadge(InteractionSeverity s) {
    final color = _Jovi.severityColor(s);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.18),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withOpacity(0.45), width: 1),
      ),
      child: Text(
        s.label.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 9.5,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.8,
        ),
      ),
    );
  }

  Widget _sourceBadge(String source) {
    return _glassPill(
      tint: _Jovi.mint,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      child: Text(
        source,
        style: TextStyle(
          color: _Jovi.mint,
          fontSize: 9.5,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.5,
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // INTERACTIONS TAB
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildInteractionsTab(ResponsiveConfig cfg) {
    if (_meds.isEmpty) {
      return _emptyState(
        icon: Icons.medication_outlined,
        title: 'No medications to check',
        subtitle:
            'Add your current medications to your profile to run safety checks.',
      );
    }

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 90),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildSummaryCard(),
          const SizedBox(height: 14),
          if (_findings.isNotEmpty) _buildHeatMap(),
          const SizedBox(height: 14),
          _buildQuickCheckCard(),
          const SizedBox(height: 20),
          if (_findings.isEmpty)
            _buildNoFindingsCard()
          else
            _buildFindingsList(),
          const SizedBox(height: 14),
          _buildGenerateReportButton(),
        ],
      ),
    );
  }

  // ─── Summary Card ────────────────────────────────────────────────────────

  Widget _buildSummaryCard() {
    final worst = _worstSeverity;
    final contraindicated = _severityCount(InteractionSeverity.contraindicated);
    final major = _severityCount(InteractionSeverity.major);
    final moderate = _severityCount(InteractionSeverity.moderate);
    final minor = _severityCount(InteractionSeverity.minor);
    final total = _findings.length;
    final worstColor = _Jovi.severityColor(worst);

    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: LinearGradient(
              colors: total == 0
                  ? [
                      _Jovi.mint.withOpacity(0.22),
                      _Jovi.mintDark.withOpacity(0.14),
                    ]
                  : [
                      worstColor.withOpacity(0.25),
                      worstColor.withOpacity(0.15),
                    ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            border: Border.all(
              color: total == 0
                  ? _Jovi.mint.withOpacity(0.35)
                  : worstColor.withOpacity(0.4),
              width: 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  ScaleTransition(
                    scale: total > 0
                        ? _pulseAnimation
                        : const AlwaysStoppedAnimation(1.0),
                    child: Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        gradient: total == 0
                            ? LinearGradient(
                                colors: [_Jovi.mint, _Jovi.mintDark])
                            : LinearGradient(
                                colors: [
                                  worstColor,
                                  worstColor.withOpacity(0.7),
                                ],
                              ),
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [
                          BoxShadow(
                            color: (total == 0 ? _Jovi.mint : worstColor)
                                .withOpacity(0.4),
                            blurRadius: 14,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Icon(
                        total == 0
                            ? Icons.verified_rounded
                            : Icons.health_and_safety_rounded,
                        color: Colors.white,
                        size: 24,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          total == 0
                              ? 'All Clear'
                              : total == 1
                                  ? '1 safety finding'
                                  : '$total safety findings',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.3,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          total == 0
                              ? 'No interactions detected across your medications.'
                              : worst == InteractionSeverity.contraindicated
                                  ? 'Contraindicated combinations need immediate attention.'
                                  : worst == InteractionSeverity.major
                                      ? 'Major risks found — review below.'
                                      : 'Review findings and discuss with your provider.',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.88),
                            fontSize: 12.5,
                            height: 1.35,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              if (total > 0) ...[
                const SizedBox(height: 14),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    if (contraindicated > 0)
                      _severityChip('$contraindicated Contraindicated',
                          InteractionSeverity.contraindicated),
                    if (major > 0)
                      _severityChip('$major Major', InteractionSeverity.major),
                    if (moderate > 0)
                      _severityChip(
                          '$moderate Moderate', InteractionSeverity.moderate),
                    if (minor > 0)
                      _severityChip('$minor Minor', InteractionSeverity.minor),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _severityChip(String label, InteractionSeverity s) {
    final color = _Jovi.severityColor(s);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(color: color.withOpacity(0.5), width: 1),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: Colors.white,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  // ─── Heat Map Visualization ──────────────────────────────────────────────

  Widget _buildHeatMap() {
    // Build adjacency: pairs of meds that have drug-drug findings
    final drugDrugFindings =
        _findings.where((f) => f.kind == InteractionKind.drugDrug).toList();
    if (drugDrugFindings.isEmpty && _meds.length < 2) {
      return const SizedBox.shrink();
    }

    return _glassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _coralGradientIcon(Icons.hub_rounded, size: 16),
              const SizedBox(width: 8),
              const Text(
                'INTERACTION MAP',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.1,
                ),
              ),
              const Spacer(),
              Text(
                '${_meds.length} medication${_meds.length == 1 ? "" : "s"}',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 10.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 200,
            child: CustomPaint(
              size: Size.infinite,
              painter: _InteractionMapPainter(
                meds: _meds.map((m) => m.name).toList(),
                findings: drugDrugFindings,
                coral: _Jovi.coral,
                coralLight: _Jovi.coralLight,
                severityColor: _Jovi.severityColor,
                textColor: Colors.white,
              ),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _heatMapLegend('Safe', _Jovi.mint),
              _heatMapLegend('Minor', _Jovi.mint),
              _heatMapLegend('Moderate', _Jovi.gold),
              _heatMapLegend('Major', _Jovi.errorRed),
            ],
          ),
        ],
      ),
    );
  }

  Widget _heatMapLegend(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 3,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.7),
            fontSize: 10,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  // ─── Quick Check Card ────────────────────────────────────────────────────

  Widget _buildQuickCheckCard() {
    return _glassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  gradient: _Jovi.coralGradient,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.add_circle_outline_rounded,
                    color: Colors.white, size: 18),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Quick Check',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w700),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Test a new medication before adding',
                      style: TextStyle(color: Colors.white70, fontSize: 11.5),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _glassCard(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            radius: 14,
            child: Row(
              children: [
                const SizedBox(width: 12),
                Icon(Icons.medication_outlined,
                    color: Colors.white.withOpacity(0.7), size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _newDrugController,
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                    cursorColor: _Jovi.coral,
                    autocorrect: false,
                    textInputAction: TextInputAction.search,
                    onSubmitted: (_) => _checkNewMedication(),
                    decoration: InputDecoration(
                      hintText: 'Medication name…',
                      hintStyle: TextStyle(
                          color: Colors.white.withOpacity(0.5), fontSize: 13.5),
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: _primaryButton(
                    label: 'Check',
                    onTap: _checkNewMedication,
                    loading: _isCheckingNewDrug,
                    icon: Icons.search_rounded,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─── No findings card ────────────────────────────────────────────────────

  Widget _buildNoFindingsCard() {
    return _glassCard(
      padding: const EdgeInsets.all(20),
      radius: 18,
      tintColor: _Jovi.mint,
      tintOpacity: 0.08,
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [_Jovi.mint, _Jovi.mintDark],
              ),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: _Jovi.mint.withOpacity(0.35),
                  blurRadius: 16,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(Icons.verified_rounded,
                color: Colors.white, size: 30),
          ),
          const SizedBox(height: 12),
          const Text(
            'No Safety Findings',
            style: TextStyle(
                color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          Text(
            'Your current medications have no detected interactions, duplicate therapies, or safety flags.',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: Colors.white.withOpacity(0.75),
                fontSize: 13,
                height: 1.4),
          ),
        ],
      ),
    );
  }

  // ─── Findings List (grouped by severity) ─────────────────────────────────

  Widget _buildFindingsList() {
    // Group by severity
    final Map<InteractionSeverity, List<SafetyFinding>> grouped = {};
    for (final f in _findings) {
      grouped.putIfAbsent(f.severity, () => []).add(f);
    }
    final order = [
      InteractionSeverity.contraindicated,
      InteractionSeverity.major,
      InteractionSeverity.moderate,
      InteractionSeverity.minor,
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final sev in order)
          if (grouped.containsKey(sev)) ...[
            _sectionHeader(
              '${sev.label} — ${grouped[sev]!.length}',
              icon: _severityIcon(sev),
            ),
            ...grouped[sev]!.map((f) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildFindingCard(f),
                )),
          ],
      ],
    );
  }

  IconData _severityIcon(InteractionSeverity s) {
    switch (s) {
      case InteractionSeverity.contraindicated:
        return Icons.dangerous_rounded;
      case InteractionSeverity.major:
        return Icons.warning_rounded;
      case InteractionSeverity.moderate:
        return Icons.error_outline_rounded;
      case InteractionSeverity.minor:
        return Icons.info_outline_rounded;
    }
  }

  Widget _buildFindingCard(SafetyFinding f) {
    final color = _Jovi.severityColor(f.severity);
    final isSevere = f.severity == InteractionSeverity.major ||
        f.severity == InteractionSeverity.contraindicated;
    return _Pressable(
      onTap: () => _showFindingDetails(f),
      child: _glassCard(
        padding: const EdgeInsets.all(14),
        radius: 14,
        tintColor: isSevere ? color : null,
        tintOpacity: isSevere ? 0.06 : 0.1,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(10),
                    border:
                        Border.all(color: color.withOpacity(0.45), width: 1),
                  ),
                  child: Icon(f.kind.icon, color: color, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        f.title,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        f.kind.label,
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.55),
                            fontSize: 11,
                            fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
                ),
                _severityBadge(f.severity),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              f.description,
              style: const TextStyle(
                  color: Colors.white, fontSize: 12.5, height: 1.45),
            ),
            if (f.source != null) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  Icon(Icons.verified_outlined,
                      color: Colors.white.withOpacity(0.55), size: 12),
                  const SizedBox(width: 5),
                  Text(
                    f.source!,
                    style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w500),
                  ),
                  const Spacer(),
                  Icon(Icons.arrow_forward_ios_rounded,
                      color: Colors.white.withOpacity(0.4), size: 11),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _showFindingDetails(SafetyFinding f) {
    final color = _Jovi.severityColor(f.severity);
    _showNavyDialog(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: color.withOpacity(0.45), width: 1),
                ),
                child: Icon(f.kind.icon, color: color, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      f.title,
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 2),
                    _severityBadge(f.severity),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Details',
            style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 10.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 1.2),
          ),
          const SizedBox(height: 6),
          Text(
            f.description,
            style: const TextStyle(
                color: Colors.white, fontSize: 13.5, height: 1.5),
          ),
          if (f.recommendation != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: _Jovi.coral.withOpacity(0.12),
                borderRadius: BorderRadius.circular(12),
                border:
                    Border.all(color: _Jovi.coral.withOpacity(0.35), width: 1),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.lightbulb_outline_rounded,
                      color: _Jovi.coral, size: 18),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'RECOMMENDATION',
                          style: TextStyle(
                              color: _Jovi.coral,
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1.1),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          f.recommendation!,
                          style: const TextStyle(
                              color: Colors.white, fontSize: 12.5, height: 1.4),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (f.source != null) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(Icons.verified_outlined,
                    color: Colors.white.withOpacity(0.55), size: 12),
                const SizedBox(width: 5),
                Text(
                  'Source: ${f.source}',
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 11,
                      fontWeight: FontWeight.w500),
                ),
              ],
            ),
          ],
          const SizedBox(height: 18),
          SizedBox(
            width: double.infinity,
            child: _primaryButton(
              label: 'Close',
              onTap: () => Navigator.of(context).pop(),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Generate Report Button ──────────────────────────────────────────────

  Widget _buildGenerateReportButton() {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: _generateReport,
        child: _glassCard(
          padding: const EdgeInsets.all(14),
          radius: 16,
          tintColor: _Jovi.coral,
          tintOpacity: 0.10,
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  gradient: _Jovi.coralGradient,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Icon(Icons.description_rounded,
                    color: Colors.white, size: 20),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Doctor Report',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Copy a shareable summary for your provider',
                      style: TextStyle(color: Colors.white70, fontSize: 11.5),
                    ),
                  ],
                ),
              ),
              Icon(Icons.copy_rounded, color: _Jovi.coral, size: 18),
            ],
          ),
        ),
      ),
    );
  }

  // ─── Quick check flow ────────────────────────────────────────────────────

  Future<void> _checkNewMedication() async {
    final drug = _newDrugController.text.trim();
    if (drug.isEmpty) return;
    if (!mounted) return;
    setState(() => _isCheckingNewDrug = true);

    final findings = <SafetyFinding>[];
    final key = _normalizeKey(drug);

    // Check against all known interactions
    for (final med in _meds) {
      final medKey = _normalizeKey(med.name);

      // Check drug-drug (in both directions)
      final list1 = _ClinicalRefs.drugDrug[key];
      if (list1 != null) {
        for (final i in list1) {
          if (_fuzzyMatch(medKey, i.otherDrug)) {
            findings.add(SafetyFinding(
              kind: InteractionKind.drugDrug,
              severity: i.severity,
              title: '$drug + ${med.name}',
              description: i.mechanism,
              affectedMeds: [drug, med.name],
              source: 'Jovi Clinical DB',
            ));
          }
        }
      }
      final list2 = _ClinicalRefs.drugDrug[medKey];
      if (list2 != null) {
        for (final i in list2) {
          if (_fuzzyMatch(key, i.otherDrug)) {
            final dup = findings.any((f) =>
                f.affectedMeds.toSet().containsAll([drug, med.name].toSet()));
            if (!dup) {
              findings.add(SafetyFinding(
                kind: InteractionKind.drugDrug,
                severity: i.severity,
                title: '$drug + ${med.name}',
                description: i.mechanism,
                affectedMeds: [drug, med.name],
                source: 'Jovi Clinical DB',
              ));
            }
          }
        }
      }
    }

    // Alcohol check
    if (_drinksAlcohol) {
      final ai = _ClinicalRefs.alcohol[key];
      if (ai != null) {
        findings.add(SafetyFinding(
          kind: InteractionKind.drugAlcohol,
          severity: ai.severity,
          title: '$drug + Alcohol',
          description: ai.description,
          affectedMeds: [drug],
          source: 'Jovi Clinical DB',
        ));
      }
    }

    // Pregnancy check
    if (_pregnancyState == _PregnancyState.pregnant ||
        _pregnancyState == _PregnancyState.both) {
      if (_ClinicalRefs.pregnancyCatX.any((d) => _fuzzyMatch(key, d))) {
        findings.add(SafetyFinding(
          kind: InteractionKind.pregnancy,
          severity: InteractionSeverity.contraindicated,
          title: '$drug: Pregnancy Category X',
          description: 'Contraindicated during pregnancy.',
          affectedMeds: [drug],
          source: 'FDA',
        ));
      } else if (_ClinicalRefs.pregnancyCatD.any((d) => _fuzzyMatch(key, d))) {
        findings.add(SafetyFinding(
          kind: InteractionKind.pregnancy,
          severity: InteractionSeverity.major,
          title: '$drug: Pregnancy Category D',
          description: 'Evidence of fetal risk.',
          affectedMeds: [drug],
          source: 'FDA',
        ));
      }
    }

    // Try FDA API for supplementary info
    Map<String, dynamic>? fdaData;
    try {
      fdaData = await _fetchFDAData(drug);
    } catch (_) {}

    if (!mounted) return;
    setState(() => _isCheckingNewDrug = false);

    _showQuickCheckResult(drug, findings, fdaData);
    _newDrugController.clear();
  }

  void _showQuickCheckResult(String drug, List<SafetyFinding> findings,
      Map<String, dynamic>? fdaData) {
    final worst = findings.isEmpty
        ? InteractionSeverity.minor
        : findings.map((f) => f.severity).reduce((a, b) {
            final order = {
              InteractionSeverity.contraindicated: 0,
              InteractionSeverity.major: 1,
              InteractionSeverity.moderate: 2,
              InteractionSeverity.minor: 3,
            };
            return order[a]! < order[b]! ? a : b;
          });

    _showNavyBottomSheet(
      heightFactor: 0.75,
      child: Column(
        children: [
          _sheetHandle(),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
              physics: const BouncingScrollPhysics(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          gradient: findings.isEmpty
                              ? LinearGradient(
                                  colors: [_Jovi.mint, _Jovi.mintDark])
                              : LinearGradient(
                                  colors: [
                                    _Jovi.severityColor(worst),
                                    _Jovi.severityColor(worst).withOpacity(0.7),
                                  ],
                                ),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Icon(
                          findings.isEmpty
                              ? Icons.check_circle_rounded
                              : Icons.health_and_safety_rounded,
                          color: Colors.white,
                          size: 24,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              drug,
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 18,
                                  fontWeight: FontWeight.w800),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              findings.isEmpty
                                  ? 'No interactions detected'
                                  : '${findings.length} potential issue${findings.length == 1 ? "" : "s"}',
                              style: TextStyle(
                                color: findings.isEmpty
                                    ? _Jovi.mint
                                    : _Jovi.severityColor(worst),
                                fontSize: 12.5,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  if (findings.isEmpty)
                    _glassCard(
                      padding: const EdgeInsets.all(16),
                      radius: 14,
                      tintColor: _Jovi.mint,
                      tintOpacity: 0.08,
                      child: Row(
                        children: [
                          Icon(Icons.check_circle_outline_rounded,
                              color: _Jovi.mint, size: 22),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Text(
                              'No known interactions were found with your current medications, alcohol use, or pregnancy status.',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 13,
                                  height: 1.4),
                            ),
                          ),
                        ],
                      ),
                    )
                  else
                    ...findings.map((f) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: _buildFindingCard(f),
                        )),
                  if (fdaData != null) ...[
                    const SizedBox(height: 14),
                    _buildFDASnippet(fdaData),
                  ],
                  const SizedBox(height: 14),
                  Text(
                    'This is an educational screening, not medical advice. Always confirm with your prescriber or pharmacist.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 11,
                      fontStyle: FontStyle.italic,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
            child: SizedBox(
              width: double.infinity,
              child: _primaryButton(
                label: 'Close',
                onTap: () => Navigator.of(context).pop(),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFDASnippet(Map<String, dynamic> fdaData) {
    final warnings = fdaData['warnings'];
    String? warningText;
    if (warnings is List && warnings.isNotEmpty) {
      warningText = warnings.first.toString();
      if (warningText.length > 280) {
        warningText = '${warningText.substring(0, 280)}…';
      }
    }
    if (warningText == null) return const SizedBox.shrink();

    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      tintColor: _Jovi.gold,
      tintOpacity: 0.06,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: _Jovi.gold, size: 16),
              const SizedBox(width: 8),
              Text(
                'FDA LABEL SNIPPET',
                style: TextStyle(
                    color: _Jovi.gold,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            warningText,
            style: const TextStyle(
                color: Colors.white, fontSize: 12, height: 1.45),
          ),
        ],
      ),
    );
  }

  // ─── Doctor report (copy to clipboard) ───────────────────────────────────

  void _generateReport() {
    final sb = StringBuffer();
    sb.writeln('MEDICATION SAFETY REPORT');
    sb.writeln('Generated via Jovi Health');
    sb.writeln('Date: ${DateTime.now().toString().split('.').first}');
    sb.writeln();

    sb.writeln('CURRENT MEDICATIONS (${_meds.length}):');
    for (final m in _meds) {
      sb.write('• ${m.name}');
      if (m.dosage.isNotEmpty || m.strength.isNotEmpty) {
        sb.write(' — ${m.dosage} ${m.strength}'.trim());
      }
      if (m.isAsNeeded) sb.write(' (as needed)');
      sb.writeln();
    }

    if (_allergies.isNotEmpty) {
      sb.writeln();
      sb.writeln('ALLERGIES:');
      for (final a in _allergies) {
        sb.writeln('• $a');
      }
    }

    final profile = <String>[];
    if (_pregnancyState == _PregnancyState.pregnant ||
        _pregnancyState == _PregnancyState.both) {
      profile.add('Pregnant');
    }
    if (_pregnancyState == _PregnancyState.breastfeeding ||
        _pregnancyState == _PregnancyState.both) {
      profile.add('Breastfeeding');
    }
    if (_drinksAlcohol) profile.add('Uses alcohol');
    if (_renalStatus != null) profile.add('Renal impairment ($_renalStatus)');
    if (_hepaticStatus != null)
      profile.add('Hepatic impairment ($_hepaticStatus)');
    if (profile.isNotEmpty) {
      sb.writeln();
      sb.writeln('RELEVANT HEALTH FACTORS:');
      for (final p in profile) {
        sb.writeln('• $p');
      }
    }

    if (_findings.isNotEmpty) {
      sb.writeln();
      sb.writeln('SAFETY FINDINGS (${_findings.length}):');
      for (final f in _findings) {
        sb.writeln();
        sb.writeln('[${f.severity.label}] ${f.title}');
        sb.writeln('  Type: ${f.kind.label}');
        sb.writeln('  ${f.description}');
        if (f.recommendation != null) {
          sb.writeln('  → ${f.recommendation}');
        }
      }
    } else {
      sb.writeln();
      sb.writeln('SAFETY FINDINGS: None detected.');
    }

    sb.writeln();
    sb.writeln('---');
    sb.writeln(
        'This report is a screening, not a clinical diagnosis. Always verify with your prescriber or pharmacist.');

    Clipboard.setData(ClipboardData(text: sb.toString()));
    HapticFeedback.lightImpact();
    _showSnack('Report copied — paste into a message to your doctor');
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SCHEDULE TAB — Timing Optimizer
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildScheduleTab(ResponsiveConfig cfg) {
    if (_meds.isEmpty) {
      return _emptyState(
        icon: Icons.schedule_rounded,
        title: 'No medications to schedule',
        subtitle:
            'Add medications in your profile to see a timing-optimized daily plan.',
      );
    }

    final suggestions = _buildTimingSuggestions();
    final conflicts = _detectTimingConflicts();

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 90),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _glassCard(
            padding: const EdgeInsets.all(16),
            radius: 18,
            tintColor: _Jovi.gold,
            tintOpacity: 0.08,
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [_Jovi.gold, _Jovi.goldDark],
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.schedule_rounded,
                      color: Colors.white, size: 20),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Optimized Daily Schedule',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w700),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Based on how each med absorbs and interacts',
                        style: TextStyle(color: Colors.white70, fontSize: 11.5),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          if (conflicts.isNotEmpty) ...[
            _sectionHeader('Timing Conflicts',
                icon: Icons.warning_amber_rounded),
            ...conflicts.map((c) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildConflictCard(c),
                )),
            const SizedBox(height: 6),
          ],
          if (suggestions.isEmpty)
            _glassCard(
              padding: const EdgeInsets.all(20),
              radius: 16,
              child: Column(
                children: [
                  Icon(Icons.schedule_rounded,
                      color: Colors.white.withOpacity(0.6), size: 32),
                  const SizedBox(height: 10),
                  Text(
                    'No specific timing guidance',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.85),
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Your medications don\'t have strict timing requirements. Follow your prescriber\'s instructions.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 12.5,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            )
          else ...[
            _sectionHeader('Recommended Timing',
                icon: Icons.access_time_rounded),
            ...suggestions.map((s) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildTimingCard(s),
                )),
          ],
          const SizedBox(height: 16),
          _buildMedsWithoutTimingSection(),
        ],
      ),
    );
  }

  List<TimingSuggestion> _buildTimingSuggestions() {
    final suggestions = <TimingSuggestion>[];
    for (final med in _meds) {
      final key = _normalizeKey(med.name);
      final rule = _ClinicalRefs.timingRules.entries
          .firstWhere((e) => _fuzzyMatch(key, e.key),
              orElse: () => MapEntry(
                  '',
                  _TimingRule(
                    preferredTime: '',
                    note: '',
                    icon: Icons.schedule_rounded,
                  )));
      if (rule.key.isNotEmpty) {
        suggestions.add(TimingSuggestion(
          time: rule.value.preferredTime,
          medicationName: med.name,
          note: rule.value.note,
          icon: rule.value.icon,
          accentColor: _colorForTimingIcon(rule.value.icon),
        ));
      }
    }
    // Sort roughly by time-of-day keyword
    suggestions.sort((a, b) {
      final score = (String t) {
        final lt = t.toLowerCase();
        if (lt.contains('6:00 am')) return 0;
        if (lt.contains('7:00 am') || lt.contains('morning')) return 1;
        if (lt.contains('before breakfast')) return 2;
        if (lt.contains('with meals')) return 3;
        if (lt.contains('any time')) return 4;
        if (lt.contains('between meals')) return 5;
        if (lt.contains('afternoon')) return 6;
        if (lt.contains('9:00 pm') || lt.contains('evening')) return 7;
        if (lt.contains('bedtime')) return 8;
        return 4;
      };
      return score(a.time).compareTo(score(b.time));
    });
    return suggestions;
  }

  Color _colorForTimingIcon(IconData icon) {
    if (icon == Icons.wb_twilight_rounded) return _Jovi.gold;
    if (icon == Icons.wb_sunny_rounded) return _Jovi.gold;
    if (icon == Icons.nights_stay_rounded) return _Jovi.coralLight;
    if (icon == Icons.coffee_rounded) return _Jovi.coral;
    if (icon == Icons.restaurant_rounded) return _Jovi.mint;
    return _Jovi.coral;
  }

  Widget _buildTimingCard(TimingSuggestion s) {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              color: s.accentColor.withOpacity(0.18),
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: s.accentColor.withOpacity(0.4), width: 1),
            ),
            child: Icon(s.icon, color: s.accentColor, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        s.medicationName,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w700),
                      ),
                    ),
                    _glassPill(
                      tint: s.accentColor,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      child: Text(
                        s.time,
                        style: TextStyle(
                          color: s.accentColor,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  s.note,
                  style: const TextStyle(
                      color: Colors.white, fontSize: 12, height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// Finds pairs of meds that need spacing (e.g., levothyroxine + calcium)
  List<List<String>> _detectTimingConflicts() {
    final conflicts = <List<String>>[];
    final keys = _meds.map((m) => _normalizeKey(m.name)).toList();

    // Levothyroxine must be separated from many things
    final ltIdx = keys.indexWhere((k) => k.contains('levothyroxine'));
    if (ltIdx >= 0) {
      final separators = ['calcium', 'iron', 'omeprazole', 'pantoprazole'];
      for (int i = 0; i < keys.length; i++) {
        if (i == ltIdx) continue;
        if (separators.any((s) => keys[i].contains(s))) {
          conflicts.add([
            _meds[ltIdx].name,
            _meds[i].name,
            'Separate by at least 4 hours — ${_meds[i].name} reduces levothyroxine absorption.',
          ]);
        }
      }
    }

    // Ciprofloxacin separator
    final cipIdx = keys.indexWhere((k) => k.contains('ciprofloxacin'));
    if (cipIdx >= 0) {
      final separators = ['calcium', 'iron', 'antacid', 'magnesium'];
      for (int i = 0; i < keys.length; i++) {
        if (i == cipIdx) continue;
        if (separators.any((s) => keys[i].contains(s))) {
          conflicts.add([
            _meds[cipIdx].name,
            _meds[i].name,
            'Separate by at least 2 hours — chelation reduces ciprofloxacin absorption.',
          ]);
        }
      }
    }

    // Doxycycline separator
    final dxIdx = keys.indexWhere((k) => k.contains('doxycycline'));
    if (dxIdx >= 0) {
      final separators = ['calcium', 'iron', 'antacid'];
      for (int i = 0; i < keys.length; i++) {
        if (i == dxIdx) continue;
        if (separators.any((s) => keys[i].contains(s))) {
          conflicts.add([
            _meds[dxIdx].name,
            _meds[i].name,
            'Separate by 1-2 hours — chelation reduces doxycycline absorption.',
          ]);
        }
      }
    }

    return conflicts;
  }

  Widget _buildConflictCard(List<String> c) {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      tintColor: _Jovi.gold,
      tintOpacity: 0.08,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.warning_amber_rounded, color: _Jovi.gold, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${c[0]}  +  ${c[1]}',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                Text(
                  c[2],
                  style: const TextStyle(
                      color: Colors.white, fontSize: 12, height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMedsWithoutTimingSection() {
    final haveTimingKeys = _ClinicalRefs.timingRules.keys;
    final missing = _meds
        .where((m) =>
            !haveTimingKeys.any((k) => _fuzzyMatch(_normalizeKey(m.name), k)))
        .toList();
    if (missing.isEmpty) return const SizedBox.shrink();

    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline_rounded,
                  color: Colors.white.withOpacity(0.7), size: 14),
              const SizedBox(width: 6),
              const Text(
                'FLEXIBLE TIMING',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'These medications don\'t have strict timing — follow your prescriber\'s directions.',
            style:
                TextStyle(color: Colors.white.withOpacity(0.7), fontSize: 11.5),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: missing
                .map((m) => _glassPill(
                      tint: Colors.white,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 9, vertical: 4),
                      child: Text(
                        m.name,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.w600),
                      ),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SAFETY TAB — allergies, taper, missed dose, health profile
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildSafetyTab(ResponsiveConfig cfg) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 90),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildHealthProfileCard(),
          const SizedBox(height: 14),
          _buildAllergiesSection(),
          const SizedBox(height: 14),
          _buildTaperSection(),
          const SizedBox(height: 14),
          _buildMissedDoseSection(),
        ],
      ),
    );
  }

  // ─── Health Profile Card ─────────────────────────────────────────────────

  Widget _buildHealthProfileCard() {
    return _glassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _coralGradientIcon(Icons.person_outline_rounded, size: 16),
              const SizedBox(width: 8),
              const Text(
                'HEALTH PROFILE',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'These help us flag medications that may be risky for your situation.',
            style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 12,
                height: 1.4),
          ),
          const SizedBox(height: 14),
          _profileToggle(
            icon: Icons.pregnant_woman_rounded,
            label: 'Pregnant',
            value: _pregnancyState == _PregnancyState.pregnant ||
                _pregnancyState == _PregnancyState.both,
            onChanged: (v) => _updatePregnancyState(pregnant: v),
          ),
          const SizedBox(height: 8),
          _profileToggle(
            icon: Icons.child_care_rounded,
            label: 'Breastfeeding',
            value: _pregnancyState == _PregnancyState.breastfeeding ||
                _pregnancyState == _PregnancyState.both,
            onChanged: (v) => _updatePregnancyState(breastfeeding: v),
          ),
          const SizedBox(height: 8),
          _profileToggle(
            icon: Icons.local_bar_rounded,
            label: 'Uses alcohol',
            value: _drinksAlcohol,
            onChanged: (v) => _updateAlcohol(v),
          ),
          const SizedBox(height: 12),
          _profileDropdown(
            icon: Icons.water_drop_rounded,
            label: 'Kidney function',
            value: _renalStatus,
            onChanged: (v) => _updateRenalStatus(v),
          ),
          const SizedBox(height: 8),
          _profileDropdown(
            icon: Icons.monitor_heart_rounded,
            label: 'Liver function',
            value: _hepaticStatus,
            onChanged: (v) => _updateHepaticStatus(v),
          ),
        ],
      ),
    );
  }

  Widget _profileToggle({
    required IconData icon,
    required String label,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        onChanged(!value);
      },
      child: _glassCard(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        radius: 12,
        tintColor: value ? _Jovi.coral : null,
        tintOpacity: value ? 0.14 : 0.08,
        child: Row(
          children: [
            Icon(icon,
                color: value ? _Jovi.coral : Colors.white.withOpacity(0.75),
                size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 13,
                    fontWeight: value ? FontWeight.w700 : FontWeight.w500),
              ),
            ),
            _buildSwitch(value),
          ],
        ),
      ),
    );
  }

  Widget _buildSwitch(bool value) {
    return Container(
      width: 40,
      height: 22,
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: value ? _Jovi.coral : Colors.white.withOpacity(0.18),
        borderRadius: BorderRadius.circular(100),
      ),
      child: AnimatedAlign(
        duration: const Duration(milliseconds: 220),
        alignment: value ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          width: 18,
          height: 18,
          decoration: const BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
          ),
        ),
      ),
    );
  }

  Widget _profileDropdown({
    required IconData icon,
    required String label,
    required String? value,
    required ValueChanged<String?> onChanged,
  }) {
    return _glassCard(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      radius: 12,
      child: Row(
        children: [
          Icon(icon, color: Colors.white.withOpacity(0.75), size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w500),
            ),
          ),
          Theme(
            data: Theme.of(context).copyWith(canvasColor: _Jovi.navyMid),
            child: DropdownButton<String?>(
              value: value,
              hint: Text('Normal',
                  style: TextStyle(
                      color: Colors.white.withOpacity(0.55), fontSize: 12.5)),
              dropdownColor: _Jovi.navyMid,
              underline: const SizedBox.shrink(),
              iconEnabledColor: _Jovi.coral,
              style: const TextStyle(color: Colors.white, fontSize: 12.5),
              items: const [
                DropdownMenuItem(value: null, child: Text('Normal')),
                DropdownMenuItem(value: 'mild', child: Text('Mild')),
                DropdownMenuItem(value: 'moderate', child: Text('Moderate')),
                DropdownMenuItem(value: 'severe', child: Text('Severe')),
              ],
              onChanged: onChanged,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _updatePregnancyState(
      {bool? pregnant, bool? breastfeeding}) async {
    final isPregnant = pregnant ??
        (_pregnancyState == _PregnancyState.pregnant ||
            _pregnancyState == _PregnancyState.both);
    final isBreastfeeding = breastfeeding ??
        (_pregnancyState == _PregnancyState.breastfeeding ||
            _pregnancyState == _PregnancyState.both);

    setState(() {
      if (isPregnant && isBreastfeeding) {
        _pregnancyState = _PregnancyState.both;
      } else if (isPregnant) {
        _pregnancyState = _PregnancyState.pregnant;
      } else if (isBreastfeeding) {
        _pregnancyState = _PregnancyState.breastfeeding;
      } else {
        _pregnancyState = _PregnancyState.none;
      }
      _runSafetyAnalysis();
    });

    try {
      await _userRef.set({
        'isPregnant': isPregnant,
        'isBreastfeeding': isBreastfeeding,
      }, SetOptions(merge: true));
    } catch (_) {}
  }

  Future<void> _updateAlcohol(bool v) async {
    setState(() {
      _drinksAlcohol = v;
      _runSafetyAnalysis();
    });
    try {
      await _userRef.set({'drinksAlcohol': v}, SetOptions(merge: true));
    } catch (_) {}
  }

  Future<void> _updateRenalStatus(String? v) async {
    setState(() {
      _renalStatus = v;
      _runSafetyAnalysis();
    });
    try {
      await _userRef.set({'renalImpairment': v}, SetOptions(merge: true));
    } catch (_) {}
  }

  Future<void> _updateHepaticStatus(String? v) async {
    setState(() {
      _hepaticStatus = v;
      _runSafetyAnalysis();
    });
    try {
      await _userRef.set({'hepaticImpairment': v}, SetOptions(merge: true));
    } catch (_) {}
  }

  // ─── Allergies Section ───────────────────────────────────────────────────

  Widget _buildAllergiesSection() {
    return _glassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _coralGradientIcon(Icons.dangerous_outlined, size: 16),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'ALLERGIES',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.1),
                ),
              ),
              _Pressable(
                onTap: _addAllergy,
                child: _glassPill(
                  tint: _Jovi.coral,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.add_rounded, color: _Jovi.coral, size: 14),
                      const SizedBox(width: 4),
                      Text(
                        'Add',
                        style: TextStyle(
                            color: _Jovi.coral,
                            fontSize: 11,
                            fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (_allergies.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'No allergies recorded yet.',
                style: TextStyle(
                    color: Colors.white.withOpacity(0.6), fontSize: 12.5),
              ),
            )
          else
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: _allergies.map((a) => _buildAllergyChip(a)).toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildAllergyChip(String allergy) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(100),
        onTap: () => _confirmRemoveAllergy(allergy),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: _Jovi.errorRed.withOpacity(0.15),
            borderRadius: BorderRadius.circular(100),
            border:
                Border.all(color: _Jovi.errorRed.withOpacity(0.4), width: 1),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.dangerous_outlined, color: _Jovi.softRed, size: 13),
              const SizedBox(width: 6),
              Text(
                allergy,
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.w600),
              ),
              const SizedBox(width: 6),
              Icon(Icons.close_rounded,
                  color: _Jovi.softRed.withOpacity(0.7), size: 12),
            ],
          ),
        ),
      ),
    );
  }

  void _addAllergy() {
    final controller = TextEditingController();
    _showNavyDialog(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Add Allergy',
            style: TextStyle(
                color: Colors.white, fontSize: 17, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 14),
          _glassCard(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            radius: 12,
            child: TextField(
              controller: controller,
              autofocus: true,
              textCapitalization: TextCapitalization.words,
              textInputAction: TextInputAction.done,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              cursorColor: _Jovi.coral,
              decoration: InputDecoration(
                hintText: 'e.g. Penicillin, Sulfa, Peanuts',
                hintStyle: TextStyle(
                    color: Colors.white.withOpacity(0.5), fontSize: 13),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _secondaryButton(
                  label: 'Cancel',
                  onTap: () => Navigator.of(context).pop(),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _primaryButton(
                  label: 'Add',
                  onTap: () async {
                    final v = controller.text.trim();
                    if (v.isEmpty) return;
                    Navigator.of(context).pop();
                    setState(() {
                      _allergies.add(v);
                      _runSafetyAnalysis();
                    });
                    try {
                      await _userRef.set(
                          {'allergies': _allergies}, SetOptions(merge: true));
                      _showSnack('Added "$v"');
                    } catch (_) {
                      _showSnack('Saved locally only', isError: true);
                    }
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _confirmRemoveAllergy(String a) {
    _showNavyDialog(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Remove allergy?',
            style: TextStyle(
                color: Colors.white, fontSize: 16, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(
            'Remove "$a" from your allergy list?',
            style: TextStyle(
                color: Colors.white.withOpacity(0.85),
                fontSize: 13,
                height: 1.4),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _secondaryButton(
                  label: 'Cancel',
                  onTap: () => Navigator.of(context).pop(),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _primaryButton(
                  label: 'Remove',
                  onTap: () async {
                    Navigator.of(context).pop();
                    setState(() {
                      _allergies.remove(a);
                      _runSafetyAnalysis();
                    });
                    try {
                      await _userRef.set(
                          {'allergies': _allergies}, SetOptions(merge: true));
                      _showSnack('Removed "$a"');
                    } catch (_) {}
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ─── Taper Section ───────────────────────────────────────────────────────

  Widget _buildTaperSection() {
    final taperMeds = <MapEntry<UserMedication, _TaperInfo>>[];
    for (final med in _meds) {
      final key = _normalizeKey(med.name);
      final found = _ClinicalRefs.taperRequired.entries.firstWhere(
          (e) => _fuzzyMatch(key, e.key),
          orElse: () => const MapEntry('', _TaperInfo('', '')));
      if (found.key.isNotEmpty) {
        taperMeds.add(MapEntry(med, found.value));
      }
    }

    return _glassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _coralGradientIcon(Icons.trending_down_rounded, size: 16),
              const SizedBox(width: 8),
              const Expanded(
                child: Text(
                  'DO NOT STOP ABRUPTLY',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.1),
                ),
              ),
              if (taperMeds.isNotEmpty)
                _glassPill(
                  tint: _Jovi.coral,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  child: Text(
                    '${taperMeds.length}',
                    style: TextStyle(
                        color: _Jovi.coral,
                        fontSize: 11,
                        fontWeight: FontWeight.w700),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'These medications can cause serious withdrawal or rebound symptoms if stopped suddenly.',
            style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 12,
                height: 1.4),
          ),
          const SizedBox(height: 12),
          if (taperMeds.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'None of your medications require a taper.',
                style: TextStyle(
                    color: Colors.white.withOpacity(0.6), fontSize: 12.5),
              ),
            )
          else
            ...taperMeds.map((e) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildTaperCard(e.key, e.value),
                )),
        ],
      ),
    );
  }

  Widget _buildTaperCard(UserMedication med, _TaperInfo info) {
    return _glassCard(
      padding: const EdgeInsets.all(12),
      radius: 12,
      tintColor: _Jovi.gold,
      tintOpacity: 0.06,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.trending_down_rounded, color: _Jovi.gold, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  med.name,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700),
                ),
              ),
              _glassPill(
                tint: _Jovi.gold,
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                child: Text(
                  info.drugClass,
                  style: TextStyle(
                      color: _Jovi.gold,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            info.guidance,
            style:
                const TextStyle(color: Colors.white, fontSize: 12, height: 1.4),
          ),
        ],
      ),
    );
  }

  // ─── Missed Dose Section ─────────────────────────────────────────────────

  Widget _buildMissedDoseSection() {
    final guidance = <MapEntry<UserMedication, String>>[];
    for (final med in _meds) {
      final key = _normalizeKey(med.name);
      final found = _ClinicalRefs.missedDoseGuidance.entries.firstWhere(
          (e) => _fuzzyMatch(key, e.key),
          orElse: () => const MapEntry('', ''));
      if (found.value.isNotEmpty) {
        guidance.add(MapEntry(med, found.value));
      }
    }

    if (guidance.isEmpty) return const SizedBox.shrink();

    return _glassCard(
      padding: const EdgeInsets.all(16),
      radius: 18,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _coralGradientIcon(Icons.history_toggle_off_rounded, size: 16),
              const SizedBox(width: 8),
              const Text(
                'IF YOU MISS A DOSE',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ...guidance.map((e) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _buildMissedDoseCard(e.key, e.value),
              )),
        ],
      ),
    );
  }

  Widget _buildMissedDoseCard(UserMedication med, String guidance) {
    return _glassCard(
      padding: const EdgeInsets.all(12),
      radius: 12,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.history_toggle_off_rounded,
                  color: _Jovi.coral, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  med.name,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            guidance,
            style:
                const TextStyle(color: Colors.white, fontSize: 12, height: 1.4),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // SIDE EFFECTS TAB
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildSideEffectsTab(ResponsiveConfig cfg) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 90),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _glassCard(
            padding: const EdgeInsets.all(16),
            radius: 18,
            tintColor: _Jovi.coral,
            tintOpacity: 0.08,
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    gradient: _Jovi.coralGradient,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.report_problem_rounded,
                      color: Colors.white, size: 20),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Report Side Effects',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w700),
                      ),
                      SizedBox(height: 2),
                      Text(
                        'Track how medications affect you over time',
                        style: TextStyle(color: Colors.white70, fontSize: 11.5),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          _sectionHeader('Your Medications', icon: Icons.medication_rounded),
          if (_meds.isEmpty)
            _emptyState(
              icon: Icons.medication_outlined,
              title: 'No medications',
              subtitle: 'Add medications to report side effects.',
            )
          else
            ..._meds.map((m) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildMedReportRow(m),
                )),
          const SizedBox(height: 16),
          if (_sideEffects.isNotEmpty) ...[
            _sectionHeader(
              'Reported (${_sideEffects.length})',
              icon: Icons.history_rounded,
            ),
            ..._sideEffects.map((se) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildSideEffectCard(se),
                )),
          ],
        ],
      ),
    );
  }

  Widget _buildMedReportRow(UserMedication med) {
    // Count prior reports for this med
    final reportCount =
        _sideEffects.where((s) => s.medicationId == med.id).length;
    return _glassCard(
      padding: const EdgeInsets.all(12),
      radius: 14,
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: _Jovi.coral.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: _Jovi.coral.withOpacity(0.3), width: 1),
            ),
            child: Icon(Icons.medication_rounded, color: _Jovi.coral, size: 18),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  med.name,
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w700),
                ),
                if (med.dosage.isNotEmpty || med.strength.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(
                    '${med.dosage} ${med.strength}'.trim(),
                    style: TextStyle(
                        color: Colors.white.withOpacity(0.6), fontSize: 11.5),
                  ),
                ],
                if (reportCount > 0) ...[
                  const SizedBox(height: 4),
                  Text(
                    '$reportCount prior report${reportCount == 1 ? "" : "s"}',
                    style: TextStyle(
                        color: _Jovi.gold,
                        fontSize: 10.5,
                        fontWeight: FontWeight.w600),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 8),
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: () => _openSideEffectReport(med),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  gradient: _Jovi.coralGradient,
                  borderRadius: BorderRadius.circular(10),
                  boxShadow: [
                    BoxShadow(
                      color: _Jovi.coral.withOpacity(0.3),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ],
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.add_rounded, color: Colors.white, size: 14),
                    SizedBox(width: 4),
                    Text(
                      'Report',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w700),
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

  Widget _buildSideEffectCard(ReportedSideEffect se) {
    final severity = se.severity.toLowerCase();
    final color = severity == 'severe'
        ? _Jovi.errorRed
        : severity == 'moderate'
            ? _Jovi.gold
            : _Jovi.mint;
    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 14,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: color.withOpacity(0.4), width: 1),
                ),
                child:
                    Icon(Icons.report_problem_rounded, color: color, size: 18),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      se.medicationName,
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _formatDate(se.reportedAt),
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.55),
                          fontSize: 11,
                          fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: color.withOpacity(0.5), width: 1),
                ),
                child: Text(
                  severity.toUpperCase(),
                  style: TextStyle(
                      color: color,
                      fontSize: 9.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.8),
                ),
              ),
            ],
          ),
          if (se.symptoms.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: se.symptoms
                  .map((s) => Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(100),
                          border: Border.all(
                              color: Colors.white.withOpacity(0.14), width: 1),
                        ),
                        child: Text(
                          s,
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 10.5,
                              fontWeight: FontWeight.w600),
                        ),
                      ))
                  .toList(),
            ),
          ],
          if (se.description.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(
              se.description,
              style: const TextStyle(
                  color: Colors.white, fontSize: 12.5, height: 1.4),
            ),
          ],
        ],
      ),
    );
  }

  String _formatDate(DateTime d) {
    final now = DateTime.now();
    final diff = now.difference(d);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return '${d.month}/${d.day}/${d.year}';
  }

  // ─── Report Side Effect Bottom Sheet ─────────────────────────────────────

  static const List<String> _commonSymptoms = [
    'Nausea',
    'Headache',
    'Dizziness',
    'Fatigue',
    'Insomnia',
    'Dry mouth',
    'Constipation',
    'Diarrhea',
    'Rash',
    'Anxiety',
    'Weight gain',
    'Weight loss',
    'Muscle pain',
    'Joint pain',
    'Brain fog',
  ];

  void _openSideEffectReport(UserMedication med) {
    String severity = 'mild';
    final selectedSymptoms = <String>{};
    final descriptionCtrl = TextEditingController();

    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.5),
      isScrollControlled: true,
      builder: (sheetContext) {
        return StatefulBuilder(
          builder: (sheetContext, setSheet) {
            return Padding(
              padding: EdgeInsets.only(
                  bottom: MediaQuery.of(sheetContext).viewInsets.bottom),
              child: FractionallySizedBox(
              heightFactor: 0.88,
              child: ClipRRect(
                borderRadius:
                    const BorderRadius.vertical(top: Radius.circular(26)),
                child: BackdropFilter(
                  filter: ui.ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: _Jovi.navyGradient,
                      borderRadius:
                          const BorderRadius.vertical(top: Radius.circular(26)),
                      border: Border(
                        top: BorderSide(
                            color: Colors.white.withOpacity(0.12), width: 1),
                      ),
                    ),
                    child: Column(
                      children: [
                        _sheetHandle(),
                        Padding(
                          padding: const EdgeInsets.fromLTRB(20, 4, 20, 14),
                          child: Row(
                            children: [
                              Container(
                                width: 44,
                                height: 44,
                                decoration: BoxDecoration(
                                  gradient: _Jovi.coralGradient,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: const Icon(Icons.report_problem_rounded,
                                    color: Colors.white, size: 22),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'Report Side Effect',
                                      style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 17,
                                          fontWeight: FontWeight.w800),
                                    ),
                                    Text(
                                      med.name,
                                      style: TextStyle(
                                          color: _Jovi.coral,
                                          fontSize: 12.5,
                                          fontWeight: FontWeight.w600),
                                    ),
                                  ],
                                ),
                              ),
                              _Pressable(
                                onTap: () => Navigator.of(sheetContext).pop(),
                                child: Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Icon(Icons.close_rounded,
                                      color: Colors.white, size: 18),
                                ),
                              ),
                            ],
                          ),
                        ),
                        Expanded(
                          child: SingleChildScrollView(
                            physics: const BouncingScrollPhysics(),
                            padding: const EdgeInsets.fromLTRB(20, 0, 20, 16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                _sectionHeader('Severity',
                                    icon: Icons.speed_rounded),
                                Row(
                                  children: [
                                    Expanded(
                                        child: _severityChoice(
                                            'mild',
                                            'Mild',
                                            _Jovi.mint,
                                            severity,
                                            (v) =>
                                                setSheet(() => severity = v))),
                                    const SizedBox(width: 8),
                                    Expanded(
                                        child: _severityChoice(
                                            'moderate',
                                            'Moderate',
                                            _Jovi.gold,
                                            severity,
                                            (v) =>
                                                setSheet(() => severity = v))),
                                    const SizedBox(width: 8),
                                    Expanded(
                                        child: _severityChoice(
                                            'severe',
                                            'Severe',
                                            _Jovi.errorRed,
                                            severity,
                                            (v) =>
                                                setSheet(() => severity = v))),
                                  ],
                                ),
                                const SizedBox(height: 14),
                                _sectionHeader('Symptoms',
                                    icon: Icons.checklist_rounded),
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: _commonSymptoms.map((sym) {
                                    final sel = selectedSymptoms.contains(sym);
                                    return _Pressable(
                                      onTap: () => setSheet(() {
                                        if (sel) {
                                          selectedSymptoms.remove(sym);
                                        } else {
                                          selectedSymptoms.add(sym);
                                        }
                                        HapticFeedback.selectionClick();
                                      }),
                                      child: AnimatedContainer(
                                        duration:
                                            const Duration(milliseconds: 160),
                                        padding: const EdgeInsets.symmetric(
                                            horizontal: 12, vertical: 7),
                                        decoration: BoxDecoration(
                                          gradient:
                                              sel ? _Jovi.coralGradient : null,
                                          color: sel
                                              ? null
                                              : Colors.white.withOpacity(0.08),
                                          borderRadius:
                                              BorderRadius.circular(100),
                                          border: Border.all(
                                            color: sel
                                                ? Colors.transparent
                                                : Colors.white
                                                    .withOpacity(0.18),
                                            width: 1,
                                          ),
                                        ),
                                        child: Text(
                                          sym,
                                          style: TextStyle(
                                            color: Colors.white,
                                            fontSize: 12,
                                            fontWeight: sel
                                                ? FontWeight.w700
                                                : FontWeight.w500,
                                          ),
                                        ),
                                      ),
                                    );
                                  }).toList(),
                                ),
                                const SizedBox(height: 16),
                                _sectionHeader('Description',
                                    icon: Icons.edit_note_rounded),
                                _glassCard(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 12, vertical: 4),
                                  radius: 14,
                                  child: TextField(
                                    controller: descriptionCtrl,
                                    maxLines: 4,
                                    textCapitalization:
                                        TextCapitalization.sentences,
                                    style: const TextStyle(
                                        color: Colors.white, fontSize: 13.5),
                                    cursorColor: _Jovi.coral,
                                    decoration: InputDecoration(
                                      hintText:
                                          'What happened? When did it start? How is it affecting you?',
                                      hintStyle: TextStyle(
                                          color: Colors.white.withOpacity(0.45),
                                          fontSize: 12.5,
                                          height: 1.4),
                                      border: InputBorder.none,
                                      contentPadding:
                                          const EdgeInsets.symmetric(
                                              vertical: 10),
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 20),
                              ],
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
                          decoration: BoxDecoration(
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
                                child: _secondaryButton(
                                  label: 'Cancel',
                                  onTap: () => Navigator.of(sheetContext).pop(),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                flex: 2,
                                child: _primaryButton(
                                  label: 'Submit Report',
                                  icon: Icons.check_rounded,
                                  onTap: () async {
                                    Navigator.of(sheetContext).pop();
                                    await _submitSideEffect(
                                      medId: med.id,
                                      medName: med.name,
                                      severity: severity,
                                      description: descriptionCtrl.text.trim(),
                                      symptoms: selectedSymptoms.toList(),
                                    );
                                  },
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
            ));
          },
        );
      },
    );
  }

  Widget _severityChoice(String value, String label, Color color,
      String current, ValueChanged<String> onTap) {
    final sel = current == value;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap(value);
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: sel ? color.withOpacity(0.2) : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: sel ? color : Colors.white.withOpacity(0.14),
            width: sel ? 1.5 : 1,
          ),
        ),
        child: Column(
          children: [
            Icon(
              value == 'mild'
                  ? Icons.sentiment_satisfied_rounded
                  : value == 'moderate'
                      ? Icons.sentiment_neutral_rounded
                      : Icons.sentiment_very_dissatisfied_rounded,
              color: sel ? color : Colors.white.withOpacity(0.7),
              size: 22,
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submitSideEffect({
    required String medId,
    required String medName,
    required String severity,
    required String description,
    required List<String> symptoms,
  }) async {
    try {
      await _sideEffectsRef.add({
        'medicationId': medId,
        'medicationName': medName,
        'severity': severity,
        'description': description,
        'symptoms': symptoms,
        'reportedAt': Timestamp.now(),
      });
      HapticFeedback.lightImpact();
      _showSnack('Side effect reported for $medName');
      await _loadData();
    } catch (_) {
      _showSnack('Unable to save report', isError: true);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // EDUCATION TAB
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildEducationTab(ResponsiveConfig cfg) {
    final filtered = _searchQuery.isEmpty
        ? _meds
        : _meds
            .where((m) =>
                m.name.toLowerCase().contains(_searchQuery.toLowerCase()))
            .toList();

    return Column(
      children: [
        Padding(
          padding: EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, 10),
          child: _glassCard(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
            radius: 14,
            child: Row(
              children: [
                Icon(Icons.search_rounded,
                    color: Colors.white.withOpacity(0.7), size: 18),
                const SizedBox(width: 10),
                Expanded(
                  child: TextField(
                    controller: _searchController,
                    style: const TextStyle(color: Colors.white, fontSize: 14),
                    cursorColor: _Jovi.coral,
                    autocorrect: false,
                    textInputAction: TextInputAction.search,
                    onChanged: (v) => setState(() => _searchQuery = v),
                    decoration: InputDecoration(
                      hintText: 'Search medications…',
                      hintStyle: TextStyle(
                          color: Colors.white.withOpacity(0.5), fontSize: 13.5),
                      border: InputBorder.none,
                      contentPadding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                if (_searchQuery.isNotEmpty)
                  _Pressable(
                    onTap: () {
                      _searchController.clear();
                      setState(() => _searchQuery = '');
                    },
                    child: Icon(Icons.close_rounded,
                        color: Colors.white.withOpacity(0.6), size: 18),
                  ),
              ],
            ),
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            physics: const BouncingScrollPhysics(),
            padding: EdgeInsets.fromLTRB(
                cfg.paddingH, 0, cfg.paddingH, cfg.paddingV + 90),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _sectionHeader('Your Medications',
                    icon: Icons.medication_rounded),
                if (filtered.isEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    child: Text(
                      _searchQuery.isEmpty
                          ? 'No medications to show.'
                          : 'No medications match your search.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.6), fontSize: 13),
                    ),
                  )
                else
                  ...filtered.map((m) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _buildEducationMedRow(m),
                      )),
                const SizedBox(height: 18),
                _sectionHeader('Resources', icon: Icons.auto_stories_rounded),
                _buildResourceRow(
                  icon: Icons.merge_type_rounded,
                  title: 'Understanding Drug Interactions',
                  subtitle:
                      'How medications can amplify, block, or alter each other',
                  onTap: () => _openResourceSheet(
                      'Understanding Drug Interactions', _resourceInteractions),
                ),
                const SizedBox(height: 8),
                _buildResourceRow(
                  icon: Icons.restaurant_rounded,
                  title: 'Food & Drug Interactions',
                  subtitle: 'Foods that affect how medications work',
                  onTap: () => _openResourceSheet(
                      'Food & Drug Interactions', _resourceFood),
                ),
                const SizedBox(height: 8),
                _buildResourceRow(
                  icon: Icons.healing_rounded,
                  title: 'Managing Side Effects',
                  subtitle: 'What to track and when to call your provider',
                  onTap: () => _openResourceSheet(
                      'Managing Side Effects', _resourceSideEffects),
                ),
                const SizedBox(height: 8),
                _buildResourceRow(
                  icon: Icons.security_rounded,
                  title: 'Medication Safety',
                  subtitle: 'Best practices for storage, timing, and adherence',
                  onTap: () =>
                      _openResourceSheet('Medication Safety', _resourceSafety),
                ),
                const SizedBox(height: 8),
                _buildResourceRow(
                  icon: Icons.local_bar_rounded,
                  title: 'Alcohol & Your Medications',
                  subtitle: 'When alcohol is a real risk, not just a footnote',
                  onTap: () => _openResourceSheet(
                      'Alcohol & Your Medications', _resourceAlcohol),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildEducationMedRow(UserMedication med) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openMedEducation(med),
        child: _glassCard(
          padding: const EdgeInsets.all(12),
          radius: 14,
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: _Jovi.coral.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border:
                      Border.all(color: _Jovi.coral.withOpacity(0.3), width: 1),
                ),
                child: Icon(Icons.medication_rounded,
                    color: _Jovi.coral, size: 18),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      med.name,
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700),
                    ),
                    if (med.dosage.isNotEmpty || med.strength.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        '${med.dosage} ${med.strength}'.trim(),
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 11.5),
                      ),
                    ],
                  ],
                ),
              ),
              Icon(Icons.arrow_forward_ios_rounded,
                  color: Colors.white.withOpacity(0.4), size: 14),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResourceRow({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: _glassCard(
          padding: const EdgeInsets.all(12),
          radius: 14,
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      _Jovi.coral.withOpacity(0.25),
                      _Jovi.coralLight.withOpacity(0.15),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(10),
                  border:
                      Border.all(color: _Jovi.coral.withOpacity(0.3), width: 1),
                ),
                child: Icon(icon, color: _Jovi.coralLight, size: 18),
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
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.6),
                          fontSize: 11.5,
                          height: 1.35),
                    ),
                  ],
                ),
              ),
              Icon(Icons.arrow_forward_ios_rounded,
                  color: Colors.white.withOpacity(0.4), size: 14),
            ],
          ),
        ),
      ),
    );
  }

  // ─── Medication Education Sheet (fetches from FDA) ───────────────────────

  void _openMedEducation(UserMedication med) {
    _showNavyBottomSheet(
      heightFactor: 0.86,
      child: _MedEducationSheet(
        med: med,
        onFetch: _fetchFDAData,
        primaryButtonBuilder: (label, onTap) =>
            _primaryButton(label: label, onTap: onTap),
        secondaryButtonBuilder: (label, onTap) =>
            _secondaryButton(label: label, onTap: onTap),
        glassCardBuilder: (child, {tint}) => _glassCard(
          padding: const EdgeInsets.all(14),
          radius: 14,
          tintColor: tint,
          tintOpacity: tint != null ? 0.08 : 0.1,
          child: child,
        ),
        sheetHandle: _sheetHandle,
        sectionHeader: (label, icon) => _sectionHeader(label, icon: icon),
      ),
    );
  }

  // ─── Resource Sheets (static educational content) ────────────────────────

  static const List<Map<String, String>> _resourceInteractions = [
    {
      'title': 'What is a drug interaction?',
      'body':
          'When one medication changes how another works — making it stronger, weaker, or causing unintended effects. Interactions can happen between two prescription drugs, or with foods, supplements, alcohol, or over-the-counter products.',
    },
    {
      'title': 'The most common mechanisms',
      'body':
          'Liver enzyme (CYP) competition is the biggest cause — one drug slows down another\'s breakdown, raising its level. Protein binding displacement, pH changes, absorption blockage (chelation), and additive organ effects (bleeding, sedation, kidney) are the other big families.',
    },
    {
      'title': 'What actually matters day-to-day',
      'body':
          'Most "interactions" in databases are minor. What you want to catch: major CYP inhibitors (azole antifungals, macrolide antibiotics, some SSRIs), anticoagulants + NSAIDs, opioids + benzodiazepines, serotonergic combinations, and QT-prolonging combinations.',
    },
    {
      'title': 'When to call a pharmacist',
      'body':
          'Any time you start a new medication, before any OTC purchase, before flying with new meds, when refills arrive looking different, and whenever you add a supplement. Pharmacists are free consultations.',
    },
  ];

  static const List<Map<String, String>> _resourceFood = [
    {
      'title': 'Grapefruit — the classic',
      'body':
          'Grapefruit and grapefruit juice inhibit CYP3A4 in the gut for up to 72 hours. That affects statins (especially simvastatin), some calcium channel blockers (felodipine, nifedipine), amiodarone, tacrolimus, cyclosporine, and many others. Even one glass can matter.',
    },
    {
      'title': 'Calcium, iron, magnesium',
      'body':
          'These bind to certain drugs in the gut and block absorption. Classic offenders: levothyroxine, fluoroquinolones (ciprofloxacin, levofloxacin), tetracyclines (doxycycline), bisphosphonates (alendronate). Separate by at least 2–4 hours.',
    },
    {
      'title': 'Vitamin K + warfarin',
      'body':
          'Large amounts of vitamin K (kale, spinach, collard greens, brussels sprouts) lower the INR and reduce warfarin effectiveness. The goal is consistency, not avoidance — eat similar amounts day to day.',
    },
    {
      'title': 'Tyramine + MAOIs',
      'body':
          'Tyramine-rich foods (aged cheese, cured meats, draft beer, fermented soy) can cause hypertensive crisis with MAOIs and linezolid. This is one of the few interactions that\'s genuinely dangerous and worth strict dietary restriction.',
    },
  ];

  static const List<Map<String, String>> _resourceSideEffects = [
    {
      'title': 'What to track',
      'body':
          'When symptoms started (relative to starting the med), severity, whether they\'re getting worse or better over time, and whether they happen in clusters. Patterns matter more than individual events.',
    },
    {
      'title': 'Red flag symptoms — seek care',
      'body':
          'Any trouble breathing, tongue/face swelling, chest pain, severe rash (especially with blisters), yellowing of skin or eyes, dark urine, severe abdominal pain, fainting, confusion, or suicidal thoughts. These are emergency-level.',
    },
    {
      'title': 'Common but manageable',
      'body':
          'Nausea, headache, dizziness, and fatigue often improve after 1–2 weeks as your body adjusts. Dry mouth, constipation, and mild insomnia can often be managed with timing changes, food pairing, hydration, or small tweaks that your pharmacist can suggest.',
    },
    {
      'title': 'When to call before stopping',
      'body':
          'Always, for SSRIs, SNRIs, benzodiazepines, beta-blockers, gabapentin, corticosteroids, and opioids. Abrupt stops can be dangerous. If side effects are severe, call first — don\'t just stop.',
    },
  ];

  static const List<Map<String, String>> _resourceSafety = [
    {
      'title': 'Store medications safely',
      'body':
          'Room temperature, away from bathroom humidity and direct sunlight. Keep original containers with labels. Out of reach of children and pets. Refrigerate only what the label tells you to.',
    },
    {
      'title': 'Dispose responsibly',
      'body':
          'Never flush (unless the FDA flush list says so — mostly controlled substances). Use pharmacy take-back programs, DEA take-back days, or mail-back envelopes. For unavoidable trash disposal: mix with coffee grounds or dirt in a sealed bag.',
    },
    {
      'title': 'Stick with one pharmacy',
      'body':
          'Using a single pharmacy lets the pharmacist see your full medication list and catch interactions your prescribers might miss. It\'s the single highest-leverage safety behavior you can adopt.',
    },
    {
      'title': 'The "Brown Bag" check',
      'body':
          'Once a year, bring ALL your medications (prescription, OTC, supplements, old bottles) to your pharmacist in a bag. Ask them to review. You\'ll almost always find duplicates, expired meds, or interactions nobody caught.',
    },
  ];

  static const List<Map<String, String>> _resourceAlcohol = [
    {
      'title': 'Why this deserves its own section',
      'body':
          'Alcohol is the most common "interaction" people have and the most frequently missed. It\'s not just about being tipsy — alcohol affects liver metabolism, kidney function, bleeding risk, and respiratory drive.',
    },
    {
      'title': 'The truly dangerous combinations',
      'body':
          'Alcohol + opioids: fatal respiratory depression risk. Alcohol + benzodiazepines: severe CNS depression. Alcohol + acetaminophen (chronic): severe liver toxicity. Alcohol + metronidazole: disulfiram-like reaction. Alcohol + warfarin: unpredictable INR.',
    },
    {
      'title': 'Things to know',
      'body':
          'Alcohol counts even if you "only have a glass of wine with dinner" — regular moderate use with the wrong medication can still be harmful. Cough syrups, mouthwashes, and some liquid medications also contain alcohol.',
    },
    {
      'title': 'How to have an honest conversation',
      'body':
          'Tell your prescriber and pharmacist your actual drinking pattern — not what you think they want to hear. They need accurate information to dose safely, and nobody is going to lecture you.',
    },
  ];

  void _openResourceSheet(String title, List<Map<String, String>> content) {
    _showNavyBottomSheet(
      heightFactor: 0.78,
      child: Column(
        children: [
          _sheetHandle(),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 14),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    gradient: _Jovi.coralGradient,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.auto_stories_rounded,
                      color: Colors.white, size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w800),
                  ),
                ),
                _Pressable(
                  onTap: () => Navigator.of(context).pop(),
                  child: Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.close_rounded,
                        color: Colors.white, size: 18),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (final item in content) ...[
                    _glassCard(
                      padding: const EdgeInsets.all(14),
                      radius: 14,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item['title'] ?? '',
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            item['body'] ?? '',
                            style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12.5,
                                height: 1.5),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MAIN BUILD
  // ═══════════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light.copyWith(
        statusBarColor: Colors.transparent,
        systemNavigationBarColor: _Jovi.navyDark,
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final cfg = _config(constraints);
          return Container(
            width: widget.width ?? constraints.maxWidth,
            height: widget.height ?? constraints.maxHeight,
            decoration: BoxDecoration(gradient: _Jovi.navyGradient),
            child: Stack(
              children: [
                // Ambient coral haze top-left
                Positioned(
                  top: -80,
                  left: -60,
                  child: Container(
                    width: 280,
                    height: 280,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          _Jovi.coral.withOpacity(0.22),
                          _Jovi.coral.withOpacity(0.0),
                        ],
                      ),
                    ),
                  ),
                ),
                // Ambient mint haze bottom-right
                Positioned(
                  bottom: -100,
                  right: -80,
                  child: Container(
                    width: 300,
                    height: 300,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          _Jovi.mint.withOpacity(0.14),
                          _Jovi.mint.withOpacity(0.0),
                        ],
                      ),
                    ),
                  ),
                ),
                SafeArea(
                  child: FadeTransition(
                    opacity: _fadeAnimation,
                    child: Column(
                      children: [
                        _buildTopBar(cfg),
                        _buildTabBar(cfg),
                        Expanded(
                          child: _isLoading
                              ? _buildLoadingState()
                              : AnimatedSwitcher(
                                  duration: (MediaQuery.maybeOf(context)
                                              ?.disableAnimations ??
                                          false)
                                      ? Duration.zero
                                      : _Motion.select,
                                  switchInCurve: _Motion.settle,
                                  switchOutCurve: Curves.easeIn,
                                  transitionBuilder: (child, anim) =>
                                      FadeTransition(
                                    opacity: anim,
                                    child: SlideTransition(
                                      position: Tween<Offset>(
                                        begin: const Offset(0, 0.03),
                                        end: Offset.zero,
                                      ).animate(anim),
                                      child: child,
                                    ),
                                  ),
                                  child: KeyedSubtree(
                                    key: ValueKey(_tab),
                                    child: _buildCurrentTab(cfg),
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
        },
      ),
    );
  }

  Widget _buildLoadingState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 42,
            height: 42,
            child: CircularProgressIndicator(
              strokeWidth: 3,
              valueColor: AlwaysStoppedAnimation(_Jovi.coral),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            'Running safety checks…',
            style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 13,
                fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }

  Widget _buildTopBar(ResponsiveConfig cfg) {
    return Padding(
      padding: EdgeInsets.fromLTRB(cfg.paddingH, 12, cfg.paddingH, 6),
      child: Row(
        children: [
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () {
                HapticFeedback.lightImpact();
                Navigator.of(context).maybePop();
              },
              child: _glassCard(
                padding: const EdgeInsets.all(10),
                radius: 12,
                child: const Icon(Icons.arrow_back_rounded,
                    color: Colors.white, size: 20),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'DRUG SAFETY CHECK',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 11,
                    letterSpacing: 1.6,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _meds.isEmpty
                      ? 'Add medications to get started'
                      : '${_meds.length} medication${_meds.length == 1 ? "" : "s"} monitored',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.65),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () {
                HapticFeedback.lightImpact();
                _loadData();
              },
              child: _glassCard(
                padding: const EdgeInsets.all(10),
                radius: 12,
                child: const Icon(Icons.refresh_rounded,
                    color: Colors.white, size: 20),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabBar(ResponsiveConfig cfg) {
    return Padding(
      padding: EdgeInsets.fromLTRB(cfg.paddingH - 4, 8, cfg.paddingH - 4, 6),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        physics: const BouncingScrollPhysics(),
        child: Row(
          children: [
            _tabPill(_Tab.interactions, 'Interactions',
                Icons.health_and_safety_rounded),
            _tabPill(_Tab.schedule, 'Schedule', Icons.schedule_rounded),
            _tabPill(_Tab.safety, 'Safety', Icons.shield_rounded),
            _tabPill(
                _Tab.sideEffects, 'Side Effects', Icons.report_problem_rounded),
            _tabPill(_Tab.education, 'Education', Icons.auto_stories_rounded),
          ],
        ),
      ),
    );
  }

  Widget _tabPill(_Tab tab, String label, IconData icon) {
    final sel = _tab == tab;
    // Count badges per tab
    int? badge;
    if (tab == _Tab.interactions && _findings.isNotEmpty) {
      badge = _findings
          .where((f) =>
              f.severity == InteractionSeverity.major ||
              f.severity == InteractionSeverity.contraindicated)
          .length;
      if (badge == 0) badge = null;
    }

    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _tab = tab);
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        constraints: const BoxConstraints(minHeight: 40),
        decoration: BoxDecoration(
          gradient: sel ? _Jovi.coralGradient : null,
          color: sel ? null : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(100),
          border: Border.all(
            color: sel ? Colors.transparent : Colors.white.withOpacity(0.12),
            width: 1,
          ),
          boxShadow: sel
              ? [
                  BoxShadow(
                    color: _Jovi.coral.withOpacity(0.38),
                    blurRadius: 14,
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: Row(
          children: [
            Icon(icon,
                color: sel ? Colors.white : Colors.white.withOpacity(0.75),
                size: 14),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: Colors.white,
                fontSize: 12.5,
                fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
            if (badge != null) ...[
              const SizedBox(width: 6),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                decoration: BoxDecoration(
                  color: sel ? Colors.white : _Jovi.errorRed,
                  borderRadius: BorderRadius.circular(100),
                ),
                child: Text(
                  '$badge',
                  style: TextStyle(
                    color: sel ? _Jovi.coralDark : Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCurrentTab(ResponsiveConfig cfg) {
    switch (_tab) {
      case _Tab.interactions:
        return _buildInteractionsTab(cfg);
      case _Tab.schedule:
        return _buildScheduleTab(cfg);
      case _Tab.safety:
        return _buildSafetyTab(cfg);
      case _Tab.sideEffects:
        return _buildSideEffectsTab(cfg);
      case _Tab.education:
        return _buildEducationTab(cfg);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// MED EDUCATION SHEET (separate stateful widget — fetches FDA data async)
// ═══════════════════════════════════════════════════════════════════════════

class _MedEducationSheet extends StatefulWidget {
  final UserMedication med;
  final Future<Map<String, dynamic>?> Function(String) onFetch;
  final Widget Function(String, VoidCallback) primaryButtonBuilder;
  final Widget Function(String, VoidCallback) secondaryButtonBuilder;
  final Widget Function(Widget, {Color? tint}) glassCardBuilder;
  final Widget Function() sheetHandle;
  final Widget Function(String, IconData) sectionHeader;

  const _MedEducationSheet({
    required this.med,
    required this.onFetch,
    required this.primaryButtonBuilder,
    required this.secondaryButtonBuilder,
    required this.glassCardBuilder,
    required this.sheetHandle,
    required this.sectionHeader,
  });

  @override
  State<_MedEducationSheet> createState() => _MedEducationSheetState();
}

class _MedEducationSheetState extends State<_MedEducationSheet> {
  Map<String, dynamic>? _fdaData;
  bool _loading = true;
  bool _error = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await widget.onFetch(widget.med.name);
      if (!mounted) return;
      setState(() {
        _fdaData = data;
        _loading = false;
        _error = data == null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = true;
      });
    }
  }

  String? _extract(String field) {
    if (_fdaData == null) return null;
    final v = _fdaData![field];
    if (v is List && v.isNotEmpty) {
      var s = v.first.toString();
      // Clean excessive whitespace
      s = s.replaceAll(RegExp(r'\s+'), ' ').trim();
      // Trim very long fields
      if (s.length > 800) s = '${s.substring(0, 800)}…';
      return s;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        widget.sheetHandle(),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 14),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  gradient: _Jovi.coralGradient,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: _Jovi.coral.withOpacity(0.35),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: const Icon(Icons.medication_rounded,
                    color: Colors.white, size: 24),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.med.name,
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w800),
                    ),
                    if (widget.med.dosage.isNotEmpty ||
                        widget.med.strength.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        '${widget.med.dosage} ${widget.med.strength}'.trim(),
                        style: TextStyle(
                            color: _Jovi.coral,
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600),
                      ),
                    ],
                  ],
                ),
              ),
              _Pressable(
                onTap: () => Navigator.of(context).pop(),
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.close_rounded,
                      color: Colors.white, size: 18),
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: _loading
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 36,
                        height: 36,
                        child: CircularProgressIndicator(
                          strokeWidth: 3,
                          valueColor: AlwaysStoppedAnimation(_Jovi.coral),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Looking up ${widget.med.name}…',
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.7),
                            fontSize: 12.5),
                      ),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (_error || _fdaData == null)
                        widget.glassCardBuilder(
                          const Column(
                            children: [
                              Icon(Icons.cloud_off_rounded,
                                  color: Colors.white70, size: 28),
                              SizedBox(height: 10),
                              Text(
                                'Couldn\'t reach FDA database',
                                style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 13,
                                    fontWeight: FontWeight.w700),
                              ),
                              SizedBox(height: 6),
                              Text(
                                'This medication may not be in the FDA label database, or the service is temporarily unavailable. Ask your pharmacist for a printed medication guide.',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                    color: Colors.white70,
                                    fontSize: 11.5,
                                    height: 1.4),
                              ),
                            ],
                          ),
                        )
                      else ...[
                        _buildEducationSection(
                          'Indications & Uses',
                          Icons.task_alt_rounded,
                          _extract('indications_and_usage'),
                        ),
                        _buildEducationSection(
                          'How to Take',
                          Icons.access_time_rounded,
                          _extract('dosage_and_administration'),
                        ),
                        _buildEducationSection(
                          'Warnings',
                          Icons.warning_amber_rounded,
                          _extract('warnings'),
                          tint: _Jovi.gold,
                        ),
                        _buildEducationSection(
                          'Do Not Take If',
                          Icons.dangerous_outlined,
                          _extract('contraindications'),
                          tint: _Jovi.errorRed,
                        ),
                        _buildEducationSection(
                          'Possible Side Effects',
                          Icons.report_problem_rounded,
                          _extract('adverse_reactions'),
                        ),
                        _buildEducationSection(
                          'Drug Interactions',
                          Icons.merge_type_rounded,
                          _extract('drug_interactions'),
                        ),
                        _buildEducationSection(
                          'Storage',
                          Icons.inventory_2_rounded,
                          _extract('storage_and_handling') ??
                              _extract('how_supplied'),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Source: FDA drug label database (openFDA). This is not medical advice — always consult your prescriber or pharmacist.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                            fontSize: 10.5,
                            fontStyle: FontStyle.italic,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
        ),
      ],
    );
  }

  Widget _buildEducationSection(String title, IconData icon, String? content,
      {Color? tint}) {
    if (content == null || content.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: widget.glassCardBuilder(
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: tint ?? _Jovi.coral, size: 16),
                const SizedBox(width: 8),
                Text(
                  title.toUpperCase(),
                  style: TextStyle(
                    color: tint ?? Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              content,
              style: const TextStyle(
                  color: Colors.white, fontSize: 12.5, height: 1.5),
            ),
          ],
        ),
        tint: tint,
      ),
    );
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// INTERACTION HEAT MAP PAINTER
// Draws meds as nodes in a circle; lines between pairs that have findings.
// Line color = severity; line weight = severity intensity.
// ═══════════════════════════════════════════════════════════════════════════

class _InteractionMapPainter extends CustomPainter {
  final List<String> meds;
  final List<SafetyFinding> findings;
  final Color coral;
  final Color coralLight;
  final Color Function(InteractionSeverity) severityColor;
  final Color textColor;

  _InteractionMapPainter({
    required this.meds,
    required this.findings,
    required this.coral,
    required this.coralLight,
    required this.severityColor,
    required this.textColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (meds.isEmpty) return;

    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2 - 38;
    final n = meds.length;

    // Calculate node positions
    final positions = <int, Offset>{};
    for (int i = 0; i < n; i++) {
      // Start at top, go clockwise
      final angle = -math.pi / 2 + (2 * math.pi * i) / n;
      positions[i] = Offset(
        center.dx + radius * math.cos(angle),
        center.dy + radius * math.sin(angle),
      );
    }

    // Draw connection lines for findings
    for (final f in findings) {
      if (f.affectedMeds.length < 2) continue;
      final idx1 = meds.indexWhere(
          (m) => m.toLowerCase() == f.affectedMeds[0].toLowerCase());
      final idx2 = meds.indexWhere(
          (m) => m.toLowerCase() == f.affectedMeds[1].toLowerCase());
      if (idx1 < 0 || idx2 < 0) continue;

      final color = severityColor(f.severity);
      final double thickness = f.severity == InteractionSeverity.contraindicated
          ? 3.0
          : f.severity == InteractionSeverity.major
              ? 2.4
              : f.severity == InteractionSeverity.moderate
                  ? 1.8
                  : 1.2;

      // Glow
      canvas.drawLine(
        positions[idx1]!,
        positions[idx2]!,
        Paint()
          ..color = color.withOpacity(0.28)
          ..strokeWidth = thickness + 3
          ..strokeCap = StrokeCap.round,
      );
      // Main line
      canvas.drawLine(
        positions[idx1]!,
        positions[idx2]!,
        Paint()
          ..color = color.withOpacity(0.92)
          ..strokeWidth = thickness
          ..strokeCap = StrokeCap.round,
      );
    }

    // Draw connecting "mesh" at low opacity for all meds (context)
    if (findings.isEmpty && n > 1) {
      for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
          canvas.drawLine(
            positions[i]!,
            positions[j]!,
            Paint()
              ..color = Colors.white.withOpacity(0.08)
              ..strokeWidth = 0.6,
          );
        }
      }
    }

    // Draw nodes
    for (int i = 0; i < n; i++) {
      final pos = positions[i]!;

      // Determine if this med has any findings
      final hasFinding = findings.any((f) => f.affectedMeds
          .any((am) => am.toLowerCase() == meds[i].toLowerCase()));

      // Outer glow
      canvas.drawCircle(
        pos,
        13,
        Paint()
          ..color = (hasFinding ? coral : coralLight).withOpacity(0.18)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
      );

      // Node circle
      final nodePaint = Paint()
        ..shader = ui.Gradient.linear(
          Offset(pos.dx - 9, pos.dy - 9),
          Offset(pos.dx + 9, pos.dy + 9),
          hasFinding
              ? [coral, Color.lerp(coral, Colors.black, 0.3)!]
              : [coralLight, coral],
        );
      canvas.drawCircle(pos, 9, nodePaint);

      // White ring
      canvas.drawCircle(
        pos,
        9,
        Paint()
          ..color = Colors.white.withOpacity(0.35)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1,
      );

      // Label (truncate long names)
      var label = meds[i];
      if (label.length > 12) label = '${label.substring(0, 11)}…';
      final angle = -math.pi / 2 + (2 * math.pi * i) / n;

      final textPainter = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(
            color: textColor.withOpacity(0.88),
            fontSize: 9.5,
            fontWeight: FontWeight.w600,
          ),
        ),
        textDirection: ui.TextDirection.ltr,
        textAlign: TextAlign.center,
      );
      textPainter.layout(maxWidth: 90);

      // Position label outside the node, away from center
      final labelDistance = radius + 22;
      final labelOffset = Offset(
        center.dx + labelDistance * math.cos(angle) - textPainter.width / 2,
        center.dy + labelDistance * math.sin(angle) - textPainter.height / 2,
      );
      textPainter.paint(canvas, labelOffset);
    }
  }

  @override
  bool shouldRepaint(covariant _InteractionMapPainter old) {
    return old.meds.length != meds.length ||
        old.findings.length != findings.length;
  }
}
