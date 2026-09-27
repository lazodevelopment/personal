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
// JOVI HEALTH — VITAL SIGNS TRACKER
// Version: 2026.09.22 (Apple HIG pass: painted glass instead of per-card
//          blur, press feedback, no looping motion, real 911 dialer,
//          keyboard-aware sheets, navy toasts)
// Base:    2026.04.17 (comprehensive rebuild)
//
// Features:
// • Dashboard with sparklines, summary stats, and crisis detection
// • Interactive trend chart (pinch-zoom, drag-crosshair tooltip, range bands)
// • Clinical classification (BP stages, glucose contexts, A1C estimate, BMI)
// • Pattern detection: morning surge, white-coat, med effectiveness
// • Medication cross-link (detects start dates, compares pre/post averages)
// • Context tagging: position, meal timing, stress, location, post-exercise
// • Goal setting per vital type with progress tracking
// • Reading log with filter, edit, delete, notes
// • CSV export + doctor-ready text report (clipboard)
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
import 'package:url_launcher/url_launcher.dart';

// ─── Enums ──────────────────────────────────────────────────────────────────

enum ScreenType { compact, medium, expanded, large }

enum _Tab { dashboard, trends, insights, log, goals }

enum VitalType {
  bloodPressure('Blood Pressure', 'mmHg', 'bp'),
  heartRate('Heart Rate', 'bpm', 'hr'),
  bloodGlucose('Blood Glucose', 'mg/dL', 'glucose'),
  weight('Weight', 'lbs', 'weight'),
  oxygen('Oxygen Saturation', '%', 'spo2'),
  temperature('Temperature', '°F', 'temp');

  const VitalType(this.label, this.unit, this.key);
  final String label;
  final String unit;
  final String key;

  static VitalType fromLabel(String s) {
    for (final v in VitalType.values) {
      if (v.label == s) return v;
    }
    return VitalType.bloodPressure;
  }
}

enum BPStage {
  normal('Normal', '<120 / <80'),
  elevated('Elevated', '120-129 / <80'),
  stage1('Stage 1 Hypertension', '130-139 / 80-89'),
  stage2('Stage 2 Hypertension', '≥140 / ≥90'),
  crisis('Hypertensive Crisis', '≥180 / ≥120'),
  lowBP('Low', '<90 / <60');

  const BPStage(this.label, this.range);
  final String label;
  final String range;
}

enum GlucoseContext {
  fasting('Fasting (8h+)', Icons.wb_sunny_outlined),
  beforeMeal('Before Meal', Icons.restaurant_outlined),
  afterMeal('After Meal (2h)', Icons.restaurant_rounded),
  bedtime('Bedtime', Icons.nights_stay_outlined),
  random('Random', Icons.schedule_rounded);

  const GlucoseContext(this.label, this.icon);
  final String label;
  final IconData icon;
}

enum BPPosition {
  sitting('Sitting'),
  standing('Standing'),
  lying('Lying');

  const BPPosition(this.label);
  final String label;
}

enum Location {
  home('Home'),
  office('Doctor\'s Office'),
  pharmacy('Pharmacy'),
  other('Other');

  const Location(this.label);
  final String label;
}

enum InsightSeverity { info, watch, concern, urgent }

// ─── Responsive config ──────────────────────────────────────────────────────

class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final int gridColumns;
  final double cardHeight;
  final double iconSize;
  final double fontSize;
  final bool wideMode;
  final bool hasHinge;
  final bool useTwoColumnLayout;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.gridColumns,
    required this.cardHeight,
    required this.iconSize,
    required this.fontSize,
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
  static const Color sky = Color(0xFF56CCF2);
  static const Color violet = Color(0xFFB388FF);

  static LinearGradient get coralGradient => const LinearGradient(
        colors: [coral, coralDark],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
  static LinearGradient get navyGradient => const LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [navy, navy, navyDark],
      );

  /// Color associated with a vital type
  static Color vitalColor(VitalType v) {
    switch (v) {
      case VitalType.bloodPressure:
        return softRed;
      case VitalType.heartRate:
        return coral;
      case VitalType.bloodGlucose:
        return violet;
      case VitalType.weight:
        return sky;
      case VitalType.oxygen:
        return mint;
      case VitalType.temperature:
        return gold;
    }
  }

  /// Severity color for status classification
  static Color severityColor(InsightSeverity s) {
    switch (s) {
      case InsightSeverity.info:
        return mint;
      case InsightSeverity.watch:
        return gold;
      case InsightSeverity.concern:
        return coral;
      case InsightSeverity.urgent:
        return errorRed;
    }
  }
}

// ─── Data Models ────────────────────────────────────────────────────────────

class VitalReading {
  final String id;
  final VitalType type;
  final DateTime timestamp;
  final double? value; // primary value (or systolic for BP)
  final double? secondary; // diastolic for BP
  final String source; // 'Manual' | 'Google Fit' | 'Import' | 'Photo OCR'
  final String? notes;
  final String? context; // glucose: fasting/before/after/bedtime
  final String? position; // BP: sitting/standing/lying
  final String? location; // home/office/pharmacy/other
  final bool postExercise;
  final bool underStress;

  VitalReading({
    required this.id,
    required this.type,
    required this.timestamp,
    this.value,
    this.secondary,
    this.source = 'Manual',
    this.notes,
    this.context,
    this.position,
    this.location,
    this.postExercise = false,
    this.underStress = false,
  });

  Map<String, dynamic> toFirestore() {
    return {
      'type': type.label,
      'value': value,
      if (secondary != null) 'systolic': value,
      if (secondary != null) 'diastolic': secondary,
      'unit': type.unit,
      'timestamp': Timestamp.fromDate(timestamp),
      'source': source,
      if (notes != null && notes!.isNotEmpty) 'notes': notes,
      if (context != null) 'context': context,
      if (position != null) 'position': position,
      if (location != null) 'location': location,
      if (postExercise) 'postExercise': true,
      if (underStress) 'underStress': true,
    };
  }

  static VitalReading fromDoc(String id, Map<String, dynamic> data) {
    final typeLabel = (data['type'] ?? '').toString();
    final type = VitalType.fromLabel(typeLabel);
    final ts = data['timestamp'];
    DateTime when = DateTime.now();
    if (ts is Timestamp) when = ts.toDate();

    double? value;
    double? secondary;
    if (type == VitalType.bloodPressure) {
      value = (data['systolic'] as num?)?.toDouble();
      secondary = (data['diastolic'] as num?)?.toDouble();
    } else {
      value = (data['value'] as num?)?.toDouble();
    }

    return VitalReading(
      id: id,
      type: type,
      timestamp: when,
      value: value,
      secondary: secondary,
      source: (data['source'] ?? 'Manual').toString(),
      notes: data['notes']?.toString(),
      context: data['context']?.toString(),
      position: data['position']?.toString(),
      location: data['location']?.toString(),
      postExercise: data['postExercise'] == true,
      underStress: data['underStress'] == true,
    );
  }

  /// Returns the display label for this reading's primary value
  String get displayValue {
    if (value == null) return '--';
    if (type == VitalType.bloodPressure) {
      return '${value!.toInt()}/${secondary?.toInt() ?? "?"}';
    }
    if (type == VitalType.weight || type == VitalType.temperature) {
      return value!.toStringAsFixed(1);
    }
    return value!.toInt().toString();
  }
}

class UserMedication {
  final String id;
  final String name;
  final String dosage;
  final String strength;
  final String? condition;
  final DateTime? startDate;
  final DateTime? stopDate;

  UserMedication({
    required this.id,
    required this.name,
    this.dosage = '',
    this.strength = '',
    this.condition,
    this.startDate,
    this.stopDate,
  });

  /// True if the medication is currently active (no stop date, or stop date in future)
  bool get isActive {
    if (stopDate == null) return true;
    return stopDate!.isAfter(DateTime.now());
  }
}

class VitalGoal {
  final VitalType type;
  // For BP: systolicMax + diastolicMax
  // For HR: min + max
  // For glucose: fastingMax
  // For weight: target
  // For O2: min
  // For temp: min + max
  final double? primaryMax;
  final double? primaryMin;
  final double? secondaryMax;
  final double? target;

  VitalGoal({
    required this.type,
    this.primaryMax,
    this.primaryMin,
    this.secondaryMax,
    this.target,
  });

  Map<String, dynamic> toMap() => {
        'type': type.label,
        if (primaryMax != null) 'primaryMax': primaryMax,
        if (primaryMin != null) 'primaryMin': primaryMin,
        if (secondaryMax != null) 'secondaryMax': secondaryMax,
        if (target != null) 'target': target,
      };

  static VitalGoal? defaultFor(VitalType t) {
    switch (t) {
      case VitalType.bloodPressure:
        return VitalGoal(type: t, primaryMax: 120, secondaryMax: 80);
      case VitalType.heartRate:
        return VitalGoal(type: t, primaryMin: 60, primaryMax: 100);
      case VitalType.bloodGlucose:
        return VitalGoal(type: t, primaryMax: 100);
      case VitalType.weight:
        return VitalGoal(type: t);
      case VitalType.oxygen:
        return VitalGoal(type: t, primaryMin: 95);
      case VitalType.temperature:
        return VitalGoal(type: t, primaryMin: 97.0, primaryMax: 99.0);
    }
  }
}

class Insight {
  final String title;
  final String body;
  final InsightSeverity severity;
  final IconData icon;
  final VitalType? relatedVital;
  final VoidCallback? action;
  final String? actionLabel;

  Insight({
    required this.title,
    required this.body,
    required this.severity,
    required this.icon,
    this.relatedVital,
    this.action,
    this.actionLabel,
  });
}

/// Summary stats for a series of readings
class VitalStats {
  final double? average;
  final double? secondaryAverage; // for BP diastolic
  final double? min;
  final double? max;
  final int count;
  final double? trend; // positive = going up, negative = going down
  final double? stdDev;

  VitalStats({
    this.average,
    this.secondaryAverage,
    this.min,
    this.max,
    this.count = 0,
    this.trend,
    this.stdDev,
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// CLINICAL KNOWLEDGE BASE
// Reference data used for classification, crisis detection, and insights.
// All thresholds sourced from AHA, ADA, and FDA guidelines.
// ═══════════════════════════════════════════════════════════════════════════

class _ClinicalRefs {
  // ─── Blood Pressure Classification (AHA 2017) ─────────────────────────────
  /// Given systolic and diastolic, returns the appropriate BP stage.
  /// Takes the HIGHER classification when systolic and diastolic disagree.
  static BPStage classifyBP(double systolic, double diastolic) {
    if (systolic >= 180 || diastolic >= 120) return BPStage.crisis;
    if (systolic < 90 || diastolic < 60) return BPStage.lowBP;
    if (systolic >= 140 || diastolic >= 90) return BPStage.stage2;
    if (systolic >= 130 || diastolic >= 80) return BPStage.stage1;
    if (systolic >= 120 && diastolic < 80) return BPStage.elevated;
    return BPStage.normal;
  }

  // ─── Glucose Classification (ADA 2024) ────────────────────────────────────
  /// Returns a classification label given mg/dL and context.
  static String classifyGlucose(double mgdl, GlucoseContext? ctx) {
    // Hypoglycemia takes precedence regardless of context
    if (mgdl < 54) return 'Severe Hypoglycemia';
    if (mgdl < 70) return 'Hypoglycemia';

    final c = ctx ?? GlucoseContext.random;
    if (c == GlucoseContext.fasting || c == GlucoseContext.beforeMeal) {
      if (mgdl < 100) return 'Normal (fasting)';
      if (mgdl < 126) return 'Impaired fasting glucose';
      return 'Diabetes range (fasting)';
    }
    // Post-meal or random
    if (c == GlucoseContext.afterMeal) {
      if (mgdl < 140) return 'Normal (post-meal)';
      if (mgdl < 200) return 'Impaired glucose tolerance';
      return 'Diabetes range (post-meal)';
    }
    // Random / bedtime
    if (mgdl > 400) return 'Severe Hyperglycemia';
    if (mgdl > 200) return 'High (random)';
    if (mgdl >= 70 && mgdl <= 140) return 'Normal range';
    return 'Elevated';
  }

  /// Estimates A1C from 30-day average glucose using ADAG formula.
  /// A1C = (avgGlucose + 46.7) / 28.7
  /// Only meaningful with ~30 days of data with varied timing.
  static double? estimateA1C(List<double> glucoseReadings) {
    if (glucoseReadings.length < 10) return null;
    final avg =
        glucoseReadings.reduce((a, b) => a + b) / glucoseReadings.length;
    return ((avg + 46.7) / 28.7).clamp(4.0, 14.0);
  }

  /// A1C interpretation (ADA)
  static String interpretA1C(double a1c) {
    if (a1c < 5.7) return 'Normal';
    if (a1c < 6.5) return 'Prediabetes';
    if (a1c < 7.0) return 'Diabetes (well-controlled)';
    if (a1c < 8.0) return 'Diabetes (moderate control)';
    return 'Diabetes (poorly controlled)';
  }

  // ─── BMI Calculation ──────────────────────────────────────────────────────
  /// BMI from weight (lbs) and height (inches)
  static double? calculateBMI(double weightLbs, double? heightInches) {
    if (heightInches == null || heightInches <= 0) return null;
    // BMI = 703 × weight(lb) / height(in)²
    return (703 * weightLbs) / (heightInches * heightInches);
  }

  static String interpretBMI(double bmi) {
    if (bmi < 18.5) return 'Underweight';
    if (bmi < 25.0) return 'Healthy weight';
    if (bmi < 30.0) return 'Overweight';
    if (bmi < 35.0) return 'Obesity class I';
    if (bmi < 40.0) return 'Obesity class II';
    return 'Obesity class III';
  }

  // ─── Crisis Thresholds ────────────────────────────────────────────────────
  /// Returns (severity, message) if reading is in crisis range, else null.
  static List<String>? checkCrisis(VitalReading r) {
    switch (r.type) {
      case VitalType.bloodPressure:
        if (r.value == null || r.secondary == null) return null;
        if (r.value! >= 180 || r.secondary! >= 120) {
          return [
            'Hypertensive Crisis',
            'BP ${r.value!.toInt()}/${r.secondary!.toInt()} is severely elevated. If you also have chest pain, shortness of breath, vision changes, severe headache, or weakness, call 911 immediately. Otherwise, contact your doctor now.',
          ];
        }
        if (r.value! < 80 || r.secondary! < 50) {
          return [
            'Severely Low BP',
            'BP ${r.value!.toInt()}/${r.secondary!.toInt()} is very low. If you feel dizzy, faint, or confused, contact emergency services.',
          ];
        }
        return null;
      case VitalType.bloodGlucose:
        if (r.value == null) return null;
        if (r.value! < 54) {
          return [
            'Severe Hypoglycemia',
            'Blood glucose of ${r.value!.toInt()} mg/dL is dangerously low. Eat 15g of fast-acting carbs (juice, glucose tabs) NOW and recheck in 15 minutes. If symptoms persist or worsen, call 911.',
          ];
        }
        if (r.value! > 400) {
          return [
            'Severe Hyperglycemia',
            'Blood glucose of ${r.value!.toInt()} mg/dL is dangerously high. If you have nausea, vomiting, confusion, rapid breathing, or fruity breath, this could be diabetic ketoacidosis. Call your doctor or seek emergency care immediately.',
          ];
        }
        return null;
      case VitalType.oxygen:
        if (r.value == null) return null;
        if (r.value! < 88) {
          return [
            'Critically Low Oxygen',
            'SpO2 of ${r.value!.toInt()}% indicates dangerous hypoxia. If you have shortness of breath, confusion, or chest pain, call 911 immediately.',
          ];
        }
        if (r.value! < 92) {
          return [
            'Low Oxygen',
            'SpO2 of ${r.value!.toInt()}% is below normal. Contact your doctor, especially if symptomatic.',
          ];
        }
        return null;
      case VitalType.heartRate:
        if (r.value == null) return null;
        if (r.value! > 140 && !r.postExercise) {
          return [
            'Very High Heart Rate',
            'Heart rate of ${r.value!.toInt()} bpm at rest is unusually high. If you have chest pain, shortness of breath, or feel faint, call 911.',
          ];
        }
        if (r.value! < 40) {
          return [
            'Very Low Heart Rate',
            'Heart rate of ${r.value!.toInt()} bpm is unusually low. If you feel lightheaded, confused, or faint, seek urgent care.',
          ];
        }
        return null;
      case VitalType.temperature:
        if (r.value == null) return null;
        if (r.value! >= 103.0) {
          return [
            'High Fever',
            'Temperature of ${r.value!.toStringAsFixed(1)}°F indicates significant fever. Hydrate, monitor closely, and contact your doctor. If you have stiff neck, severe headache, rash, or confusion, seek urgent care.',
          ];
        }
        if (r.value! < 95.0) {
          return [
            'Hypothermia',
            'Temperature of ${r.value!.toStringAsFixed(1)}°F is dangerously low. Warm up and seek medical attention.',
          ];
        }
        return null;
      default:
        return null;
    }
  }

  // ─── Medication → Vital Relationships ─────────────────────────────────────
  /// Meds that affect BP (either lowering or raising)
  static const Map<String, String> bpMeds = {
    'lisinopril': 'ACE inhibitor — expected to lower BP',
    'enalapril': 'ACE inhibitor — expected to lower BP',
    'ramipril': 'ACE inhibitor — expected to lower BP',
    'losartan': 'ARB — expected to lower BP',
    'valsartan': 'ARB — expected to lower BP',
    'olmesartan': 'ARB — expected to lower BP',
    'amlodipine': 'Calcium channel blocker — expected to lower BP',
    'diltiazem': 'Calcium channel blocker — expected to lower BP',
    'metoprolol': 'Beta-blocker — lowers BP and heart rate',
    'atenolol': 'Beta-blocker — lowers BP and heart rate',
    'carvedilol': 'Beta-blocker — lowers BP and heart rate',
    'propranolol': 'Beta-blocker — lowers BP and heart rate',
    'hydrochlorothiazide': 'Diuretic — expected to lower BP',
    'chlorthalidone': 'Diuretic — expected to lower BP',
    'furosemide': 'Loop diuretic — lowers BP via volume reduction',
    'spironolactone': 'Potassium-sparing diuretic — lowers BP',
    'clonidine': 'Alpha agonist — lowers BP',
    'hydralazine': 'Vasodilator — lowers BP',
    'nifedipine': 'Calcium channel blocker — lowers BP',
    'prazosin': 'Alpha blocker — lowers BP',
    'doxazosin': 'Alpha blocker — lowers BP',
    'terazosin': 'Alpha blocker — lowers BP',
  };

  /// Meds that affect glucose
  static const Map<String, String> glucoseMeds = {
    'metformin': 'First-line diabetes med — lowers fasting glucose',
    'glipizide': 'Sulfonylurea — stimulates insulin release',
    'glyburide': 'Sulfonylurea — stimulates insulin release',
    'glimepiride': 'Sulfonylurea — stimulates insulin release',
    'insulin': 'Insulin — directly lowers glucose',
    'sitagliptin': 'DPP-4 inhibitor — lowers post-meal glucose',
    'semaglutide': 'GLP-1 agonist — lowers glucose and weight',
    'liraglutide': 'GLP-1 agonist — lowers glucose and weight',
    'tirzepatide': 'GLP-1/GIP agonist — lowers glucose and weight',
    'empagliflozin': 'SGLT-2 inhibitor — lowers glucose via urinary excretion',
    'dapagliflozin': 'SGLT-2 inhibitor — lowers glucose via urinary excretion',
    'pioglitazone': 'TZD — improves insulin sensitivity',
    'prednisone': 'Corticosteroid — may RAISE blood glucose',
    'dexamethasone': 'Corticosteroid — may RAISE blood glucose',
  };

  /// Meds that affect heart rate
  static const Map<String, String> heartRateMeds = {
    'metoprolol': 'Beta-blocker — lowers heart rate',
    'atenolol': 'Beta-blocker — lowers heart rate',
    'carvedilol': 'Beta-blocker — lowers heart rate',
    'propranolol': 'Beta-blocker — lowers heart rate',
    'bisoprolol': 'Beta-blocker — lowers heart rate',
    'diltiazem': 'Calcium channel blocker — lowers heart rate',
    'verapamil': 'Calcium channel blocker — lowers heart rate',
    'digoxin': 'Cardiac glycoside — lowers heart rate',
    'amiodarone': 'Antiarrhythmic — affects heart rate',
    'ivabradine': 'Directly lowers heart rate',
    'levothyroxine': 'May raise heart rate if dose too high',
    'albuterol': 'Beta-agonist inhaler — may transiently raise heart rate',
  };

  /// Meds that affect weight
  static const Map<String, String> weightMeds = {
    'semaglutide': 'GLP-1 agonist — promotes weight loss',
    'liraglutide': 'GLP-1 agonist — promotes weight loss',
    'tirzepatide': 'GLP-1/GIP agonist — significant weight loss',
    'phentermine': 'Appetite suppressant — weight loss',
    'orlistat': 'Fat absorption blocker — weight loss',
    'bupropion/naltrexone': 'Weight loss combination',
    'metformin': 'May cause modest weight loss',
    'prednisone': 'May cause weight gain',
    'mirtazapine': 'May cause weight gain',
    'olanzapine': 'May cause significant weight gain',
    'quetiapine': 'May cause weight gain',
    'insulin': 'May cause weight gain',
    'glipizide': 'Sulfonylurea — may cause weight gain',
    'amitriptyline': 'May cause weight gain',
    'paroxetine': 'SSRI most associated with weight gain',
    'gabapentin': 'May cause weight gain',
  };

  /// Lookup what a med affects
  static List<String> affectedVitals(String medName) {
    final key = medName.toLowerCase().trim();
    final result = <String>[];
    for (final entry in bpMeds.entries) {
      if (key.contains(entry.key) || entry.key.contains(key)) {
        result.add('bp');
        break;
      }
    }
    for (final entry in glucoseMeds.entries) {
      if (key.contains(entry.key) || entry.key.contains(key)) {
        result.add('glucose');
        break;
      }
    }
    for (final entry in heartRateMeds.entries) {
      if (key.contains(entry.key) || entry.key.contains(key)) {
        result.add('hr');
        break;
      }
    }
    for (final entry in weightMeds.entries) {
      if (key.contains(entry.key) || entry.key.contains(key)) {
        result.add('weight');
        break;
      }
    }
    return result;
  }

  static String? medEffect(String medName, VitalType vital) {
    final key = medName.toLowerCase().trim();
    Map<String, String> lookup;
    switch (vital) {
      case VitalType.bloodPressure:
        lookup = bpMeds;
        break;
      case VitalType.bloodGlucose:
        lookup = glucoseMeds;
        break;
      case VitalType.heartRate:
        lookup = heartRateMeds;
        break;
      case VitalType.weight:
        lookup = weightMeds;
        break;
      default:
        return null;
    }
    for (final entry in lookup.entries) {
      if (key.contains(entry.key) || entry.key.contains(key)) {
        return entry.value;
      }
    }
    return null;
  }
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

class VitalSignsTrackerWidget extends StatefulWidget {
  const VitalSignsTrackerWidget({
    super.key,
    this.width,
    this.height,
  });

  final double? width;
  final double? height;

  @override
  State<VitalSignsTrackerWidget> createState() =>
      _VitalSignsTrackerWidgetState();
}

class _VitalSignsTrackerWidgetState extends State<VitalSignsTrackerWidget>
    with TickerProviderStateMixin {
  // ─── Tab & view state ────────────────────────────────────────────────────
  _Tab _tab = _Tab.dashboard;
  bool _isLoading = true;
  VitalType _selectedVital = VitalType.bloodPressure;
  String _timeRange = '30d'; // '7d' | '30d' | '90d' | 'all'
  VitalType? _compareVital; // for trends tab multi-series

  // ─── Data state ──────────────────────────────────────────────────────────
  final Map<VitalType, List<VitalReading>> _readingsByType = {};
  List<VitalReading> _allReadings = [];
  List<UserMedication> _medications = [];
  Map<VitalType, VitalGoal> _goals = {};
  double? _userHeightInches;

  // ─── Insights cache ──────────────────────────────────────────────────────
  // _generateInsights() is called from both the tab badge and the Insights
  // tab body; caching avoids duplicate work within a single frame.
  List<Insight>? _insightsCache;
  String? _insightsCacheKey;

  void _invalidateInsights() {
    _insightsCache = null;
    _insightsCacheKey = null;
  }

  // ─── Firestore refs ──────────────────────────────────────────────────────
  late String _uid;
  late CollectionReference _vitalsRef;
  late CollectionReference _medsRef;
  late DocumentReference _userRef;
  late DocumentReference _goalsRef;

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
      _vitalsRef = _userRef.collection('vital_signs');
      _medsRef =
          _userRef.collection('members').doc('self').collection('medications');
      _goalsRef = _userRef.collection('vital_goals').doc('goals');
      _loadData();
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _loadData() async {
    if (!mounted) return;
    setState(() => _isLoading = true);

    try {
      // User profile (height, etc.)
      final userDoc = await _userRef.get();
      if (userDoc.exists) {
        final data = userDoc.data() as Map<String, dynamic>;
        final h = data['heightInches'];
        if (h is num) _userHeightInches = h.toDouble();
      }

      // Medications
      final medsSnap = await _medsRef.get();
      _medications = medsSnap.docs.map((d) {
        final data = d.data() as Map<String, dynamic>;
        DateTime? start;
        DateTime? stop;
        final s = data['startDate'];
        if (s is Timestamp) start = s.toDate();
        final st = data['stopDate'];
        if (st is Timestamp) stop = st.toDate();
        return UserMedication(
          id: d.id,
          name: (data['name'] ?? '').toString(),
          dosage: (data['dosage'] ?? '').toString(),
          strength: (data['strength'] ?? '').toString(),
          condition: data['condition']?.toString(),
          startDate: start,
          stopDate: stop,
        );
      }).toList();

      // Vital readings (last 90 days by default; we'll filter in-memory for views)
      final cutoff = DateTime.now().subtract(const Duration(days: 365));
      final snap = await _vitalsRef
          .where('timestamp', isGreaterThan: Timestamp.fromDate(cutoff))
          .orderBy('timestamp', descending: true)
          .limit(1000)
          .get();

      _allReadings = snap.docs
          .map((d) =>
              VitalReading.fromDoc(d.id, d.data() as Map<String, dynamic>))
          .toList();

      _readingsByType.clear();
      for (final r in _allReadings) {
        _readingsByType.putIfAbsent(r.type, () => []).add(r);
      }

      // Goals
      final goalsDoc = await _goalsRef.get();
      _goals.clear();
      if (goalsDoc.exists) {
        final data = goalsDoc.data() as Map<String, dynamic>;
        for (final t in VitalType.values) {
          final g = data[t.key];
          if (g is Map) {
            _goals[t] = VitalGoal(
              type: t,
              primaryMax: (g['primaryMax'] as num?)?.toDouble(),
              primaryMin: (g['primaryMin'] as num?)?.toDouble(),
              secondaryMax: (g['secondaryMax'] as num?)?.toDouble(),
              target: (g['target'] as num?)?.toDouble(),
            );
          }
        }
      }
      // Backfill defaults for missing goals
      for (final t in VitalType.values) {
        if (!_goals.containsKey(t)) {
          final def = VitalGoal.defaultFor(t);
          if (def != null) _goals[t] = def;
        }
      }

      if (!mounted) return;
      _invalidateInsights();
      setState(() => _isLoading = false);
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  // ═════════════════════════════════════════════════════════════════════════
  // QUERIES / HELPERS
  // ═════════════════════════════════════════════════════════════════════════

  DateTime _rangeCutoff() {
    final now = DateTime.now();
    switch (_timeRange) {
      case '7d':
        return now.subtract(const Duration(days: 7));
      case '30d':
        return now.subtract(const Duration(days: 30));
      case '90d':
        return now.subtract(const Duration(days: 90));
      case 'all':
      default:
        return DateTime(2000);
    }
  }

  List<VitalReading> _readingsInRange(VitalType type) {
    final cutoff = _rangeCutoff();
    return (_readingsByType[type] ?? [])
        .where((r) => r.timestamp.isAfter(cutoff))
        .toList()
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));
  }

  VitalReading? _latestOf(VitalType type) {
    final list = _readingsByType[type];
    if (list == null || list.isEmpty) return null;
    list.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return list.first;
  }

  /// Compute stats for a list of readings. For BP, primary=systolic, secondary=diastolic.
  VitalStats _computeStats(List<VitalReading> readings) {
    if (readings.isEmpty) return VitalStats();
    final primary = <double>[];
    final secondary = <double>[];
    for (final r in readings) {
      if (r.value != null) primary.add(r.value!);
      if (r.secondary != null) secondary.add(r.secondary!);
    }
    if (primary.isEmpty) return VitalStats(count: 0);

    final avg = primary.reduce((a, b) => a + b) / primary.length;
    final min = primary.reduce(math.min);
    final max = primary.reduce(math.max);

    // Trend: simple least-squares slope over timestamps
    double? trend;
    if (primary.length >= 3) {
      final sorted = [...readings]
        ..sort((a, b) => a.timestamp.compareTo(b.timestamp));
      final xs = sorted
          .map((r) => r.timestamp.millisecondsSinceEpoch.toDouble())
          .toList();
      final ys = sorted.map((r) => r.value ?? 0).toList();
      if (ys.isNotEmpty) {
        final meanX = xs.reduce((a, b) => a + b) / xs.length;
        final meanY = ys.reduce((a, b) => a + b) / ys.length;
        double numerator = 0;
        double denominator = 0;
        for (int i = 0; i < xs.length; i++) {
          numerator += (xs[i] - meanX) * (ys[i] - meanY);
          denominator += (xs[i] - meanX) * (xs[i] - meanX);
        }
        if (denominator > 0) {
          // slope per day
          trend = (numerator / denominator) * 86400000;
        }
      }
    }

    // Std dev
    double? stdDev;
    if (primary.length >= 3) {
      final variance =
          primary.map((v) => math.pow(v - avg, 2)).reduce((a, b) => a + b) /
              primary.length;
      stdDev = math.sqrt(variance).toDouble();
    }

    double? secAvg;
    if (secondary.isNotEmpty) {
      secAvg = secondary.reduce((a, b) => a + b) / secondary.length;
    }

    return VitalStats(
      average: avg,
      secondaryAverage: secAvg,
      min: min,
      max: max,
      count: primary.length,
      trend: trend,
      stdDev: stdDev,
    );
  }

  /// Produce clinical insights based on current data.
  /// Cached within a frame — cache invalidates when data or time range changes.
  List<Insight> _generateInsights() {
    // Cache key: data version + time range + user height (affects BMI insight)
    final key =
        '${_allReadings.length}|${_medications.length}|${_goals.length}|$_timeRange|${_userHeightInches ?? ""}';
    if (_insightsCache != null && _insightsCacheKey == key) {
      return _insightsCache!;
    }

    final out = <Insight>[];

    // ─── CRISIS CHECK (most recent reading of each type) ────────────────────
    for (final t in VitalType.values) {
      final latest = _latestOf(t);
      if (latest == null) continue;
      final crisis = _ClinicalRefs.checkCrisis(latest);
      if (crisis != null) {
        out.add(Insight(
          title: crisis[0],
          body: crisis[1],
          severity: InsightSeverity.urgent,
          icon: Icons.warning_rounded,
          relatedVital: t,
        ));
      }
    }

    // ─── BP STAGE + TREND ───────────────────────────────────────────────────
    final bpReadings = _readingsInRange(VitalType.bloodPressure);
    if (bpReadings.length >= 3) {
      final stats = _computeStats(bpReadings);
      if (stats.average != null && stats.secondaryAverage != null) {
        final stage =
            _ClinicalRefs.classifyBP(stats.average!, stats.secondaryAverage!);
        if (stage != BPStage.normal) {
          final severity = stage == BPStage.crisis
              ? InsightSeverity.urgent
              : stage == BPStage.stage2
                  ? InsightSeverity.concern
                  : stage == BPStage.stage1
                      ? InsightSeverity.watch
                      : InsightSeverity.info;
          out.add(Insight(
            title: 'Average BP: ${stage.label}',
            body:
                'Over the past ${_timeRangeLabel()}, your average BP was ${stats.average!.toInt()}/${stats.secondaryAverage!.toInt()} (${stats.count} readings). This falls in the ${stage.label} range (${stage.range}).',
            severity: severity,
            icon: Icons.favorite_rounded,
            relatedVital: VitalType.bloodPressure,
          ));
        }
      }
      // BP trend
      if (stats.trend != null && stats.trend!.abs() > 0.3) {
        final directionIsUp = stats.trend! > 0;
        final daysInRange = _rangeDays();
        final totalChange = (stats.trend! * daysInRange).abs();
        if (totalChange >= 5) {
          out.add(Insight(
            title: directionIsUp ? 'BP trending up' : 'BP trending down',
            body:
                'Your systolic BP has ${directionIsUp ? "risen" : "fallen"} by about ${totalChange.toInt()} mmHg over the past ${_timeRangeLabel()}. ${directionIsUp ? "Consider discussing this with your provider." : "This is a positive trend if intended."}',
            severity:
                directionIsUp ? InsightSeverity.watch : InsightSeverity.info,
            icon: directionIsUp
                ? Icons.trending_up_rounded
                : Icons.trending_down_rounded,
            relatedVital: VitalType.bloodPressure,
          ));
        }
      }
    }

    // ─── MORNING SURGE DETECTION ────────────────────────────────────────────
    final morningSurge = _detectMorningSurge();
    if (morningSurge != null) out.add(morningSurge);

    // ─── WHITE COAT DETECTION ──────────────────────────────────────────────
    final whiteCoat = _detectWhiteCoat();
    if (whiteCoat != null) out.add(whiteCoat);

    // ─── ORTHOSTATIC HYPOTENSION ───────────────────────────────────────────
    final orthostatic = _detectOrthostaticDrop();
    if (orthostatic != null) out.add(orthostatic);

    // ─── A1C ESTIMATE ───────────────────────────────────────────────────────
    final glucoseReadings = _readingsInRange(VitalType.bloodGlucose);
    if (glucoseReadings.length >= 10) {
      final values = glucoseReadings
          .where((r) => r.value != null)
          .map((r) => r.value!)
          .toList();
      final a1c = _ClinicalRefs.estimateA1C(values);
      if (a1c != null) {
        out.add(Insight(
          title: 'Estimated A1C: ${a1c.toStringAsFixed(1)}%',
          body:
              '${_ClinicalRefs.interpretA1C(a1c)}. This is an estimate from ${values.length} glucose readings using the ADAG formula. A lab A1C is more accurate.',
          severity: a1c < 7.0
              ? InsightSeverity.info
              : a1c < 8.0
                  ? InsightSeverity.watch
                  : InsightSeverity.concern,
          icon: Icons.water_drop_rounded,
          relatedVital: VitalType.bloodGlucose,
        ));
      }
    }

    // ─── BMI ────────────────────────────────────────────────────────────────
    final latestWeight = _latestOf(VitalType.weight);
    if (latestWeight?.value != null) {
      final bmi =
          _ClinicalRefs.calculateBMI(latestWeight!.value!, _userHeightInches);
      if (bmi != null) {
        out.add(Insight(
          title: 'BMI: ${bmi.toStringAsFixed(1)}',
          body: '${_ClinicalRefs.interpretBMI(bmi)}.',
          severity: bmi < 18.5 || bmi >= 30
              ? InsightSeverity.watch
              : InsightSeverity.info,
          icon: Icons.monitor_weight_rounded,
          relatedVital: VitalType.weight,
        ));
      } else if (_userHeightInches == null) {
        out.add(Insight(
          title: 'Set your height to see BMI',
          body:
              'Your weight readings are being tracked, but we need your height to calculate BMI.',
          severity: InsightSeverity.info,
          icon: Icons.height_rounded,
          relatedVital: VitalType.weight,
          actionLabel: 'Set height',
          action: _promptHeight,
        ));
      }
    }

    // ─── MEDICATION EFFECTIVENESS (pre/post start comparison) ───────────────
    final medInsights = _detectMedEffectiveness();
    out.addAll(medInsights);

    // ─── GOAL PROGRESS ──────────────────────────────────────────────────────
    final goalInsights = _checkGoalProgress();
    out.addAll(goalInsights);

    // Sort by severity then alphabetically
    out.sort((a, b) {
      final order = {
        InsightSeverity.urgent: 0,
        InsightSeverity.concern: 1,
        InsightSeverity.watch: 2,
        InsightSeverity.info: 3,
      };
      return order[a.severity]!.compareTo(order[b.severity]!);
    });

    _insightsCache = out;
    _insightsCacheKey = key;
    return out;
  }

  int _rangeDays() {
    switch (_timeRange) {
      case '7d':
        return 7;
      case '30d':
        return 30;
      case '90d':
        return 90;
      case 'all':
      default:
        return 365;
    }
  }

  String _timeRangeLabel() {
    switch (_timeRange) {
      case '7d':
        return '7 days';
      case '30d':
        return '30 days';
      case '90d':
        return '90 days';
      case 'all':
      default:
        return 'year';
    }
  }

  /// Detect exaggerated morning BP surge (>35 mmHg from overnight average)
  Insight? _detectMorningSurge() {
    final bp = _readingsInRange(VitalType.bloodPressure);
    if (bp.length < 8) return null;

    // Morning = 5am-10am readings
    final morning = bp
        .where((r) => r.timestamp.hour >= 5 && r.timestamp.hour < 10)
        .toList();
    // Evening/night = 8pm-2am
    final evening = bp
        .where((r) => r.timestamp.hour >= 20 || r.timestamp.hour < 2)
        .toList();

    if (morning.length < 3 || evening.length < 3) return null;

    final morningAvg =
        morning.map((r) => r.value ?? 0).reduce((a, b) => a + b) /
            morning.length;
    final eveningAvg =
        evening.map((r) => r.value ?? 0).reduce((a, b) => a + b) /
            evening.length;
    final surge = morningAvg - eveningAvg;

    if (surge >= 35) {
      return Insight(
        title: 'Morning BP surge detected',
        body:
            'Your morning readings average ${surge.toInt()} mmHg higher than evening readings. An exaggerated morning surge (>35 mmHg) is an independent cardiovascular risk factor worth mentioning to your doctor.',
        severity: InsightSeverity.watch,
        icon: Icons.wb_twilight_rounded,
        relatedVital: VitalType.bloodPressure,
      );
    }
    return null;
  }

  /// Detect "white coat" hypertension (higher at office than home)
  Insight? _detectWhiteCoat() {
    final bp = _readingsInRange(VitalType.bloodPressure);
    if (bp.length < 5) return null;

    final home = bp
        .where((r) => r.location == Location.home.label && r.value != null)
        .map((r) => r.value!)
        .toList();
    final office = bp
        .where((r) => r.location == Location.office.label && r.value != null)
        .map((r) => r.value!)
        .toList();

    if (home.length < 3 || office.isEmpty) return null;

    final homeAvg = home.reduce((a, b) => a + b) / home.length;
    final officeAvg = office.reduce((a, b) => a + b) / office.length;
    final diff = officeAvg - homeAvg;

    if (diff >= 20) {
      return Insight(
        title: 'Possible white-coat hypertension',
        body:
            'Your office BP averages ${diff.toInt()} mmHg higher than your home readings. This pattern, called white-coat hypertension, is worth showing to your doctor — at-home readings are often more representative.',
        severity: InsightSeverity.info,
        icon: Icons.local_hospital_rounded,
        relatedVital: VitalType.bloodPressure,
      );
    }
    if (diff <= -15 && home.length >= 5) {
      return Insight(
        title: 'Possible masked hypertension',
        body:
            'Your home BP averages ${diff.abs().toInt()} mmHg higher than office readings. This pattern, called masked hypertension, is often missed during clinic visits and worth discussing with your doctor.',
        severity: InsightSeverity.watch,
        icon: Icons.home_rounded,
        relatedVital: VitalType.bloodPressure,
      );
    }
    return null;
  }

  /// Detects orthostatic hypotension: a drop of ≥20 mmHg systolic or ≥10 mmHg
  /// diastolic when moving from sitting/lying to standing.
  ///
  /// Clinical note: the AHA/AAS definition requires measurement within 3 min
  /// of standing. Since we don't have sub-minute timing, we use same-day pairs
  /// within a 30-minute window as a reasonable proxy. This is a conservative
  /// filter — we'd rather miss a positive than false-alarm.
  Insight? _detectOrthostaticDrop() {
    final bp = _readingsInRange(VitalType.bloodPressure);
    if (bp.length < 4) return null;

    // Find standing readings
    final standing = bp
        .where((r) =>
            r.position == BPPosition.standing.label &&
            r.value != null &&
            r.secondary != null)
        .toList();
    if (standing.isEmpty) return null;

    // For each standing reading, find the closest seated/lying reading within 30 min
    final drops = <List<double>>[]; // [systolicDrop, diastolicDrop]
    for (final stand in standing) {
      VitalReading? paired;
      Duration bestGap = const Duration(minutes: 31);
      for (final r in bp) {
        if (r.value == null || r.secondary == null) continue;
        if (r.position != BPPosition.sitting.label &&
            r.position != BPPosition.lying.label) continue;
        // Seated/lying reading must precede the standing reading
        if (!r.timestamp.isBefore(stand.timestamp)) continue;
        final gap = stand.timestamp.difference(r.timestamp);
        if (gap.inMinutes <= 30 && gap < bestGap) {
          paired = r;
          bestGap = gap;
        }
      }
      if (paired != null) {
        final sysDrop = paired.value! - stand.value!;
        final diaDrop = paired.secondary! - stand.secondary!;
        if (sysDrop > 0 || diaDrop > 0) {
          drops.add([sysDrop, diaDrop]);
        }
      }
    }

    if (drops.length < 2) return null;

    // Average the drops
    final avgSysDrop =
        drops.map((d) => d[0]).reduce((a, b) => a + b) / drops.length;
    final avgDiaDrop =
        drops.map((d) => d[1]).reduce((a, b) => a + b) / drops.length;

    // Clinical threshold: sys drop ≥20 OR dia drop ≥10
    final significantSys = avgSysDrop >= 20;
    final significantDia = avgDiaDrop >= 10;
    if (!significantSys && !significantDia) return null;

    final sevThreshold = avgSysDrop >= 30 || avgDiaDrop >= 15;

    return Insight(
      title: 'Possible orthostatic hypotension',
      body:
          'When you stand up, your BP drops by an average of ${avgSysDrop.toInt()}/${avgDiaDrop.toInt()} mmHg compared to sitting or lying down (${drops.length} paired readings). A drop of 20/10 mmHg or more within minutes of standing can cause dizziness, lightheadedness, and falls. This is worth discussing with your doctor, especially if you take BP medications, diuretics, or antidepressants.',
      severity: sevThreshold ? InsightSeverity.concern : InsightSeverity.watch,
      icon: Icons.accessibility_new_rounded,
      relatedVital: VitalType.bloodPressure,
    );
  }

  /// For each med with a start date, compare pre-med vs on-med averages.
  /// If the med has a stop date, the "on-med" window is bounded by it.
  /// If there are ≥3 readings after stopDate, we also surface a rebound insight.
  List<Insight> _detectMedEffectiveness() {
    final out = <Insight>[];

    for (final med in _medications) {
      if (med.startDate == null) continue;
      final affected = _ClinicalRefs.affectedVitals(med.name);
      if (affected.isEmpty) continue;

      for (final vk in affected) {
        VitalType? vital;
        if (vk == 'bp') vital = VitalType.bloodPressure;
        if (vk == 'glucose') vital = VitalType.bloodGlucose;
        if (vk == 'hr') vital = VitalType.heartRate;
        if (vk == 'weight') vital = VitalType.weight;
        if (vital == null) continue;

        final all = _readingsByType[vital] ?? [];
        // Pre = before startDate
        final pre = all
            .where(
                (r) => r.timestamp.isBefore(med.startDate!) && r.value != null)
            .toList();
        // On = between startDate and stopDate (or present if still active)
        final onEnd = med.stopDate ?? DateTime.now();
        final on = all
            .where((r) =>
                r.timestamp.isAfter(med.startDate!) &&
                !r.timestamp.isAfter(onEnd) &&
                r.value != null)
            .toList();

        if (pre.length >= 3 && on.length >= 3) {
          final preAvg =
              pre.map((r) => r.value!).reduce((a, b) => a + b) / pre.length;
          final onAvg =
              on.map((r) => r.value!).reduce((a, b) => a + b) / on.length;
          final change = onAvg - preAvg;
          final pctChange = (change / preAvg) * 100;

          // Only surface if there's a meaningful change (>3% and >2 units)
          if (pctChange.abs() < 3 || change.abs() < 2) continue;

          final effect = _ClinicalRefs.medEffect(med.name, vital);
          final expectedDown = effect != null &&
              (effect.toLowerCase().contains('lower') ||
                  effect.toLowerCase().contains('weight loss'));
          final wentDown = change < 0;
          final windowSuffix = med.stopDate != null
              ? ' (while on ${med.name} from ${_formatDateShort(med.startDate!)} to ${_formatDateShort(med.stopDate!)})'
              : '';

          String title, body;
          InsightSeverity severity;
          if (expectedDown && wentDown) {
            title = '${med.name} appears effective';
            body =
                'After starting ${med.name} on ${_formatDateShort(med.startDate!)}, your average ${vital.label} dropped by ${change.abs().toStringAsFixed(1)} ${vital.unit} (${preAvg.toStringAsFixed(1)} → ${onAvg.toStringAsFixed(1)})$windowSuffix. ${effect ?? ""}';
            severity = InsightSeverity.info;
          } else if (expectedDown && !wentDown) {
            title = '${med.name} — limited effect';
            body =
                'After starting ${med.name} on ${_formatDateShort(med.startDate!)}, your average ${vital.label} has not decreased. Pre: ${preAvg.toStringAsFixed(1)}, On-med: ${onAvg.toStringAsFixed(1)}$windowSuffix. Consider discussing with your prescriber.';
            severity = InsightSeverity.watch;
          } else if (!expectedDown && !wentDown) {
            title = '${med.name} — weight change';
            body =
                'Since starting ${med.name} on ${_formatDateShort(med.startDate!)}, your average weight increased by ${change.abs().toStringAsFixed(1)} lbs$windowSuffix. ${effect ?? ""}';
            severity = InsightSeverity.info;
          } else {
            continue;
          }

          out.add(Insight(
            title: title,
            body: body,
            severity: severity,
            icon: Icons.medication_rounded,
            relatedVital: vital,
          ));
        }

        // Rebound check: med was stopped and we have post-stop data
        if (med.stopDate != null) {
          final post = all
              .where(
                  (r) => r.timestamp.isAfter(med.stopDate!) && r.value != null)
              .toList();
          if (on.length >= 3 && post.length >= 3) {
            final onAvg =
                on.map((r) => r.value!).reduce((a, b) => a + b) / on.length;
            final postAvg =
                post.map((r) => r.value!).reduce((a, b) => a + b) / post.length;
            final reboundChange = postAvg - onAvg;
            final pctChange = (reboundChange / onAvg) * 100;

            if (pctChange.abs() >= 4 && reboundChange.abs() >= 3) {
              final effect = _ClinicalRefs.medEffect(med.name, vital);
              final wasReducing = effect != null &&
                  (effect.toLowerCase().contains('lower') ||
                      effect.toLowerCase().contains('weight loss'));
              // Rebound = vital went back up after stopping a lowering med
              if (wasReducing && reboundChange > 0) {
                out.add(Insight(
                  title: 'Possible ${med.name} rebound',
                  body:
                      'After you stopped ${med.name} on ${_formatDateShort(med.stopDate!)}, your average ${vital.label} rose by ${reboundChange.toStringAsFixed(1)} ${vital.unit} (${onAvg.toStringAsFixed(1)} → ${postAvg.toStringAsFixed(1)}). If this was an unplanned stop, discuss with your doctor.',
                  severity: InsightSeverity.watch,
                  icon: Icons.trending_up_rounded,
                  relatedVital: vital,
                ));
              }
            }
          }
        }
      }
    }

    return out;
  }

  List<Insight> _checkGoalProgress() {
    final out = <Insight>[];
    for (final t in VitalType.values) {
      final goal = _goals[t];
      if (goal == null) continue;
      final readings = _readingsInRange(t);
      if (readings.length < 3) continue;
      final stats = _computeStats(readings);
      if (stats.average == null) continue;

      bool atGoal = false;
      String statusBody = '';

      if (t == VitalType.bloodPressure &&
          goal.primaryMax != null &&
          goal.secondaryMax != null &&
          stats.secondaryAverage != null) {
        atGoal = stats.average! <= goal.primaryMax! &&
            stats.secondaryAverage! <= goal.secondaryMax!;
        statusBody =
            'Average ${stats.average!.toInt()}/${stats.secondaryAverage!.toInt()}, goal ≤${goal.primaryMax!.toInt()}/${goal.secondaryMax!.toInt()}.';
      } else if (goal.primaryMax != null && goal.primaryMin != null) {
        atGoal = stats.average! >= goal.primaryMin! &&
            stats.average! <= goal.primaryMax!;
        statusBody =
            'Average ${stats.average!.toStringAsFixed(1)}, goal ${goal.primaryMin!.toStringAsFixed(0)}-${goal.primaryMax!.toStringAsFixed(0)} ${t.unit}.';
      } else if (goal.primaryMax != null) {
        atGoal = stats.average! <= goal.primaryMax!;
        statusBody =
            'Average ${stats.average!.toStringAsFixed(1)}, goal ≤${goal.primaryMax!.toStringAsFixed(0)} ${t.unit}.';
      } else if (goal.primaryMin != null) {
        atGoal = stats.average! >= goal.primaryMin!;
        statusBody =
            'Average ${stats.average!.toStringAsFixed(1)}%, goal ≥${goal.primaryMin!.toStringAsFixed(0)}%.';
      } else if (goal.target != null && t == VitalType.weight) {
        final diff = (stats.average! - goal.target!).abs();
        atGoal = diff <= 2;
        statusBody =
            'Current ${stats.average!.toStringAsFixed(1)} lbs, target ${goal.target!.toStringAsFixed(1)} lbs.';
      } else {
        continue;
      }

      if (atGoal) {
        out.add(Insight(
          title: '${t.label}: At goal',
          body: 'Keep it up! $statusBody',
          severity: InsightSeverity.info,
          icon: Icons.flag_rounded,
          relatedVital: t,
        ));
      }
    }
    return out;
  }

  String _formatDateShort(DateTime d) {
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec'
    ];
    return '${months[d.month - 1]} ${d.day}';
  }

  String _formatDate(DateTime d) {
    final now = DateTime.now();
    final diff = now.difference(d);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    return _formatDateShort(d);
  }

  String _formatDateTime(DateTime d) {
    final hour = d.hour == 0
        ? 12
        : d.hour > 12
            ? d.hour - 12
            : d.hour;
    final period = d.hour >= 12 ? 'PM' : 'AM';
    final minute = d.minute.toString().padLeft(2, '0');
    return '${_formatDateShort(d)}, $hour:$minute $period';
  }

  // ─── Responsive config ────────────────────────────────────────────────────
  ResponsiveConfig _config(BoxConstraints c) {
    final w = c.maxWidth;
    final h = c.maxHeight;
    final isTwoColumn = w > 800 && w / h > 0.9;
    return ResponsiveConfig(
      paddingH: w < 400 ? 16 : 20,
      paddingV: 16,
      contentMax: isTwoColumn ? 1100 : 720,
      gridColumns: w < 400 ? 1 : (w < 700 ? 2 : 3),
      cardHeight: 120,
      iconSize: 24,
      fontSize: 14,
      wideMode: w > 700,
      hasHinge: false,
      useTwoColumnLayout: isTwoColumn,
    );
  }

  /// Placeholder referenced by _generateInsights — real impl in part 6
  void _promptHeight() {
    _showHeightDialog();
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

  Future<T?> _showNavyDialog<T>({
    required Widget child,
    EdgeInsets insetPadding = const EdgeInsets.symmetric(horizontal: 28),
  }) {
    return showDialog<T>(
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

  Future<T?> _showNavyBottomSheet<T>({
    required Widget child,
    double? heightFactor,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withOpacity(0.5),
      isScrollControlled: true,
      // Rises with the keyboard so the Save button is never hidden under it.
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
    bool expand = false,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: loading ? null : onTap,
        child: Container(
          width: expand ? double.infinity : null,
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
    bool expand = false,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: onTap,
        child: Container(
          width: expand ? double.infinity : null,
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

  Widget _severityBadge(InsightSeverity s) {
    final color = _Jovi.severityColor(s);
    final label = s == InsightSeverity.urgent
        ? 'URGENT'
        : s == InsightSeverity.concern
            ? 'CONCERN'
            : s == InsightSeverity.watch
                ? 'WATCH'
                : 'INFO';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withOpacity(0.18),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withOpacity(0.45), width: 1),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: 9.5,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.8,
        ),
      ),
    );
  }

  Widget _timeRangePill(String label, String value) {
    final sel = _timeRange == value;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _timeRange = value);
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.symmetric(horizontal: 3),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          gradient: sel ? _Jovi.coralGradient : null,
          color: sel ? null : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(100),
          border: Border.all(
            color: sel ? Colors.transparent : Colors.white.withOpacity(0.12),
            width: 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: Colors.white,
            fontSize: 11.5,
            fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ),
    );
  }

  /// Converts switch expression (Dart 3) result for severity label
  /// Separated out just in case — but modern FlutterFlow runs Dart 3.

  // ═══════════════════════════════════════════════════════════════════════════
  // DASHBOARD TAB
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildDashboardTab(ResponsiveConfig cfg) {
    // Crisis check — scan most recent reading per type
    final crises = <List<dynamic>>[];
    for (final t in VitalType.values) {
      final latest = _latestOf(t);
      if (latest == null) continue;
      final c = _ClinicalRefs.checkCrisis(latest);
      if (c != null) crises.add([t, latest, c[0], c[1]]);
    }

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 90),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Crisis banner
          if (crises.isNotEmpty) ...[
            _buildCrisisBanner(crises),
            const SizedBox(height: 14),
          ],
          // Time range selector
          _glassCard(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            radius: 100,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              child: Row(
                children: [
                  _timeRangePill('7 Days', '7d'),
                  _timeRangePill('30 Days', '30d'),
                  _timeRangePill('90 Days', '90d'),
                  _timeRangePill('All Time', 'all'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          _buildSummaryStrip(cfg),
          const SizedBox(height: 14),
          _sectionHeader('Vital Signs', icon: Icons.favorite_rounded),
          ...VitalType.values.map((t) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _buildVitalCard(t),
              )),
          const SizedBox(height: 8),
          _buildQuickAddRow(),
        ],
      ),
    );
  }

  // ─── Crisis Banner ───────────────────────────────────────────────────────

  Widget _buildCrisisBanner(List<List<dynamic>> crises) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                _Jovi.errorRed.withOpacity(0.34),
                _Jovi.errorRed.withOpacity(0.2),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: _Jovi.errorRed.withOpacity(0.6),
              width: 1.5,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  ScaleTransition(
                    scale: _pulseAnimation,
                    child: Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [_Jovi.errorRed, Color(0xFFB71C1C)],
                        ),
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: [
                          BoxShadow(
                            color: _Jovi.errorRed.withOpacity(0.6),
                            blurRadius: 16,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: const Icon(Icons.warning_rounded,
                          color: Colors.white, size: 22),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      crises.length == 1
                          ? (crises[0][2] as String)
                          : '${crises.length} urgent findings',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.2),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              for (final c in crises) ...[
                const SizedBox(height: 6),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.circle, color: _Jovi.softRed, size: 6),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        c[3] as String,
                        style: const TextStyle(
                            color: Colors.white, fontSize: 12.5, height: 1.45),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: _primaryButton(
                      label: 'Call 911',
                      icon: Icons.phone_rounded,
                      onTap: () async {
                        HapticFeedback.heavyImpact();
                        // Hands off to the phone's dialer. The OS still asks
                        // the user to confirm before the call is placed.
                        final ok = await _dial('911');
                        if (!ok) {
                          _showSnack('Could not open the dialer. Call 911.',
                              isError: true);
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _secondaryButton(
                      label: 'Log Symptoms',
                      icon: Icons.edit_note_rounded,
                      onTap: () {
                        // Jump to log with current context
                        setState(() => _tab = _Tab.log);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.info_outline_rounded,
                        color: Colors.white.withOpacity(0.75), size: 12),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Readings can be inaccurate. Retake before acting. This is not medical advice.',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.85),
                          fontSize: 10.5,
                          fontStyle: FontStyle.italic,
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
      ),
    );
  }

  // ─── Summary Strip (total readings, latest activity) ─────────────────────

  Widget _buildSummaryStrip(ResponsiveConfig cfg) {
    final countInRange =
        _allReadings.where((r) => r.timestamp.isAfter(_rangeCutoff())).length;
    final vitalsTracked =
        VitalType.values.where((t) => _readingsInRange(t).isNotEmpty).length;
    // Streak: consecutive days with at least one reading, counting back from
    // today. If today is empty but yesterday has a reading, the streak is
    // measured from yesterday (user hasn't logged today yet — give them grace).
    final dayKeys = <String>{};
    for (final r in _allReadings) {
      dayKeys
          .add('${r.timestamp.year}-${r.timestamp.month}-${r.timestamp.day}');
    }
    int streak = 0;
    final now = DateTime.now();
    DateTime cursor = DateTime(now.year, now.month, now.day);
    // If today has no reading, roll back one day as a grace period before counting
    final todayKey = '${cursor.year}-${cursor.month}-${cursor.day}';
    if (!dayKeys.contains(todayKey)) {
      cursor = cursor.subtract(const Duration(days: 1));
    }
    while (true) {
      final key = '${cursor.year}-${cursor.month}-${cursor.day}';
      if (dayKeys.contains(key)) {
        streak++;
        cursor = cursor.subtract(const Duration(days: 1));
      } else {
        break;
      }
    }

    return Row(
      children: [
        Expanded(
          child: _buildStatPill(
            label: 'Readings',
            value: countInRange.toString(),
            icon: Icons.assessment_rounded,
            accent: _Jovi.coral,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _buildStatPill(
            label: 'Vitals',
            value: '$vitalsTracked/${VitalType.values.length}',
            icon: Icons.favorite_rounded,
            accent: _Jovi.sky,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: _buildStatPill(
            label: streak == 1 ? 'Day Streak' : 'Day Streak',
            value: streak.toString(),
            icon: Icons.local_fire_department_rounded,
            accent: streak > 0 ? _Jovi.gold : Colors.white.withOpacity(0.4),
          ),
        ),
      ],
    );
  }

  Widget _buildStatPill({
    required String label,
    required String value,
    required IconData icon,
    required Color accent,
  }) {
    return _glassCard(
      padding: const EdgeInsets.all(12),
      radius: 14,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: accent, size: 14),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  label.toUpperCase(),
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.5,
            ),
          ),
        ],
      ),
    );
  }

  // ─── Vital Card with sparkline ───────────────────────────────────────────

  Widget _buildVitalCard(VitalType t) {
    final latest = _latestOf(t);
    final readings = _readingsInRange(t);
    final vColor = _Jovi.vitalColor(t);
    final stats = _computeStats(readings);

    // Determine status color
    Color statusColor = Colors.white.withOpacity(0.7);
    String? statusLabel;
    if (latest != null) {
      final crisis = _ClinicalRefs.checkCrisis(latest);
      if (crisis != null) {
        statusColor = _Jovi.errorRed;
        statusLabel = 'URGENT';
      } else if (t == VitalType.bloodPressure &&
          latest.value != null &&
          latest.secondary != null) {
        final stage =
            _ClinicalRefs.classifyBP(latest.value!, latest.secondary!);
        statusLabel = stage.label;
        statusColor = stage == BPStage.normal
            ? _Jovi.mint
            : stage == BPStage.elevated
                ? _Jovi.gold
                : stage == BPStage.stage1
                    ? _Jovi.coral
                    : _Jovi.errorRed;
      } else {
        // Use goal-based classification
        final goal = _goals[t];
        if (goal != null && latest.value != null) {
          if (goal.primaryMax != null && latest.value! > goal.primaryMax!) {
            statusColor = _Jovi.coral;
            statusLabel = 'Above goal';
          } else if (goal.primaryMin != null &&
              latest.value! < goal.primaryMin!) {
            statusColor = _Jovi.gold;
            statusLabel = 'Below goal';
          } else {
            statusColor = _Jovi.mint;
            statusLabel = 'At goal';
          }
        }
      }
    }

    return _Pressable(
      onTap: () {
        setState(() {
          _selectedVital = t;
          _tab = _Tab.trends;
        });
        HapticFeedback.selectionClick();
      },
      child: _glassCard(
        padding: const EdgeInsets.all(14),
        radius: 16,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: vColor.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(12),
                    border:
                        Border.all(color: vColor.withOpacity(0.4), width: 1),
                  ),
                  child: Icon(_vitalIcon(t), color: vColor, size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        t.label,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 2),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.baseline,
                        textBaseline: TextBaseline.alphabetic,
                        children: [
                          Text(
                            latest?.displayValue ?? '--',
                            style: TextStyle(
                                color: statusColor,
                                fontSize: 24,
                                fontWeight: FontWeight.w800,
                                letterSpacing: -0.5),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            t.unit,
                            style: TextStyle(
                                color: Colors.white.withOpacity(0.6),
                                fontSize: 11.5,
                                fontWeight: FontWeight.w500),
                          ),
                          const SizedBox(width: 6),
                          if (stats.trend != null && stats.trend!.abs() > 0.1)
                            Icon(
                              stats.trend! > 0
                                  ? Icons.trending_up_rounded
                                  : Icons.trending_down_rounded,
                              color:
                                  stats.trend! > 0 ? _Jovi.coral : _Jovi.mint,
                              size: 15,
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
                // Add button
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(10),
                    onTap: () {
                      HapticFeedback.lightImpact();
                      _openAddReadingSheet(t);
                    },
                    child: Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        gradient: _Jovi.coralGradient,
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: [
                          BoxShadow(
                            color: _Jovi.coral.withOpacity(0.35),
                            blurRadius: 10,
                            offset: const Offset(0, 3),
                          ),
                        ],
                      ),
                      child: const Icon(Icons.add_rounded,
                          color: Colors.white, size: 18),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            // Sparkline row
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: 32,
                    child: readings.length < 2
                        ? _buildSparklineEmpty()
                        : CustomPaint(
                            size: Size.infinite,
                            painter: _SparklinePainter(
                              readings: readings.reversed.toList(),
                              color: vColor,
                              secondaryColor: t == VitalType.bloodPressure
                                  ? _Jovi.sky
                                  : null,
                            ),
                          ),
                  ),
                ),
                const SizedBox(width: 10),
                if (latest != null)
                  Text(
                    _formatDate(latest.timestamp),
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.55),
                      fontSize: 10.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
              ],
            ),
            if (statusLabel != null) ...[
              const SizedBox(height: 10),
              Row(
                children: [
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.18),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                          color: statusColor.withOpacity(0.4), width: 1),
                    ),
                    child: Text(
                      statusLabel.toUpperCase(),
                      style: TextStyle(
                        color: statusColor,
                        fontSize: 9.5,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.6,
                      ),
                    ),
                  ),
                  const Spacer(),
                  if (stats.average != null)
                    Text(
                      'avg ${_formatStatValue(t, stats.average!, stats.secondaryAverage)}',
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.55),
                        fontSize: 10.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _formatStatValue(VitalType t, double primary, double? secondary) {
    if (t == VitalType.bloodPressure && secondary != null) {
      return '${primary.toInt()}/${secondary.toInt()}';
    }
    if (t == VitalType.weight || t == VitalType.temperature) {
      return primary.toStringAsFixed(1);
    }
    return primary.toInt().toString();
  }

  IconData _vitalIcon(VitalType t) {
    switch (t) {
      case VitalType.bloodPressure:
        return Icons.favorite_rounded;
      case VitalType.heartRate:
        return Icons.monitor_heart_rounded;
      case VitalType.bloodGlucose:
        return Icons.water_drop_rounded;
      case VitalType.weight:
        return Icons.monitor_weight_rounded;
      case VitalType.oxygen:
        return Icons.air_rounded;
      case VitalType.temperature:
        return Icons.thermostat_rounded;
    }
  }

  Widget _buildSparklineEmpty() {
    return Center(
      child: Text(
        'No data yet',
        style: TextStyle(
          color: Colors.white.withOpacity(0.4),
          fontSize: 10.5,
          fontStyle: FontStyle.italic,
        ),
      ),
    );
  }

  Widget _buildQuickAddRow() {
    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _coralGradientIcon(Icons.bolt_rounded, size: 16),
              const SizedBox(width: 8),
              const Text(
                'QUICK ADD',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _quickAddButton(
                    VitalType.bloodPressure, Icons.favorite_rounded),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _quickAddButton(
                    VitalType.bloodGlucose, Icons.water_drop_rounded),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _quickAddButton(
                    VitalType.weight, Icons.monitor_weight_rounded),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _quickAddButton(VitalType t, IconData icon) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          HapticFeedback.lightImpact();
          _openAddReadingSheet(t);
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(
            color: _Jovi.vitalColor(t).withOpacity(0.12),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _Jovi.vitalColor(t).withOpacity(0.3),
              width: 1,
            ),
          ),
          child: Column(
            children: [
              Icon(icon, color: _Jovi.vitalColor(t), size: 18),
              const SizedBox(height: 4),
              Text(
                t == VitalType.bloodPressure
                    ? 'BP'
                    : t == VitalType.bloodGlucose
                        ? 'Glucose'
                        : 'Weight',
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // TRENDS TAB — Interactive Chart
  // ═══════════════════════════════════════════════════════════════════════════

  // Chart interaction state (ephemeral, not persisted)
  double? _chartCursorX; // user-dragged crosshair position (normalized 0-1)
  double _chartScale = 1.0;
  double _chartPanOffset = 0.0; // normalized 0-1 pan offset

  Widget _buildTrendsTab(ResponsiveConfig cfg) {
    final readings = _readingsInRange(_selectedVital);

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 90),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Vital selector
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              children:
                  VitalType.values.map((t) => _buildVitalChip(t)).toList(),
            ),
          ),
          const SizedBox(height: 12),
          // Time range
          _glassCard(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            radius: 100,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              child: Row(
                children: [
                  _timeRangePill('7D', '7d'),
                  _timeRangePill('30D', '30d'),
                  _timeRangePill('90D', '90d'),
                  _timeRangePill('All', 'all'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          // Stats summary
          _buildTrendStats(readings),
          const SizedBox(height: 14),
          // The chart
          _buildInteractiveChart(readings),
          const SizedBox(height: 14),
          // Annotations list (medication changes within range)
          _buildMedicationTimeline(),
          const SizedBox(height: 12),
          // Export buttons
          _primaryButton(
            label: 'Generate Doctor Report',
            icon: Icons.description_rounded,
            expand: true,
            onTap: _openDoctorReport,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _secondaryButton(
                  label: 'Quick Copy',
                  icon: Icons.copy_rounded,
                  onTap: _copyTrendReport,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _secondaryButton(
                  label: 'Export CSV',
                  icon: Icons.download_rounded,
                  onTap: _exportCSV,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildVitalChip(VitalType t) {
    final sel = _selectedVital == t;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() {
          _selectedVital = t;
          _chartCursorX = null;
          _chartScale = 1.0;
          _chartPanOffset = 0.0;
        });
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: sel
              ? _Jovi.vitalColor(t).withOpacity(0.25)
              : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(100),
          border: Border.all(
            color: sel ? _Jovi.vitalColor(t) : Colors.white.withOpacity(0.12),
            width: sel ? 1.5 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(_vitalIcon(t),
                color:
                    sel ? _Jovi.vitalColor(t) : Colors.white.withOpacity(0.75),
                size: 14),
            const SizedBox(width: 6),
            Text(
              t.label,
              style: TextStyle(
                color: Colors.white,
                fontSize: 11.5,
                fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTrendStats(List<VitalReading> readings) {
    final stats = _computeStats(readings);
    final t = _selectedVital;

    Widget stat(String label, String? value, {Color? color}) {
      return Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label.toUpperCase(),
              style: TextStyle(
                color: Colors.white.withOpacity(0.55),
                fontSize: 9.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.8,
              ),
            ),
            const SizedBox(height: 3),
            Text(
              value ?? '--',
              style: TextStyle(
                color: color ?? Colors.white,
                fontSize: 15,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.3,
              ),
            ),
          ],
        ),
      );
    }

    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 16,
      child: Row(
        children: [
          stat(
            'Avg',
            stats.average != null
                ? _formatStatValue(t, stats.average!, stats.secondaryAverage)
                : null,
            color: _Jovi.vitalColor(t),
          ),
          Container(
            height: 28,
            width: 1,
            color: Colors.white.withOpacity(0.1),
            margin: const EdgeInsets.symmetric(horizontal: 8),
          ),
          stat(
            'Low',
            stats.min != null
                ? (t == VitalType.weight || t == VitalType.temperature
                    ? stats.min!.toStringAsFixed(1)
                    : stats.min!.toInt().toString())
                : null,
            color: _Jovi.mint,
          ),
          Container(
            height: 28,
            width: 1,
            color: Colors.white.withOpacity(0.1),
            margin: const EdgeInsets.symmetric(horizontal: 8),
          ),
          stat(
            'High',
            stats.max != null
                ? (t == VitalType.weight || t == VitalType.temperature
                    ? stats.max!.toStringAsFixed(1)
                    : stats.max!.toInt().toString())
                : null,
            color: _Jovi.softRed,
          ),
          Container(
            height: 28,
            width: 1,
            color: Colors.white.withOpacity(0.1),
            margin: const EdgeInsets.symmetric(horizontal: 8),
          ),
          stat('N', stats.count.toString()),
        ],
      ),
    );
  }

  Widget _buildInteractiveChart(List<VitalReading> readings) {
    if (readings.isEmpty) {
      return _glassCard(
        padding: const EdgeInsets.all(20),
        radius: 18,
        child: _emptyState(
          icon: Icons.show_chart_rounded,
          title: 'No data for ${_timeRangeLabel()}',
          subtitle:
              'Add ${_selectedVital.label.toLowerCase()} readings to see trends over time.',
          action: _primaryButton(
            label: 'Add Reading',
            icon: Icons.add_rounded,
            onTap: () => _openAddReadingSheet(_selectedVital),
          ),
        ),
      );
    }

    // Sort oldest to newest for chart
    final sorted = [...readings]
      ..sort((a, b) => a.timestamp.compareTo(b.timestamp));

    // Build medication annotations within range
    final annotations = <ChartAnnotation>[];
    for (final med in _medications) {
      if (med.startDate == null) continue;
      final affected = _ClinicalRefs.affectedVitals(med.name);
      final vk = _vitalKey(_selectedVital);
      if (!affected.contains(vk)) continue;
      if (sorted.isNotEmpty &&
          med.startDate!.isAfter(sorted.first.timestamp) &&
          med.startDate!
              .isBefore(sorted.last.timestamp.add(const Duration(hours: 1)))) {
        annotations.add(ChartAnnotation(
          timestamp: med.startDate!,
          label: 'Started ${med.name}',
          color: _Jovi.coral,
        ));
      }
    }

    // Goal lines
    final goal = _goals[_selectedVital];
    final goalLines = <double>[];
    final goalLineColors = <Color>[];
    if (goal != null) {
      if (goal.primaryMax != null) {
        goalLines.add(goal.primaryMax!);
        goalLineColors.add(_Jovi.coral);
      }
      if (goal.primaryMin != null) {
        goalLines.add(goal.primaryMin!);
        goalLineColors.add(_Jovi.mint);
      }
      if (goal.secondaryMax != null) {
        goalLines.add(goal.secondaryMax!);
        goalLineColors.add(_Jovi.sky);
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
              _coralGradientIcon(Icons.insights_rounded, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${_selectedVital.label.toUpperCase()} TREND',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.1),
                ),
              ),
              if (_chartScale > 1.01 || _chartPanOffset.abs() > 0.01)
                _Pressable(
                  onTap: () {
                    HapticFeedback.lightImpact();
                    setState(() {
                      _chartScale = 1.0;
                      _chartPanOffset = 0.0;
                      _chartCursorX = null;
                    });
                  },
                  child: _glassPill(
                    tint: _Jovi.coral,
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.refresh_rounded,
                            color: _Jovi.coral, size: 11),
                        const SizedBox(width: 4),
                        Text(
                          'Reset',
                          style: TextStyle(
                            color: _Jovi.coral,
                            fontSize: 10.5,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          // THE CHART
          // Gesture handling (single GestureDetector, no conflicting handlers):
          //   • Long-press + drag  → crosshair inspection
          //   • Two-finger pinch   → zoom (1x-8x)
          //   • One-finger drag    → pan (ONLY when zoomed > 1x; at 1x we
          //     ignore single-finger drags so the parent scroll view wins)
          LayoutBuilder(
            builder: (context, constraints) {
              return SizedBox(
                height: 240,
                child: GestureDetector(
                  behavior: HitTestBehavior.opaque,
                  onScaleStart: (details) {
                    if (details.pointerCount >= 2) {
                      HapticFeedback.selectionClick();
                    }
                  },
                  onScaleUpdate: (details) {
                    // Pinch zoom on 2+ fingers with actual scale change
                    final isPinching =
                        details.pointerCount >= 2 && details.scale != 1.0;
                    // Pan only when already zoomed (otherwise let parent scroll)
                    final isPanning =
                        _chartScale > 1.01 && details.focalPointDelta.dx != 0;
                    if (!isPinching && !isPanning) return;

                    setState(() {
                      if (isPinching) {
                        _chartScale =
                            (_chartScale * details.scale).clamp(1.0, 8.0);
                      }
                      if (isPanning) {
                        final deltaNormalized = details.focalPointDelta.dx /
                            constraints.maxWidth /
                            _chartScale;
                        final maxPan = (1.0 - 1.0 / _chartScale) / 2;
                        _chartPanOffset = (_chartPanOffset + deltaNormalized)
                            .clamp(-maxPan, maxPan);
                      }
                    });
                  },
                  onLongPressStart: (details) {
                    HapticFeedback.lightImpact();
                    setState(() {
                      _chartCursorX =
                          (details.localPosition.dx / constraints.maxWidth)
                              .clamp(0.0, 1.0);
                    });
                  },
                  onLongPressMoveUpdate: (details) {
                    setState(() {
                      _chartCursorX =
                          (details.localPosition.dx / constraints.maxWidth)
                              .clamp(0.0, 1.0);
                    });
                  },
                  onLongPressEnd: (details) {
                    setState(() => _chartCursorX = null);
                  },
                  child: CustomPaint(
                    size: Size.infinite,
                    painter: _InteractiveChartPainter(
                      readings: sorted,
                      vitalType: _selectedVital,
                      primaryColor: _Jovi.vitalColor(_selectedVital),
                      secondaryColor: _selectedVital == VitalType.bloodPressure
                          ? _Jovi.sky
                          : null,
                      cursorX: _chartCursorX,
                      scale: _chartScale,
                      panOffset: _chartPanOffset,
                      goalLines: goalLines,
                      goalLineColors: goalLineColors,
                      annotations: annotations,
                    ),
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 10),
          // Legend / tip
          Row(
            children: [
              Icon(Icons.touch_app_rounded,
                  color: Colors.white.withOpacity(0.5), size: 12),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  'Long-press to inspect • Pinch to zoom • Drag to pan when zoomed',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.5),
                    fontSize: 10.5,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          if (_selectedVital == VitalType.bloodPressure) ...[
            const SizedBox(height: 6),
            Row(
              children: [
                _legendSwatch(
                    _Jovi.vitalColor(VitalType.bloodPressure), 'Systolic'),
                const SizedBox(width: 14),
                _legendSwatch(_Jovi.sky, 'Diastolic'),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _legendSwatch(Color color, String label) {
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
        const SizedBox(width: 6),
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.7),
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  String _vitalKey(VitalType t) {
    switch (t) {
      case VitalType.bloodPressure:
        return 'bp';
      case VitalType.bloodGlucose:
        return 'glucose';
      case VitalType.heartRate:
        return 'hr';
      case VitalType.weight:
        return 'weight';
      default:
        return t.key;
    }
  }

  Widget _buildMedicationTimeline() {
    final relevantMeds = _medications.where((m) {
      if (m.startDate == null) return false;
      final affected = _ClinicalRefs.affectedVitals(m.name);
      return affected.contains(_vitalKey(_selectedVital));
    }).toList();

    if (relevantMeds.isEmpty) return const SizedBox.shrink();

    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 16,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _coralGradientIcon(Icons.medication_rounded, size: 16),
              const SizedBox(width: 8),
              const Text(
                'MEDICATIONS AFFECTING THIS VITAL',
                style: TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.1),
              ),
            ],
          ),
          const SizedBox(height: 10),
          ...relevantMeds.map((m) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: _Jovi.coral,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: _Jovi.coral.withOpacity(0.5),
                            blurRadius: 6,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            m.name,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 1),
                          Text(
                            _ClinicalRefs.medEffect(m.name, _selectedVital) ??
                                'Affects ${_selectedVital.label.toLowerCase()}',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.65),
                              fontSize: 11,
                              height: 1.3,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          'Started ${_formatDateShort(m.startDate!)}',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.5),
                            fontSize: 10.5,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        if (m.stopDate != null)
                          Text(
                            'Stopped ${_formatDateShort(m.stopDate!)}',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.45),
                              fontSize: 10,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }

  void _copyTrendReport() {
    final readings = _readingsInRange(_selectedVital);
    final stats = _computeStats(readings);
    final sb = StringBuffer();
    sb.writeln('${_selectedVital.label} Report — Jovi Health');
    sb.writeln('Generated: ${DateTime.now().toString().split('.').first}');
    sb.writeln('Range: Last ${_timeRangeLabel()}');
    sb.writeln();
    sb.writeln('SUMMARY:');
    sb.writeln('  Readings: ${stats.count}');
    if (stats.average != null) {
      sb.writeln(
          '  Average: ${_formatStatValue(_selectedVital, stats.average!, stats.secondaryAverage)} ${_selectedVital.unit}');
    }
    if (stats.min != null) {
      sb.writeln(
          '  Low: ${_selectedVital == VitalType.weight ? stats.min!.toStringAsFixed(1) : stats.min!.toInt()} ${_selectedVital.unit}');
    }
    if (stats.max != null) {
      sb.writeln(
          '  High: ${_selectedVital == VitalType.weight ? stats.max!.toStringAsFixed(1) : stats.max!.toInt()} ${_selectedVital.unit}');
    }
    if (stats.stdDev != null) {
      sb.writeln('  Std deviation: ${stats.stdDev!.toStringAsFixed(1)}');
    }

    sb.writeln();
    sb.writeln('INDIVIDUAL READINGS (most recent first):');
    for (final r in readings) {
      sb.write(
          '  ${_formatDateTime(r.timestamp)}: ${r.displayValue} ${_selectedVital.unit}');
      if (r.context != null) sb.write(' [${r.context}]');
      if (r.location != null) sb.write(' @${r.location}');
      if (r.notes != null && r.notes!.isNotEmpty) sb.write(' — ${r.notes}');
      sb.writeln();
    }

    Clipboard.setData(ClipboardData(text: sb.toString()));
    HapticFeedback.lightImpact();
    _showSnack('Report copied to clipboard');
  }

  void _exportCSV() {
    final readings = _readingsInRange(_selectedVital);
    final sb = StringBuffer();
    sb.writeln('Date,Time,Value,Unit,Context,Location,Source,Notes');
    for (final r in readings) {
      final date =
          '${r.timestamp.year}-${r.timestamp.month.toString().padLeft(2, "0")}-${r.timestamp.day.toString().padLeft(2, "0")}';
      final time =
          '${r.timestamp.hour.toString().padLeft(2, "0")}:${r.timestamp.minute.toString().padLeft(2, "0")}';
      sb.write('$date,$time,');
      if (_selectedVital == VitalType.bloodPressure) {
        sb.write('"${r.value?.toInt() ?? ""}/${r.secondary?.toInt() ?? ""}"');
      } else {
        sb.write('${r.value ?? ""}');
      }
      sb.write(',${_selectedVital.unit}');
      sb.write(',${r.context ?? ""}');
      sb.write(',${r.location ?? ""}');
      sb.write(',${r.source}');
      final safeNotes = (r.notes ?? '').replaceAll('"', '""');
      sb.write(',"$safeNotes"');
      sb.writeln();
    }

    Clipboard.setData(ClipboardData(text: sb.toString()));
    HapticFeedback.lightImpact();
    _showSnack('CSV copied to clipboard — paste into Numbers or Excel');
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // DOCTOR REPORT — Full cross-vital report suitable for clinic visits.
  //
  // Produces a formatted plaintext report that covers ALL vitals in the
  // selected time range, classification & stats per vital, medications
  // (including stop dates), active insights, and individual readings.
  //
  // Renders to a scrollable preview sheet with actions:
  //   • Copy all (to clipboard as monospace text)
  //   • Share sheet (delegates to platform via copy + snackbar hint)
  // The report structure is designed to paste cleanly into email, Google
  // Docs, or the iOS Notes app where it can be printed to PDF natively.
  // ═══════════════════════════════════════════════════════════════════════════

  String _generateDoctorReport() {
    final sb = StringBuffer();
    final now = DateTime.now();
    final rangeLabel = _timeRangeLabel();

    // ─── HEADER ────────────────────────────────────────────────────────────
    sb.writeln('═══════════════════════════════════════════════════════════');
    sb.writeln('  VITAL SIGNS REPORT');
    sb.writeln('  Generated via Jovi Health');
    sb.writeln('═══════════════════════════════════════════════════════════');
    sb.writeln();
    sb.writeln('Report date: ${_formatDateTime(now)}');
    sb.writeln('Period covered: Last $rangeLabel');
    if (_userHeightInches != null) {
      final feet = (_userHeightInches! / 12).floor();
      final inches = (_userHeightInches! % 12).round();
      sb.writeln('Height on file: $feet\' $inches"');
    }
    sb.writeln();

    // ─── ACTIVE INSIGHTS ───────────────────────────────────────────────────
    final insights = _generateInsights();
    if (insights.isNotEmpty) {
      sb.writeln('───────────────────────────────────────────────────────────');
      sb.writeln('  CLINICAL OBSERVATIONS');
      sb.writeln('───────────────────────────────────────────────────────────');
      sb.writeln();
      for (final i in insights) {
        final sevLabel = i.severity == InsightSeverity.urgent
            ? '[URGENT]'
            : i.severity == InsightSeverity.concern
                ? '[CONCERN]'
                : i.severity == InsightSeverity.watch
                    ? '[WATCH]'
                    : '[INFO]';
        sb.writeln('$sevLabel ${i.title}');
        sb.writeln('  ${i.body}');
        sb.writeln();
      }
    }

    // ─── PER-VITAL SUMMARY ─────────────────────────────────────────────────
    sb.writeln('───────────────────────────────────────────────────────────');
    sb.writeln('  VITAL SUMMARIES');
    sb.writeln('───────────────────────────────────────────────────────────');
    sb.writeln();

    for (final t in VitalType.values) {
      final readings = _readingsInRange(t);
      if (readings.isEmpty) continue;
      final stats = _computeStats(readings);
      sb.writeln('◆ ${t.label.toUpperCase()} (${t.unit})');

      if (stats.average != null) {
        if (t == VitalType.bloodPressure && stats.secondaryAverage != null) {
          final stage =
              _ClinicalRefs.classifyBP(stats.average!, stats.secondaryAverage!);
          sb.writeln(
              '  Average: ${stats.average!.toInt()}/${stats.secondaryAverage!.toInt()} — ${stage.label}');
        } else if (t == VitalType.weight) {
          sb.writeln('  Average: ${stats.average!.toStringAsFixed(1)}');
          if (_userHeightInches != null) {
            final bmi =
                _ClinicalRefs.calculateBMI(stats.average!, _userHeightInches);
            if (bmi != null) {
              sb.writeln(
                  '  BMI: ${bmi.toStringAsFixed(1)} — ${_ClinicalRefs.interpretBMI(bmi)}');
            }
          }
        } else if (t == VitalType.temperature) {
          sb.writeln('  Average: ${stats.average!.toStringAsFixed(1)}');
        } else {
          sb.writeln('  Average: ${stats.average!.toInt()}');
        }

        if (stats.min != null && stats.max != null) {
          final minStr = t == VitalType.weight || t == VitalType.temperature
              ? stats.min!.toStringAsFixed(1)
              : stats.min!.toInt().toString();
          final maxStr = t == VitalType.weight || t == VitalType.temperature
              ? stats.max!.toStringAsFixed(1)
              : stats.max!.toInt().toString();
          sb.writeln('  Range: $minStr to $maxStr');
        }
        if (stats.stdDev != null) {
          sb.writeln('  Std deviation: ${stats.stdDev!.toStringAsFixed(1)}');
        }
        sb.writeln('  Readings: ${stats.count}');
        if (stats.trend != null && stats.trend!.abs() > 0.1) {
          final totalChange = stats.trend! * _rangeDays();
          sb.writeln(
              '  Trend: ${totalChange >= 0 ? "+" : ""}${totalChange.toStringAsFixed(1)} over period');
        }
      }

      // A1C for glucose
      if (t == VitalType.bloodGlucose && readings.length >= 10) {
        final values = readings
            .where((r) => r.value != null)
            .map((r) => r.value!)
            .toList();
        final a1c = _ClinicalRefs.estimateA1C(values);
        if (a1c != null) {
          sb.writeln(
              '  Estimated A1C: ${a1c.toStringAsFixed(1)}% — ${_ClinicalRefs.interpretA1C(a1c)}');
          sb.writeln('  (Estimated from glucose average via ADAG formula)');
        }
      }
      sb.writeln();
    }

    // ─── MEDICATIONS ───────────────────────────────────────────────────────
    if (_medications.isNotEmpty) {
      sb.writeln('───────────────────────────────────────────────────────────');
      sb.writeln('  MEDICATIONS ON FILE');
      sb.writeln('───────────────────────────────────────────────────────────');
      sb.writeln();
      for (final m in _medications) {
        sb.write('• ${m.name}');
        if (m.strength.isNotEmpty) sb.write(' ${m.strength}');
        if (m.dosage.isNotEmpty) sb.write(' — ${m.dosage}');
        sb.writeln();
        if (m.condition != null && m.condition!.isNotEmpty) {
          sb.writeln('    For: ${m.condition}');
        }
        if (m.startDate != null) {
          sb.write('    Started ${_formatDateShort(m.startDate!)}');
          if (m.stopDate != null) {
            sb.write(' · Stopped ${_formatDateShort(m.stopDate!)}');
          } else {
            sb.write(' · Active');
          }
          sb.writeln();
        }
        final affectedKeys = _ClinicalRefs.affectedVitals(m.name);
        if (affectedKeys.isNotEmpty) {
          final affectedLabels = <String>[];
          for (final k in affectedKeys) {
            if (k == 'bp') affectedLabels.add('BP');
            if (k == 'glucose') affectedLabels.add('glucose');
            if (k == 'hr') affectedLabels.add('heart rate');
            if (k == 'weight') affectedLabels.add('weight');
          }
          sb.writeln('    Known to affect: ${affectedLabels.join(", ")}');
        }
      }
      sb.writeln();
    }

    // ─── GOALS ─────────────────────────────────────────────────────────────
    final activeGoals = _goals.entries
        .where((e) =>
            e.value.primaryMax != null ||
            e.value.primaryMin != null ||
            e.value.secondaryMax != null ||
            e.value.target != null)
        .toList();
    if (activeGoals.isNotEmpty) {
      sb.writeln('───────────────────────────────────────────────────────────');
      sb.writeln('  GOALS');
      sb.writeln('───────────────────────────────────────────────────────────');
      sb.writeln();
      for (final entry in activeGoals) {
        sb.writeln(
            '• ${entry.key.label}: ${_goalSummary(entry.key, entry.value)}');
      }
      sb.writeln();
    }

    // ─── INDIVIDUAL READINGS (for selected vital) ──────────────────────────
    final selectedReadings = _readingsInRange(_selectedVital);
    if (selectedReadings.isNotEmpty) {
      sb.writeln('───────────────────────────────────────────────────────────');
      sb.writeln(
          '  ${_selectedVital.label.toUpperCase()} — INDIVIDUAL READINGS');
      sb.writeln('───────────────────────────────────────────────────────────');
      sb.writeln();
      for (final r in selectedReadings) {
        sb.write('${_formatDateTime(r.timestamp)}');
        sb.write('   ${r.displayValue} ${_selectedVital.unit}');
        final tags = <String>[];
        if (r.context != null) tags.add(r.context!);
        if (r.position != null) tags.add(r.position!);
        if (r.location != null) tags.add(r.location!);
        if (r.postExercise) tags.add('post-exercise');
        if (r.underStress) tags.add('stressed');
        if (tags.isNotEmpty) sb.write('   [${tags.join(", ")}]');
        if (r.notes != null && r.notes!.isNotEmpty) {
          sb.writeln();
          sb.write('   Note: ${r.notes}');
        }
        sb.writeln();
      }
      sb.writeln();
    }

    // ─── FOOTER ────────────────────────────────────────────────────────────
    sb.writeln('───────────────────────────────────────────────────────────');
    sb.writeln('  DISCLAIMER');
    sb.writeln('───────────────────────────────────────────────────────────');
    sb.writeln();
    sb.writeln(
        'This report is generated from self-reported readings and is not a');
    sb.writeln(
        'clinical diagnostic document. Values and observations should be');
    sb.writeln(
        'reviewed by a qualified healthcare provider. Jovi Health does not');
    sb.writeln('provide medical advice.');
    sb.writeln();
    sb.writeln('═══════════════════════════════════════════════════════════');

    return sb.toString();
  }

  /// Opens a preview sheet showing the full doctor report with export actions.
  void _openDoctorReport() {
    final reportText = _generateDoctorReport();

    _showNavyBottomSheet(
      heightFactor: 0.92,
      child: Column(
        children: [
          _sheetHandle(),
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
            child: Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    gradient: _Jovi.coralGradient,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                        color: _Jovi.coral.withOpacity(0.4),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.description_rounded,
                      color: Colors.white, size: 22),
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
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.3,
                        ),
                      ),
                      Text(
                        'Ready to share with your provider',
                        style: TextStyle(
                          color: Color(0x99FFFFFF),
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
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
          // Report preview — monospace, scrollable
          Expanded(
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 16),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.25),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: Colors.white.withOpacity(0.08),
                  width: 1,
                ),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(14),
                child: Scrollbar(
                  thumbVisibility: true,
                  child: SingleChildScrollView(
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.all(14),
                    child: SelectableText(
                      reportText,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.92),
                        fontSize: 10.5,
                        fontFamily: 'Courier',
                        height: 1.5,
                        letterSpacing: 0.1,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          // Action buttons
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _primaryButton(
                        label: 'Copy Full Report',
                        icon: Icons.copy_all_rounded,
                        expand: true,
                        onTap: () {
                          Clipboard.setData(ClipboardData(text: reportText));
                          HapticFeedback.mediumImpact();
                          _showSnack(
                              'Report copied — paste into email, Notes, or a document');
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: _secondaryButton(
                        label: 'CSV Data',
                        icon: Icons.table_chart_outlined,
                        onTap: () {
                          Navigator.of(context).pop();
                          _exportCSV();
                        },
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _secondaryButton(
                        label: 'Save as PDF',
                        icon: Icons.picture_as_pdf_rounded,
                        onTap: () {
                          Navigator.of(context).pop();
                          _savePdfInstructions();
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(Icons.info_outline_rounded,
                        color: Colors.white.withOpacity(0.45), size: 12),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Text is selectable above — long-press to copy a section.',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.5),
                          fontSize: 10.5,
                          fontWeight: FontWeight.w500,
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
    );
  }

  /// Copies the report and opens a dialog explaining the PDF conversion flow.
  /// This uses the OS-native print-to-PDF capability rather than requiring
  /// a heavyweight dart:pdf dependency that may not be in the build.
  void _savePdfInstructions() {
    final reportText = _generateDoctorReport();
    Clipboard.setData(ClipboardData(text: reportText));
    HapticFeedback.mediumImpact();

    _showNavyDialog(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: _Jovi.coral.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: _Jovi.coral.withOpacity(0.4),
                    width: 1,
                  ),
                ),
                child: Icon(Icons.picture_as_pdf_rounded,
                    color: _Jovi.coral, size: 18),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  'Report copied',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'To save as a PDF:',
            style: TextStyle(
              color: Colors.white.withOpacity(0.9),
              fontSize: 13,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          _instructionStep(
            '1',
            'Open Notes or Mail',
            'Paste the report into a new note or email draft.',
          ),
          _instructionStep(
            '2',
            'Use the share icon',
            'Tap share → Print, then pinch-to-zoom the preview to save as PDF.',
          ),
          _instructionStep(
            '3',
            'Send to your doctor',
            'Email, AirDrop, or attach to your patient portal.',
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: _Jovi.mint.withOpacity(0.12),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: _Jovi.mint.withOpacity(0.3),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.lightbulb_outline_rounded,
                    color: _Jovi.mint, size: 16),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'The report is formatted in monospace, so it holds its layout when pasted into any document.',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.85),
                      fontSize: 11.5,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _primaryButton(
            label: 'Got it',
            expand: true,
            onTap: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }

  Widget _instructionStep(String num, String title, String body) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 22,
            height: 22,
            decoration: BoxDecoration(
              gradient: _Jovi.coralGradient,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text(
              num,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  body,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.75),
                    fontSize: 11.5,
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─── HEIGHT DIALOG (for BMI) ─────────────────────────────────────────────

  void _showHeightDialog() {
    int feet =
        _userHeightInches != null ? (_userHeightInches! / 12).floor() : 5;
    int inches =
        _userHeightInches != null ? (_userHeightInches! % 12).round() : 8;

    _showNavyDialog(
      child: StatefulBuilder(
        builder: (ctx, setDialog) => Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Your Height',
              style: TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 6),
            Text(
              'Used only to calculate BMI from your weight readings.',
              style: TextStyle(
                  color: Colors.white.withOpacity(0.7),
                  fontSize: 12,
                  height: 1.4),
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: _numberStepper(
                    label: 'Feet',
                    value: feet,
                    min: 3,
                    max: 8,
                    onChanged: (v) => setDialog(() => feet = v),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _numberStepper(
                    label: 'Inches',
                    value: inches,
                    min: 0,
                    max: 11,
                    onChanged: (v) => setDialog(() => inches = v),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Row(
              children: [
                Expanded(
                  child: _secondaryButton(
                    label: 'Cancel',
                    onTap: () => Navigator.of(ctx).pop(),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _primaryButton(
                    label: 'Save',
                    onTap: () async {
                      Navigator.of(ctx).pop();
                      final total = feet * 12 + inches;
                      setState(() => _userHeightInches = total.toDouble());
                      try {
                        await _userRef.set(
                          {'heightInches': total},
                          SetOptions(merge: true),
                        );
                        _showSnack('Height saved');
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
      ),
    );
  }

  Widget _numberStepper({
    required String label,
    required int value,
    required int min,
    required int max,
    required ValueChanged<int> onChanged,
  }) {
    return _glassCard(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      radius: 12,
      child: Column(
        children: [
          Text(
            label.toUpperCase(),
            style: TextStyle(
              color: Colors.white.withOpacity(0.6),
              fontSize: 9.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _Pressable(
                onTap: () {
                  if (value > min) {
                    HapticFeedback.selectionClick();
                    onChanged(value - 1);
                  }
                },
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(Icons.remove_rounded,
                      color: value > min
                          ? Colors.white
                          : Colors.white.withOpacity(0.3),
                      size: 16),
                ),
              ),
              Text(
                value.toString(),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
              ),
              _Pressable(
                onTap: () {
                  if (value < max) {
                    HapticFeedback.selectionClick();
                    onChanged(value + 1);
                  }
                },
                child: Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: _Jovi.coral.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: _Jovi.coral.withOpacity(0.4),
                      width: 1,
                    ),
                  ),
                  child: Icon(Icons.add_rounded, color: _Jovi.coral, size: 16),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // INSIGHTS TAB
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildInsightsTab(ResponsiveConfig cfg) {
    final insights = _generateInsights();

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 90),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Range selector
          _glassCard(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            radius: 100,
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              child: Row(
                children: [
                  _timeRangePill('7D', '7d'),
                  _timeRangePill('30D', '30d'),
                  _timeRangePill('90D', '90d'),
                  _timeRangePill('All', 'all'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          _buildInsightsSummary(insights),
          const SizedBox(height: 14),
          if (insights.isEmpty)
            _buildNoInsightsCard()
          else
            _buildInsightsList(insights),
          if (insights.isNotEmpty) ...[
            const SizedBox(height: 14),
            _primaryButton(
              label: 'Generate Doctor Report',
              icon: Icons.description_rounded,
              expand: true,
              onTap: _openDoctorReport,
            ),
          ],
          const SizedBox(height: 10),
          _buildDisclaimerCard(),
        ],
      ),
    );
  }

  Widget _buildInsightsSummary(List<Insight> insights) {
    final urgent =
        insights.where((i) => i.severity == InsightSeverity.urgent).length;
    final concern =
        insights.where((i) => i.severity == InsightSeverity.concern).length;
    final watch =
        insights.where((i) => i.severity == InsightSeverity.watch).length;
    final info =
        insights.where((i) => i.severity == InsightSeverity.info).length;

    final worstSev = urgent > 0
        ? InsightSeverity.urgent
        : concern > 0
            ? InsightSeverity.concern
            : watch > 0
                ? InsightSeverity.watch
                : InsightSeverity.info;
    final worstColor = _Jovi.severityColor(worstSev);

    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(22),
            gradient: LinearGradient(
              colors: insights.isEmpty
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
              color: insights.isEmpty
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
                    scale: urgent > 0
                        ? _pulseAnimation
                        : const AlwaysStoppedAnimation(1.0),
                    child: Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        gradient: insights.isEmpty
                            ? const LinearGradient(
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
                            color: (insights.isEmpty ? _Jovi.mint : worstColor)
                                .withOpacity(0.4),
                            blurRadius: 14,
                            offset: const Offset(0, 4),
                          ),
                        ],
                      ),
                      child: Icon(
                        insights.isEmpty
                            ? Icons.verified_rounded
                            : Icons.psychology_rounded,
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
                          insights.isEmpty
                              ? 'All Clear'
                              : insights.length == 1
                                  ? '1 insight'
                                  : '${insights.length} insights',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -0.3,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          insights.isEmpty
                              ? 'No clinical concerns detected in your readings.'
                              : urgent > 0
                                  ? 'Urgent findings require immediate attention.'
                                  : concern > 0
                                      ? 'Some concerns worth reviewing.'
                                      : 'Patterns and observations from your data.',
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
              if (insights.isNotEmpty) ...[
                const SizedBox(height: 14),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    if (urgent > 0)
                      _countChip('$urgent Urgent', InsightSeverity.urgent),
                    if (concern > 0)
                      _countChip('$concern Concern', InsightSeverity.concern),
                    if (watch > 0)
                      _countChip('$watch Watch', InsightSeverity.watch),
                    if (info > 0)
                      _countChip('$info Info', InsightSeverity.info),
                  ],
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _countChip(String label, InsightSeverity s) {
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
        style: const TextStyle(
          color: Colors.white,
          fontSize: 11,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }

  Widget _buildNoInsightsCard() {
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
              gradient: const LinearGradient(
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
            'No Clinical Concerns',
            style: TextStyle(
                color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          Text(
            'Your recent vital sign readings don\'t show patterns that need immediate attention. Keep logging regularly to improve the quality of insights.',
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

  Widget _buildInsightsList(List<Insight> insights) {
    // Group by severity
    final grouped = <InsightSeverity, List<Insight>>{};
    for (final i in insights) {
      grouped.putIfAbsent(i.severity, () => []).add(i);
    }
    final order = [
      InsightSeverity.urgent,
      InsightSeverity.concern,
      InsightSeverity.watch,
      InsightSeverity.info,
    ];
    final labels = {
      InsightSeverity.urgent: 'Urgent',
      InsightSeverity.concern: 'Concern',
      InsightSeverity.watch: 'Watch',
      InsightSeverity.info: 'Info',
    };

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final sev in order)
          if (grouped.containsKey(sev)) ...[
            _sectionHeader(
              '${labels[sev]} — ${grouped[sev]!.length}',
              icon: _severityIcon(sev),
            ),
            ...grouped[sev]!.map((i) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _buildInsightCard(i),
                )),
          ],
      ],
    );
  }

  IconData _severityIcon(InsightSeverity s) {
    switch (s) {
      case InsightSeverity.urgent:
        return Icons.warning_rounded;
      case InsightSeverity.concern:
        return Icons.error_outline_rounded;
      case InsightSeverity.watch:
        return Icons.visibility_rounded;
      case InsightSeverity.info:
        return Icons.info_outline_rounded;
    }
  }

  Widget _buildInsightCard(Insight i) {
    final color = _Jovi.severityColor(i.severity);
    final isSevere = i.severity == InsightSeverity.urgent ||
        i.severity == InsightSeverity.concern;
    return _glassCard(
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
                  border: Border.all(color: color.withOpacity(0.45), width: 1),
                ),
                child: Icon(i.icon, color: color, size: 18),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      i.title,
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700),
                    ),
                    if (i.relatedVital != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        i.relatedVital!.label,
                        style: TextStyle(
                            color: _Jovi.vitalColor(i.relatedVital!),
                            fontSize: 11,
                            fontWeight: FontWeight.w600),
                      ),
                    ],
                  ],
                ),
              ),
              _severityBadge(i.severity),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            i.body,
            style: const TextStyle(
                color: Colors.white, fontSize: 12.5, height: 1.45),
          ),
          if (i.actionLabel != null && i.action != null) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: _primaryButton(
                label: i.actionLabel!,
                onTap: i.action!,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDisclaimerCard() {
    return _glassCard(
      padding: const EdgeInsets.all(12),
      radius: 12,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline_rounded,
              color: Colors.white.withOpacity(0.55), size: 14),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'These insights are informational and based on pattern detection in your data. They are not medical advice and do not replace consultation with a healthcare provider.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.55),
                fontSize: 11,
                fontStyle: FontStyle.italic,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // LOG TAB
  // ═══════════════════════════════════════════════════════════════════════════

  VitalType? _logFilterType; // null = show all

  Widget _buildLogTab(ResponsiveConfig cfg) {
    final filtered = _logFilterType == null
        ? _allReadings
        : (_readingsByType[_logFilterType!] ?? []);
    final sorted = [...filtered]
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));

    return Column(
      children: [
        Padding(
          padding: EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, 8),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const BouncingScrollPhysics(),
            child: Row(
              children: [
                _logFilterChip(null, 'All'),
                ...VitalType.values.map((t) => _logFilterChip(t, t.label)),
              ],
            ),
          ),
        ),
        Expanded(
          child: sorted.isEmpty
              ? _emptyState(
                  icon: Icons.history_rounded,
                  title: 'No readings logged',
                  subtitle:
                      'Readings you add will appear here with full details and notes.',
                )
              : ListView.builder(
                  physics: const BouncingScrollPhysics(),
                  padding: EdgeInsets.fromLTRB(
                      cfg.paddingH, 0, cfg.paddingH, cfg.paddingV + 90),
                  itemCount: sorted.length,
                  itemBuilder: (ctx, i) {
                    // Insert date header when date changes
                    final r = sorted[i];
                    final showHeader = i == 0 ||
                        !_sameDay(sorted[i - 1].timestamp, r.timestamp);
                    return Column(
                      children: [
                        if (showHeader) _buildDateHeader(r.timestamp),
                        _buildLogRow(r),
                      ],
                    );
                  },
                ),
        ),
      ],
    );
  }

  bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  Future<bool> _dial(String number) async {
    try {
      return await launchUrl(Uri(scheme: 'tel', path: number),
          mode: LaunchMode.externalApplication);
    } catch (_) {
      return false;
    }
  }

  Widget _buildDateHeader(DateTime d) {
    final now = DateTime.now();
    String label;
    if (_sameDay(d, now)) {
      label = 'Today';
    } else if (_sameDay(d, now.subtract(const Duration(days: 1)))) {
      label = 'Yesterday';
    } else {
      const days = [
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday'
      ];
      label = '${days[d.weekday - 1]}, ${_formatDateShort(d)}';
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 12, 4, 8),
      child: Row(
        children: [
          _coralGradientIcon(Icons.calendar_today_rounded, size: 12),
          const SizedBox(width: 6),
          Text(
            label.toUpperCase(),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 10.5,
              fontWeight: FontWeight.w700,
              letterSpacing: 1.2,
            ),
          ),
        ],
      ),
    );
  }

  Widget _logFilterChip(VitalType? t, String label) {
    final sel = _logFilterType == t;
    final color = t != null ? _Jovi.vitalColor(t) : _Jovi.coral;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _logFilterType = t);
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.only(right: 6),
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
        decoration: BoxDecoration(
          color: sel ? color.withOpacity(0.22) : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(100),
          border: Border.all(
            color: sel ? color : Colors.white.withOpacity(0.12),
            width: sel ? 1.5 : 1,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildLogRow(VitalReading r) {
    final color = _Jovi.vitalColor(r.type);
    // Compute status for BP or goal-based status for others
    Color statusColor = Colors.white;
    if (r.type == VitalType.bloodPressure &&
        r.value != null &&
        r.secondary != null) {
      final stage = _ClinicalRefs.classifyBP(r.value!, r.secondary!);
      statusColor = stage == BPStage.normal
          ? _Jovi.mint
          : stage == BPStage.elevated
              ? _Jovi.gold
              : stage == BPStage.stage1
                  ? _Jovi.coral
                  : _Jovi.errorRed;
    } else {
      final goal = _goals[r.type];
      if (goal != null && r.value != null) {
        if (goal.primaryMax != null && r.value! > goal.primaryMax!) {
          statusColor = _Jovi.coral;
        } else if (goal.primaryMin != null && r.value! < goal.primaryMin!) {
          statusColor = _Jovi.gold;
        } else {
          statusColor = _Jovi.mint;
        }
      }
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => _showReadingDetails(r),
          onLongPress: () {
            HapticFeedback.mediumImpact();
            _confirmDeleteReading(r);
          },
          child: _glassCard(
            padding: const EdgeInsets.all(12),
            radius: 14,
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: color.withOpacity(0.3), width: 1),
                  ),
                  child: Icon(_vitalIcon(r.type), color: color, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.baseline,
                        textBaseline: TextBaseline.alphabetic,
                        children: [
                          Text(
                            r.displayValue,
                            style: TextStyle(
                                color: statusColor,
                                fontSize: 16,
                                fontWeight: FontWeight.w800,
                                letterSpacing: -0.3),
                          ),
                          const SizedBox(width: 4),
                          Text(
                            r.type.unit,
                            style: TextStyle(
                                color: Colors.white.withOpacity(0.6),
                                fontSize: 10.5,
                                fontWeight: FontWeight.w500),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${r.type.label} · ${_timeOnly(r.timestamp)}',
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.6),
                            fontSize: 11,
                            fontWeight: FontWeight.w500),
                      ),
                      if (r.notes != null && r.notes!.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(
                          r.notes!,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.75),
                            fontSize: 11,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                // Tags
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    if (r.source != 'Manual')
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: _glassPill(
                          tint: _Jovi.mint,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2),
                          child: Text(
                            r.source,
                            style: TextStyle(
                                color: _Jovi.mint,
                                fontSize: 9.5,
                                fontWeight: FontWeight.w700),
                          ),
                        ),
                      ),
                    if (r.context != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: _glassPill(
                          tint: _Jovi.violet,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2),
                          child: Text(
                            r.context!,
                            style: TextStyle(
                                color: _Jovi.violet,
                                fontSize: 9.5,
                                fontWeight: FontWeight.w700),
                          ),
                        ),
                      ),
                    if (r.postExercise || r.underStress)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: _glassPill(
                          tint: _Jovi.gold,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2),
                          child: Text(
                            r.postExercise ? 'Post-Exercise' : 'Stressed',
                            style: TextStyle(
                                color: _Jovi.gold,
                                fontSize: 9.5,
                                fontWeight: FontWeight.w700),
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
    );
  }

  String _timeOnly(DateTime d) {
    final hour = d.hour == 0
        ? 12
        : d.hour > 12
            ? d.hour - 12
            : d.hour;
    final period = d.hour >= 12 ? 'PM' : 'AM';
    final minute = d.minute.toString().padLeft(2, '0');
    return '$hour:$minute $period';
  }

  void _showReadingDetails(VitalReading r) {
    _showNavyBottomSheet(
      heightFactor: 0.6,
      child: Column(
        children: [
          _sheetHandle(),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 14),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: _Jovi.vitalColor(r.type).withOpacity(0.18),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: _Jovi.vitalColor(r.type).withOpacity(0.4),
                      width: 1,
                    ),
                  ),
                  child: Icon(
                    _vitalIcon(r.type),
                    color: _Jovi.vitalColor(r.type),
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        r.type.label,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w700),
                      ),
                      Text(
                        _formatDateTime(r.timestamp),
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.65),
                            fontSize: 12,
                            fontWeight: FontWeight.w500),
                      ),
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
            child: SingleChildScrollView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Big value display
                  _glassCard(
                    padding: const EdgeInsets.all(20),
                    radius: 16,
                    tintColor: _Jovi.vitalColor(r.type),
                    tintOpacity: 0.08,
                    child: Column(
                      children: [
                        Text(
                          r.displayValue,
                          style: TextStyle(
                              color: _Jovi.vitalColor(r.type),
                              fontSize: 48,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -1.5,
                              height: 1),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          r.type.unit,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.7),
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 10),
                        if (r.type == VitalType.bloodPressure &&
                            r.value != null &&
                            r.secondary != null)
                          Text(
                            _ClinicalRefs.classifyBP(r.value!, r.secondary!)
                                .label,
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  if (r.context != null ||
                      r.position != null ||
                      r.location != null ||
                      r.postExercise ||
                      r.underStress) ...[
                    _sectionHeader('Context',
                        icon: Icons.label_outline_rounded),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        if (r.context != null)
                          _detailChip(r.context!, _Jovi.violet),
                        if (r.position != null)
                          _detailChip(r.position!, _Jovi.sky),
                        if (r.location != null)
                          _detailChip(r.location!, _Jovi.mint),
                        if (r.postExercise)
                          _detailChip('Post-exercise', _Jovi.gold),
                        if (r.underStress) _detailChip('Stressed', _Jovi.coral),
                      ],
                    ),
                    const SizedBox(height: 14),
                  ],
                  if (r.notes != null && r.notes!.isNotEmpty) ...[
                    _sectionHeader('Notes', icon: Icons.edit_note_rounded),
                    _glassCard(
                      padding: const EdgeInsets.all(12),
                      radius: 12,
                      child: Text(
                        r.notes!,
                        style: const TextStyle(
                            color: Colors.white, fontSize: 13, height: 1.5),
                      ),
                    ),
                    const SizedBox(height: 14),
                  ],
                  _sectionHeader('Source', icon: Icons.source_rounded),
                  _glassCard(
                    padding: const EdgeInsets.all(12),
                    radius: 12,
                    child: Row(
                      children: [
                        Icon(Icons.verified_outlined,
                            color: Colors.white.withOpacity(0.7), size: 16),
                        const SizedBox(width: 8),
                        Text(
                          r.source,
                          style: const TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      Expanded(
                        child: _secondaryButton(
                          label: 'Delete',
                          icon: Icons.delete_outline_rounded,
                          onTap: () {
                            Navigator.of(context).pop();
                            _confirmDeleteReading(r);
                          },
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _primaryButton(
                          label: 'Done',
                          onTap: () => Navigator.of(context).pop(),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _detailChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withOpacity(0.18),
        borderRadius: BorderRadius.circular(100),
        border: Border.all(color: color.withOpacity(0.4), width: 1),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  void _confirmDeleteReading(VitalReading r) {
    _showNavyDialog(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Delete reading?',
            style: TextStyle(
                color: Colors.white, fontSize: 16, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(
            '${r.type.label}: ${r.displayValue} ${r.type.unit} from ${_formatDateTime(r.timestamp)}. This cannot be undone.',
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
                  label: 'Delete',
                  onTap: () async {
                    Navigator.of(context).pop();
                    try {
                      await _vitalsRef.doc(r.id).delete();
                      _showSnack('Reading deleted');
                      _loadData();
                    } catch (_) {
                      _showSnack('Couldn\'t delete', isError: true);
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

  // ═══════════════════════════════════════════════════════════════════════════
  // ADD READING SHEET
  // ═══════════════════════════════════════════════════════════════════════════

  void _openAddReadingSheet(VitalType type) {
    // Ephemeral state for the sheet
    final systolicCtrl = TextEditingController();
    final diastolicCtrl = TextEditingController();
    final valueCtrl = TextEditingController();
    final notesCtrl = TextEditingController();

    GlucoseContext? glucoseCtx;
    BPPosition? bpPosition;
    Location? location;
    bool postExercise = false;
    bool underStress = false;
    DateTime readingTime = DateTime.now();
    bool saving = false;

    _showNavyBottomSheet(
      heightFactor: 0.9,
      child: StatefulBuilder(
        builder: (ctx, setSheet) {
          Future<void> saveReading() async {
            if (saving) return;

            VitalReading? reading;
            if (type == VitalType.bloodPressure) {
              final sys = double.tryParse(systolicCtrl.text);
              final dia = double.tryParse(diastolicCtrl.text);
              if (sys == null || dia == null) {
                _showSnack('Enter both systolic and diastolic', isError: true);
                return;
              }
              if (sys < 40 || sys > 260 || dia < 30 || dia > 180) {
                _showSnack('BP values out of realistic range', isError: true);
                return;
              }
              reading = VitalReading(
                id: '',
                type: type,
                timestamp: readingTime,
                value: sys,
                secondary: dia,
                notes: notesCtrl.text.trim().isEmpty
                    ? null
                    : notesCtrl.text.trim(),
                position: bpPosition?.label,
                location: location?.label,
                postExercise: postExercise,
                underStress: underStress,
              );
            } else {
              final v = double.tryParse(valueCtrl.text);
              if (v == null) {
                _showSnack('Enter a valid number', isError: true);
                return;
              }
              // Basic range validation
              if (type == VitalType.heartRate && (v < 20 || v > 250)) {
                _showSnack('Heart rate out of realistic range', isError: true);
                return;
              }
              if (type == VitalType.bloodGlucose && (v < 15 || v > 700)) {
                _showSnack('Glucose out of realistic range', isError: true);
                return;
              }
              if (type == VitalType.oxygen && (v < 50 || v > 100)) {
                _showSnack('Oxygen must be between 50-100%', isError: true);
                return;
              }
              if (type == VitalType.temperature && (v < 85 || v > 115)) {
                _showSnack('Temperature out of realistic range', isError: true);
                return;
              }
              if (type == VitalType.weight && (v < 20 || v > 1500)) {
                _showSnack('Weight out of realistic range', isError: true);
                return;
              }
              reading = VitalReading(
                id: '',
                type: type,
                timestamp: readingTime,
                value: v,
                notes: notesCtrl.text.trim().isEmpty
                    ? null
                    : notesCtrl.text.trim(),
                context: glucoseCtx?.label,
                location: location?.label,
                postExercise: postExercise,
                underStress: underStress,
              );
            }

            setSheet(() => saving = true);
            try {
              await _vitalsRef.add(reading.toFirestore());
              if (!mounted) return;
              Navigator.of(ctx).pop();
              HapticFeedback.mediumImpact();
              _showSnack('${type.label} saved');
              _loadData();
              // If weight was logged and height not set, prompt
              if (type == VitalType.weight && _userHeightInches == null) {
                Future.delayed(
                    const Duration(milliseconds: 400), _showHeightDialog);
              }
            } catch (e) {
              setSheet(() => saving = false);
              _showSnack('Couldn\'t save', isError: true);
            }
          }

          return Column(
            children: [
              _sheetHandle(),
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 4, 20, 10),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: _Jovi.vitalColor(type).withOpacity(0.18),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: _Jovi.vitalColor(type).withOpacity(0.4),
                          width: 1,
                        ),
                      ),
                      child: Icon(
                        _vitalIcon(type),
                        color: _Jovi.vitalColor(type),
                        size: 22,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Log ${type.label}',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              letterSpacing: -0.3,
                            ),
                          ),
                          Text(
                            'Measured in ${type.unit}',
                            style: TextStyle(
                              color: Colors.white.withOpacity(0.6),
                              fontSize: 11.5,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                    _Pressable(
                      onTap: () => Navigator.of(ctx).pop(),
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
                      // ─── VALUE INPUT ─────────────────────────────────────
                      _sectionHeader('Reading', icon: Icons.edit_rounded),
                      if (type == VitalType.bloodPressure)
                        _buildBPInput(systolicCtrl, diastolicCtrl, setSheet)
                      else
                        _buildSingleValueInput(type, valueCtrl, setSheet),

                      // Preset buttons for BP
                      if (type == VitalType.bloodPressure) ...[
                        const SizedBox(height: 10),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: [
                            _presetChip('Normal\n120/80', () {
                              setSheet(() {
                                systolicCtrl.text = '120';
                                diastolicCtrl.text = '80';
                              });
                            }, _Jovi.mint),
                            _presetChip('Elevated\n125/80', () {
                              setSheet(() {
                                systolicCtrl.text = '125';
                                diastolicCtrl.text = '80';
                              });
                            }, _Jovi.gold),
                            _presetChip('Stage 1\n135/85', () {
                              setSheet(() {
                                systolicCtrl.text = '135';
                                diastolicCtrl.text = '85';
                              });
                            }, _Jovi.coral),
                            _presetChip('Stage 2\n145/95', () {
                              setSheet(() {
                                systolicCtrl.text = '145';
                                diastolicCtrl.text = '95';
                              });
                            }, _Jovi.softRed),
                          ],
                        ),
                      ],

                      const SizedBox(height: 18),

                      // ─── CONTEXT (glucose-specific) ───────────────────────
                      if (type == VitalType.bloodGlucose) ...[
                        _sectionHeader('When was this taken?',
                            icon: Icons.schedule_rounded),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: GlucoseContext.values.map((c) {
                            final sel = glucoseCtx == c;
                            return _Pressable(
                              onTap: () {
                                HapticFeedback.selectionClick();
                                setSheet(() => glucoseCtx = sel ? null : c);
                              },
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 12, vertical: 8),
                                decoration: BoxDecoration(
                                  color: sel
                                      ? _Jovi.violet.withOpacity(0.22)
                                      : Colors.white.withOpacity(0.06),
                                  borderRadius: BorderRadius.circular(100),
                                  border: Border.all(
                                    color: sel
                                        ? _Jovi.violet
                                        : Colors.white.withOpacity(0.12),
                                    width: sel ? 1.5 : 1,
                                  ),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(c.icon,
                                        color: sel
                                            ? _Jovi.violet
                                            : Colors.white.withOpacity(0.7),
                                        size: 13),
                                    const SizedBox(width: 6),
                                    Text(
                                      c.label,
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 11.5,
                                        fontWeight: sel
                                            ? FontWeight.w700
                                            : FontWeight.w500,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                        const SizedBox(height: 18),
                      ],

                      // ─── POSITION (BP-specific) ──────────────────────────
                      if (type == VitalType.bloodPressure) ...[
                        _sectionHeader('Position',
                            icon: Icons.accessibility_new_rounded),
                        Row(
                          children: BPPosition.values.map((p) {
                            final sel = bpPosition == p;
                            return Expanded(
                              child: Padding(
                                padding: EdgeInsets.only(
                                    right: p == BPPosition.values.last ? 0 : 6),
                                child: _Pressable(
                                  onTap: () {
                                    HapticFeedback.selectionClick();
                                    setSheet(() => bpPosition = sel ? null : p);
                                  },
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                        vertical: 10),
                                    decoration: BoxDecoration(
                                      color: sel
                                          ? _Jovi.sky.withOpacity(0.22)
                                          : Colors.white.withOpacity(0.06),
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(
                                        color: sel
                                            ? _Jovi.sky
                                            : Colors.white.withOpacity(0.12),
                                        width: sel ? 1.5 : 1,
                                      ),
                                    ),
                                    child: Text(
                                      p.label,
                                      textAlign: TextAlign.center,
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 11.5,
                                        fontWeight: sel
                                            ? FontWeight.w700
                                            : FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            );
                          }).toList(),
                        ),
                        const SizedBox(height: 18),
                      ],

                      // ─── LOCATION (all types) ────────────────────────────
                      _sectionHeader('Location', icon: Icons.place_outlined),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: Location.values.map((loc) {
                          final sel = location == loc;
                          return _Pressable(
                            onTap: () {
                              HapticFeedback.selectionClick();
                              setSheet(() => location = sel ? null : loc);
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 8),
                              decoration: BoxDecoration(
                                color: sel
                                    ? _Jovi.mint.withOpacity(0.22)
                                    : Colors.white.withOpacity(0.06),
                                borderRadius: BorderRadius.circular(100),
                                border: Border.all(
                                  color: sel
                                      ? _Jovi.mint
                                      : Colors.white.withOpacity(0.12),
                                  width: sel ? 1.5 : 1,
                                ),
                              ),
                              child: Text(
                                loc.label,
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 11.5,
                                  fontWeight:
                                      sel ? FontWeight.w700 : FontWeight.w500,
                                ),
                              ),
                            ),
                          );
                        }).toList(),
                      ),

                      const SizedBox(height: 18),

                      // ─── CONDITIONS ──────────────────────────────────────
                      _sectionHeader('Conditions (optional)',
                          icon: Icons.flag_rounded),
                      Row(
                        children: [
                          Expanded(
                            child: _toggleCard(
                              label: 'Post-Exercise',
                              icon: Icons.directions_run_rounded,
                              selected: postExercise,
                              color: _Jovi.gold,
                              onTap: () =>
                                  setSheet(() => postExercise = !postExercise),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _toggleCard(
                              label: 'Under Stress',
                              icon: Icons.psychology_rounded,
                              selected: underStress,
                              color: _Jovi.coral,
                              onTap: () =>
                                  setSheet(() => underStress = !underStress),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 18),

                      // ─── NOTES ──────────────────────────────────────────
                      _sectionHeader('Notes (optional)',
                          icon: Icons.edit_note_rounded),
                      _glassCard(
                        padding: const EdgeInsets.all(4),
                        radius: 12,
                        child: TextField(
                          controller: notesCtrl,
                          maxLines: 3,
                          textCapitalization: TextCapitalization.sentences,
                          textInputAction: TextInputAction.done,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                          ),
                          decoration: InputDecoration(
                            border: InputBorder.none,
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 10),
                            hintText: 'e.g., Right after waking, felt dizzy…',
                            hintStyle: TextStyle(
                              color: Colors.white.withOpacity(0.4),
                              fontSize: 12.5,
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 22),

                      // ─── SAVE ────────────────────────────────────────────
                      _primaryButton(
                        label: 'Save Reading',
                        icon: Icons.check_rounded,
                        onTap: saveReading,
                        loading: saving,
                        expand: true,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildBPInput(
    TextEditingController sys,
    TextEditingController dia,
    void Function(void Function()) setSheet,
  ) {
    return Row(
      children: [
        Expanded(
          child: _glassCard(
            padding: const EdgeInsets.all(4),
            radius: 14,
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    'SYSTOLIC',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 9.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                    ),
                  ),
                ),
                TextField(
                  controller: sys,
                  keyboardType: TextInputType.number,
                  textAlign: TextAlign.center,
                  autofocus: true,
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    LengthLimitingTextInputFormatter(3),
                  ],
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 32,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -1,
                  ),
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.symmetric(vertical: 4),
                    hintText: '120',
                    hintStyle: TextStyle(
                      color: Color(0x33FFFFFF),
                      fontSize: 32,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  onChanged: (_) => setSheet(() {}),
                ),
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    'mmHg',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 10.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: Text(
            '/',
            style: TextStyle(
              color: Colors.white.withOpacity(0.4),
              fontSize: 32,
              fontWeight: FontWeight.w300,
            ),
          ),
        ),
        Expanded(
          child: _glassCard(
            padding: const EdgeInsets.all(4),
            radius: 14,
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    'DIASTOLIC',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.6),
                      fontSize: 9.5,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.8,
                    ),
                  ),
                ),
                TextField(
                  controller: dia,
                  keyboardType: TextInputType.number,
                  textAlign: TextAlign.center,
                  inputFormatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    LengthLimitingTextInputFormatter(3),
                  ],
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 32,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -1,
                  ),
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.symmetric(vertical: 4),
                    hintText: '80',
                    hintStyle: TextStyle(
                      color: Color(0x33FFFFFF),
                      fontSize: 32,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  onChanged: (_) => setSheet(() {}),
                ),
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    'mmHg',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.5),
                      fontSize: 10.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSingleValueInput(
    VitalType type,
    TextEditingController ctrl,
    void Function(void Function()) setSheet,
  ) {
    final allowDecimal =
        type == VitalType.weight || type == VitalType.temperature;
    String hint;
    switch (type) {
      case VitalType.heartRate:
        hint = '72';
        break;
      case VitalType.bloodGlucose:
        hint = '95';
        break;
      case VitalType.weight:
        hint = '170';
        break;
      case VitalType.oxygen:
        hint = '98';
        break;
      case VitalType.temperature:
        hint = '98.6';
        break;
      default:
        hint = '';
    }
    return _glassCard(
      padding: const EdgeInsets.all(4),
      radius: 14,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              type.label.toUpperCase(),
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 9.5,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.8,
              ),
            ),
          ),
          TextField(
            controller: ctrl,
            keyboardType:
                TextInputType.numberWithOptions(decimal: allowDecimal),
            textAlign: TextAlign.center,
            autofocus: true,
            inputFormatters: [
              if (!allowDecimal) FilteringTextInputFormatter.digitsOnly,
              if (allowDecimal)
                FilteringTextInputFormatter.allow(RegExp(r'^\d+\.?\d{0,1}')),
              LengthLimitingTextInputFormatter(6),
            ],
            style: TextStyle(
              color: _Jovi.vitalColor(type),
              fontSize: 48,
              fontWeight: FontWeight.w800,
              letterSpacing: -1.5,
            ),
            decoration: InputDecoration(
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(vertical: 6),
              hintText: hint,
              hintStyle: TextStyle(
                color: Colors.white.withOpacity(0.2),
                fontSize: 48,
                fontWeight: FontWeight.w800,
              ),
            ),
            onChanged: (_) => setSheet(() {}),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              type.unit,
              style: TextStyle(
                color: Colors.white.withOpacity(0.6),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _presetChip(String label, VoidCallback onTap, Color accent) {
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: accent.withOpacity(0.14),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: accent.withOpacity(0.4), width: 1),
        ),
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: accent,
            fontSize: 10.5,
            fontWeight: FontWeight.w700,
            height: 1.3,
          ),
        ),
      ),
    );
  }

  Widget _toggleCard({
    required String label,
    required IconData icon,
    required bool selected,
    required Color color,
    required VoidCallback onTap,
  }) {
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
        decoration: BoxDecoration(
          color: selected
              ? color.withOpacity(0.18)
              : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected ? color : Colors.white.withOpacity(0.12),
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              selected ? Icons.check_circle_rounded : icon,
              color: selected ? color : Colors.white.withOpacity(0.6),
              size: 16,
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                label,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 11.5,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // GOALS TAB
  // ═══════════════════════════════════════════════════════════════════════════

  Widget _buildGoalsTab(ResponsiveConfig cfg) {
    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      padding:
          EdgeInsets.fromLTRB(cfg.paddingH, 8, cfg.paddingH, cfg.paddingV + 90),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _glassCard(
            padding: const EdgeInsets.all(14),
            radius: 16,
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
                    boxShadow: [
                      BoxShadow(
                        color: _Jovi.coral.withOpacity(0.4),
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: const Icon(Icons.flag_rounded,
                      color: Colors.white, size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Set Your Targets',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Discuss goals with your doctor. Defaults are based on general healthy ranges.',
                        style: TextStyle(
                          color: Colors.white.withOpacity(0.75),
                          fontSize: 11.5,
                          height: 1.35,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          if (_userHeightInches == null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _glassCard(
                padding: const EdgeInsets.all(12),
                radius: 14,
                tintColor: _Jovi.sky,
                tintOpacity: 0.06,
                child: Row(
                  children: [
                    Icon(Icons.height_rounded, color: _Jovi.sky, size: 20),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Set height for BMI',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          SizedBox(height: 2),
                          Text(
                            'Required for weight classification.',
                            style: TextStyle(
                              color: Color(0xBBFFFFFF),
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    _Pressable(
                      onTap: _showHeightDialog,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 7),
                        decoration: BoxDecoration(
                          gradient: _Jovi.coralGradient,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Text(
                          'Set',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 11.5,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ...VitalType.values.map((t) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _buildGoalCard(t),
              )),
        ],
      ),
    );
  }

  Widget _buildGoalCard(VitalType t) {
    final goal = _goals[t] ?? VitalGoal.defaultFor(t)!;
    final readings = _readingsInRange(t);
    final stats = _computeStats(readings);
    final color = _Jovi.vitalColor(t);

    String currentStatus = '—';
    bool atGoal = false;
    if (stats.average != null) {
      if (t == VitalType.bloodPressure && stats.secondaryAverage != null) {
        currentStatus =
            'Avg ${stats.average!.toInt()}/${stats.secondaryAverage!.toInt()}';
        if (goal.primaryMax != null && goal.secondaryMax != null) {
          atGoal = stats.average! <= goal.primaryMax! &&
              stats.secondaryAverage! <= goal.secondaryMax!;
        }
      } else {
        currentStatus = 'Avg ${_formatStatValue(t, stats.average!, null)}';
        if (goal.primaryMax != null) {
          atGoal = stats.average! <= goal.primaryMax!;
        }
        if (goal.primaryMin != null) {
          atGoal = atGoal && stats.average! >= goal.primaryMin!;
        }
        if (goal.target != null) {
          atGoal = (stats.average! - goal.target!).abs() <= 2;
        }
      }
    }

    String goalText = _goalSummary(t, goal);

    return _glassCard(
      padding: const EdgeInsets.all(14),
      radius: 16,
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
                child: Icon(_vitalIcon(t), color: color, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      t.label,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      currentStatus,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.65),
                        fontSize: 11.5,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              if (stats.average != null)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: atGoal
                        ? _Jovi.mint.withOpacity(0.2)
                        : _Jovi.gold.withOpacity(0.2),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color:
                          (atGoal ? _Jovi.mint : _Jovi.gold).withOpacity(0.5),
                      width: 1,
                    ),
                  ),
                  child: Text(
                    atGoal ? 'AT GOAL' : 'OFF GOAL',
                    style: TextStyle(
                      color: atGoal ? _Jovi.mint : _Jovi.gold,
                      fontSize: 9.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.6,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.04),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: Colors.white.withOpacity(0.08),
                width: 1,
              ),
            ),
            child: Row(
              children: [
                Icon(Icons.flag_outlined,
                    color: Colors.white.withOpacity(0.6), size: 14),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    'Goal: $goalText',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                _Pressable(
                  onTap: () => _editGoal(t),
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: _Jovi.coral.withOpacity(0.18),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: _Jovi.coral.withOpacity(0.45),
                        width: 1,
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Icon(Icons.edit_rounded, color: _Jovi.coral, size: 12),
                        SizedBox(width: 4),
                        Text(
                          'Edit',
                          style: TextStyle(
                            color: _Jovi.coral,
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
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
      ),
    );
  }

  String _goalSummary(VitalType t, VitalGoal g) {
    if (t == VitalType.bloodPressure) {
      if (g.primaryMax != null && g.secondaryMax != null) {
        return '≤ ${g.primaryMax!.toInt()}/${g.secondaryMax!.toInt()} mmHg';
      }
      return 'Not set';
    }
    if (t == VitalType.heartRate) {
      if (g.primaryMin != null && g.primaryMax != null) {
        return '${g.primaryMin!.toInt()}–${g.primaryMax!.toInt()} bpm';
      }
      return 'Not set';
    }
    if (t == VitalType.bloodGlucose) {
      if (g.primaryMax != null) return '≤ ${g.primaryMax!.toInt()} mg/dL';
      return 'Not set';
    }
    if (t == VitalType.weight) {
      if (g.target != null) return '${g.target!.toStringAsFixed(1)} lbs';
      return 'Not set';
    }
    if (t == VitalType.oxygen) {
      if (g.primaryMin != null) return '≥ ${g.primaryMin!.toInt()}%';
      return 'Not set';
    }
    if (t == VitalType.temperature) {
      if (g.primaryMin != null && g.primaryMax != null) {
        return '${g.primaryMin!.toStringAsFixed(1)}–${g.primaryMax!.toStringAsFixed(1)}°F';
      }
      return 'Not set';
    }
    return 'Not set';
  }

  void _editGoal(VitalType t) {
    final goal = _goals[t] ?? VitalGoal.defaultFor(t)!;

    final pMinCtrl = TextEditingController(
      text: goal.primaryMin
              ?.toStringAsFixed(t == VitalType.temperature ? 1 : 0) ??
          '',
    );
    final pMaxCtrl = TextEditingController(
      text: goal.primaryMax
              ?.toStringAsFixed(t == VitalType.temperature ? 1 : 0) ??
          '',
    );
    final sMaxCtrl = TextEditingController(
      text: goal.secondaryMax?.toStringAsFixed(0) ?? '',
    );
    final targetCtrl = TextEditingController(
      text: goal.target?.toStringAsFixed(1) ?? '',
    );

    _showNavyDialog(
      child: StatefulBuilder(
        builder: (ctx, setDialog) {
          Future<void> saveGoal() async {
            final newGoal = VitalGoal(
              type: t,
              primaryMin: double.tryParse(pMinCtrl.text),
              primaryMax: double.tryParse(pMaxCtrl.text),
              secondaryMax: double.tryParse(sMaxCtrl.text),
              target: double.tryParse(targetCtrl.text),
            );

            setState(() => _goals[t] = newGoal);

            // Persist to Firestore
            try {
              final allGoalsMap = <String, dynamic>{};
              for (final entry in _goals.entries) {
                allGoalsMap[entry.key.key] = entry.value.toMap();
              }
              await _goalsRef.set(allGoalsMap, SetOptions(merge: true));
              if (!mounted) return;
              Navigator.of(ctx).pop();
              _showSnack('Goal saved');
            } catch (_) {
              Navigator.of(ctx).pop();
              _showSnack('Couldn\'t save goal', isError: true);
            }
          }

          List<Widget> fields = [];

          // Compose the right input fields per vital type
          if (t == VitalType.bloodPressure) {
            fields = [
              _goalInputField(pMaxCtrl, 'Systolic Max', 'mmHg', _Jovi.softRed),
              const SizedBox(height: 10),
              _goalInputField(sMaxCtrl, 'Diastolic Max', 'mmHg', _Jovi.sky),
              const SizedBox(height: 14),
              const Text(
                'Common targets:',
                style: TextStyle(
                    color: Color(0x99FFFFFF),
                    fontSize: 11,
                    fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  _goalPresetChip('Normal 120/80', () {
                    setDialog(() {
                      pMaxCtrl.text = '120';
                      sMaxCtrl.text = '80';
                    });
                  }),
                  _goalPresetChip('Elevated 130/80', () {
                    setDialog(() {
                      pMaxCtrl.text = '130';
                      sMaxCtrl.text = '80';
                    });
                  }),
                  _goalPresetChip('Stage 1 140/90', () {
                    setDialog(() {
                      pMaxCtrl.text = '140';
                      sMaxCtrl.text = '90';
                    });
                  }),
                ],
              ),
            ];
          } else if (t == VitalType.heartRate) {
            fields = [
              _goalInputField(pMinCtrl, 'Rest HR Min', 'bpm', _Jovi.mint),
              const SizedBox(height: 10),
              _goalInputField(pMaxCtrl, 'Rest HR Max', 'bpm', _Jovi.softRed),
            ];
          } else if (t == VitalType.bloodGlucose) {
            fields = [
              _goalInputField(pMaxCtrl, 'Fasting Max', 'mg/dL', _Jovi.violet),
              const SizedBox(height: 14),
              const Text(
                'Common targets:',
                style: TextStyle(
                    color: Color(0x99FFFFFF),
                    fontSize: 11,
                    fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  _goalPresetChip('Normal ≤ 100', () {
                    setDialog(() => pMaxCtrl.text = '100');
                  }),
                  _goalPresetChip('Prediabetes ≤ 125', () {
                    setDialog(() => pMaxCtrl.text = '125');
                  }),
                  _goalPresetChip('Diabetes target ≤ 130', () {
                    setDialog(() => pMaxCtrl.text = '130');
                  }),
                ],
              ),
            ];
          } else if (t == VitalType.weight) {
            fields = [
              _goalInputField(targetCtrl, 'Target Weight', 'lbs', _Jovi.sky),
            ];
          } else if (t == VitalType.oxygen) {
            fields = [
              _goalInputField(pMinCtrl, 'SpO2 Min', '%', _Jovi.mint),
            ];
          } else if (t == VitalType.temperature) {
            fields = [
              _goalInputField(pMinCtrl, 'Normal Min', '°F', _Jovi.sky),
              const SizedBox(height: 10),
              _goalInputField(pMaxCtrl, 'Normal Max', '°F', _Jovi.coral),
            ];
          }

          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 34,
                    height: 34,
                    decoration: BoxDecoration(
                      color: _Jovi.vitalColor(t).withOpacity(0.18),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: _Jovi.vitalColor(t).withOpacity(0.4),
                        width: 1,
                      ),
                    ),
                    child: Icon(
                      _vitalIcon(t),
                      color: _Jovi.vitalColor(t),
                      size: 18,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Edit ${t.label} Goal',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              ...fields,
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: _secondaryButton(
                      label: 'Cancel',
                      onTap: () => Navigator.of(ctx).pop(),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _primaryButton(
                      label: 'Save',
                      onTap: saveGoal,
                    ),
                  ),
                ],
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _goalInputField(
    TextEditingController ctrl,
    String label,
    String unit,
    Color accent,
  ) {
    return _glassCard(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      radius: 12,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label.toUpperCase(),
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.6),
                    fontSize: 9.5,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                  ),
                ),
                TextField(
                  controller: ctrl,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(
                        RegExp(r'^\d+\.?\d{0,1}')),
                    LengthLimitingTextInputFormatter(6),
                  ],
                  style: TextStyle(
                    color: accent,
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    letterSpacing: -0.3,
                  ),
                  decoration: const InputDecoration(
                    border: InputBorder.none,
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(vertical: 4),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 6),
          Text(
            unit,
            style: TextStyle(
              color: Colors.white.withOpacity(0.55),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _goalPresetChip(String label, VoidCallback onTap) {
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(100),
          border: Border.all(
            color: Colors.white.withOpacity(0.18),
            width: 1,
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 10.5,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // MAIN BUILD
  // ═══════════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final cfg = _config(constraints);
          return Container(
            width: widget.width ?? double.infinity,
            height: widget.height ?? double.infinity,
            decoration: BoxDecoration(gradient: _Jovi.navyGradient),
            child: Stack(
              children: [
                // Ambient coral haze (top-left)
                Positioned(
                  top: -100,
                  left: -80,
                  child: Container(
                    width: 280,
                    height: 280,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          _Jovi.coral.withOpacity(0.18),
                          _Jovi.coral.withOpacity(0.0),
                        ],
                      ),
                    ),
                  ),
                ),
                // Ambient mint haze (bottom-right)
                Positioned(
                  bottom: -120,
                  right: -90,
                  child: Container(
                    width: 300,
                    height: 300,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          _Jovi.mint.withOpacity(0.15),
                          _Jovi.mint.withOpacity(0.0),
                        ],
                      ),
                    ),
                  ),
                ),
                SafeArea(
                  child: Column(
                    children: [
                      _buildTopBar(),
                      _buildTabBar(),
                      Expanded(
                        child: _isLoading
                            ? _buildLoadingView()
                            : FadeTransition(
                                opacity: _fadeAnimation,
                                child: _buildCurrentTab(cfg),
                              ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildLoadingView() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 36,
            height: 36,
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              valueColor: AlwaysStoppedAnimation(_Jovi.coral),
            ),
          ),
          const SizedBox(height: 14),
          Text(
            'Loading your vitals…',
            style: TextStyle(
              color: Colors.white.withOpacity(0.75),
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTopBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 6),
      child: Row(
        children: [
          // Back button
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () {
                HapticFeedback.lightImpact();
                if (Navigator.of(context).canPop()) {
                  Navigator.of(context).pop();
                }
              },
              child: _glassCard(
                padding: const EdgeInsets.all(9),
                radius: 12,
                child: const Icon(Icons.arrow_back_ios_new_rounded,
                    color: Colors.white, size: 16),
              ),
            ),
          ),
          const Spacer(),
          // Title
          Column(
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ShaderMask(
                    shaderCallback: (r) => _Jovi.coralGradient.createShader(r),
                    child: const Text(
                      'jovi',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -0.3,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.15),
                        width: 1,
                      ),
                    ),
                    child: const Text(
                      'VITALS',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                ],
              ),
              Text(
                'Track · Trend · Improve',
                style: TextStyle(
                  color: Colors.white.withOpacity(0.55),
                  fontSize: 9.5,
                  fontWeight: FontWeight.w500,
                  letterSpacing: 0.3,
                ),
              ),
            ],
          ),
          const Spacer(),
          // Refresh
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () {
                HapticFeedback.lightImpact();
                _loadData();
              },
              child: _glassCard(
                padding: const EdgeInsets.all(9),
                radius: 12,
                child: const Icon(Icons.refresh_rounded,
                    color: Colors.white, size: 16),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabBar() {
    final insights = _isLoading ? <Insight>[] : _generateInsights();
    final urgentCount = insights
        .where((i) =>
            i.severity == InsightSeverity.urgent ||
            i.severity == InsightSeverity.concern)
        .length;

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
      child: _glassCard(
        padding: const EdgeInsets.all(4),
        radius: 100,
        child: Row(
          children: [
            _tabChip(
                _Tab.dashboard, 'Home', Icons.space_dashboard_rounded, null),
            _tabChip(_Tab.trends, 'Trends', Icons.show_chart_rounded, null),
            _tabChip(_Tab.insights, 'Insights', Icons.psychology_rounded,
                urgentCount),
            _tabChip(_Tab.log, 'Log', Icons.list_alt_rounded, null),
            _tabChip(_Tab.goals, 'Goals', Icons.flag_rounded, null),
          ],
        ),
      ),
    );
  }

  Widget _tabChip(_Tab tab, String label, IconData icon, int? badge) {
    final sel = _tab == tab;
    return Expanded(
      child: _Pressable(
        onTap: () {
          HapticFeedback.selectionClick();
          setState(() {
            _tab = tab;
            _chartCursorX = null;
          });
          _fadeController
            ..reset()
            ..forward();
        },
        child: AnimatedContainer(
          duration: _Motion.select,
          curve: _Motion.settle,
          padding: const EdgeInsets.symmetric(vertical: 9),
          constraints: const BoxConstraints(minHeight: 40),
          decoration: BoxDecoration(
            gradient: sel ? _Jovi.coralGradient : null,
            borderRadius: BorderRadius.circular(100),
            boxShadow: sel
                ? [
                    BoxShadow(
                      color: _Jovi.coral.withOpacity(0.35),
                      blurRadius: 10,
                      offset: const Offset(0, 3),
                    ),
                  ]
                : null,
          ),
          child: Stack(
            clipBehavior: Clip.none,
            alignment: Alignment.center,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    icon,
                    color: sel ? Colors.white : Colors.white.withOpacity(0.65),
                    size: 13,
                  ),
                  const SizedBox(width: 5),
                  Flexible(
                    child: Text(
                      label,
                      style: TextStyle(
                        color:
                            sel ? Colors.white : Colors.white.withOpacity(0.75),
                        fontSize: 10.5,
                        fontWeight: sel ? FontWeight.w700 : FontWeight.w500,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              if (badge != null && badge > 0)
                Positioned(
                  top: -6,
                  right: -2,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                    constraints:
                        const BoxConstraints(minWidth: 14, minHeight: 14),
                    decoration: BoxDecoration(
                      color: _Jovi.errorRed,
                      borderRadius: BorderRadius.circular(100),
                      border: Border.all(
                        color: _Jovi.navy,
                        width: 1.5,
                      ),
                    ),
                    child: Text(
                      badge > 9 ? '9+' : badge.toString(),
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 8.5,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCurrentTab(ResponsiveConfig cfg) {
    switch (_tab) {
      case _Tab.dashboard:
        return _buildDashboardTab(cfg);
      case _Tab.trends:
        return _buildTrendsTab(cfg);
      case _Tab.insights:
        return _buildInsightsTab(cfg);
      case _Tab.log:
        return _buildLogTab(cfg);
      case _Tab.goals:
        return _buildGoalsTab(cfg);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// CHART DATA
// ═══════════════════════════════════════════════════════════════════════════

class ChartAnnotation {
  final DateTime timestamp;
  final String label;
  final Color color;

  ChartAnnotation({
    required this.timestamp,
    required this.label,
    required this.color,
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// SPARKLINE PAINTER
// Minimal area-under-line chart used on dashboard vital cards.
// ═══════════════════════════════════════════════════════════════════════════

class _SparklinePainter extends CustomPainter {
  final List<VitalReading> readings; // oldest -> newest
  final Color color;
  final Color? secondaryColor; // used for BP diastolic

  _SparklinePainter({
    required this.readings,
    required this.color,
    this.secondaryColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (readings.length < 2) return;

    final primary =
        readings.where((r) => r.value != null).map((r) => r.value!).toList();
    if (primary.isEmpty) return;

    _drawSeries(canvas, size, primary, color, filled: true);

    if (secondaryColor != null) {
      final sec = readings
          .where((r) => r.secondary != null)
          .map((r) => r.secondary!)
          .toList();
      if (sec.isNotEmpty) {
        _drawSeries(canvas, size, sec, secondaryColor!, filled: false);
      }
    }
  }

  void _drawSeries(
    Canvas canvas,
    Size size,
    List<double> values,
    Color lineColor, {
    bool filled = false,
  }) {
    final minV = values.reduce(math.min);
    final maxV = values.reduce(math.max);
    final range = (maxV - minV) == 0 ? 1.0 : (maxV - minV);

    final points = <Offset>[];
    for (int i = 0; i < values.length; i++) {
      final x = (i / (values.length - 1)) * size.width;
      final norm = (values[i] - minV) / range;
      final y = size.height - (norm * size.height * 0.82) - 3;
      points.add(Offset(x, y));
    }

    if (filled) {
      final fillPath = Path()..moveTo(points.first.dx, size.height);
      for (final p in points) {
        fillPath.lineTo(p.dx, p.dy);
      }
      fillPath.lineTo(points.last.dx, size.height);
      fillPath.close();

      final fillPaint = Paint()
        ..shader = LinearGradient(
          colors: [
            lineColor.withOpacity(0.28),
            lineColor.withOpacity(0.02),
          ],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ).createShader(Rect.fromLTWH(0, 0, size.width, size.height));
      canvas.drawPath(fillPath, fillPaint);
    }

    final linePaint = Paint()
      ..color = lineColor
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final linePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (int i = 1; i < points.length; i++) {
      linePath.lineTo(points[i].dx, points[i].dy);
    }
    canvas.drawPath(linePath, linePaint);

    // Draw a final marker dot
    canvas.drawCircle(
      points.last,
      2.5,
      Paint()..color = lineColor,
    );
    canvas.drawCircle(
      points.last,
      4.5,
      Paint()
        ..color = lineColor.withOpacity(0.25)
        ..style = PaintingStyle.fill,
    );
  }

  @override
  bool shouldRepaint(covariant _SparklinePainter old) {
    return old.readings.length != readings.length ||
        old.readings != readings ||
        old.color != color;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// INTERACTIVE CHART PAINTER
// Full chart with pan/zoom, goal lines, annotations, and crosshair tooltip.
// ═══════════════════════════════════════════════════════════════════════════

class _InteractiveChartPainter extends CustomPainter {
  final List<VitalReading> readings; // oldest -> newest
  final VitalType vitalType;
  final Color primaryColor;
  final Color? secondaryColor;
  final double? cursorX; // 0-1 normalized position
  final double scale; // 1.0 - 8.0
  final double panOffset; // normalized
  final List<double> goalLines;
  final List<Color> goalLineColors;
  final List<ChartAnnotation> annotations;

  _InteractiveChartPainter({
    required this.readings,
    required this.vitalType,
    required this.primaryColor,
    this.secondaryColor,
    this.cursorX,
    this.scale = 1.0,
    this.panOffset = 0.0,
    this.goalLines = const [],
    this.goalLineColors = const [],
    this.annotations = const [],
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (readings.isEmpty) {
      _drawEmpty(canvas, size);
      return;
    }

    // Layout: leave padding for labels
    const leftPad = 36.0;
    const rightPad = 8.0;
    const topPad = 12.0;
    const bottomPad = 24.0;

    final chartRect = Rect.fromLTWH(
      leftPad,
      topPad,
      size.width - leftPad - rightPad,
      size.height - topPad - bottomPad,
    );

    // Gather all visible values to compute y-range
    final primaryVals =
        readings.where((r) => r.value != null).map((r) => r.value!).toList();
    final secondaryVals = secondaryColor != null
        ? readings
            .where((r) => r.secondary != null)
            .map((r) => r.secondary!)
            .toList()
        : <double>[];

    final allY = [...primaryVals, ...secondaryVals, ...goalLines];
    if (allY.isEmpty) {
      _drawEmpty(canvas, size);
      return;
    }
    var minY = allY.reduce(math.min);
    var maxY = allY.reduce(math.max);

    // Add some headroom and snap to sensible values
    final range = (maxY - minY);
    if (range < 10) {
      // Expand tiny ranges
      minY -= 5;
      maxY += 5;
    } else {
      minY -= range * 0.1;
      maxY += range * 0.1;
    }
    // Snap for specific vitals to clinical ranges
    if (vitalType == VitalType.bloodPressure) {
      minY = math.min(minY, 60);
      maxY = math.max(maxY, 160);
    } else if (vitalType == VitalType.oxygen) {
      minY = math.max(minY, 80);
      maxY = 100;
    } else if (vitalType == VitalType.temperature) {
      minY = math.min(minY, 96);
      maxY = math.max(maxY, 102);
    }

    // X range (time range)
    final tStart = readings.first.timestamp.millisecondsSinceEpoch.toDouble();
    final tEnd = readings.last.timestamp.millisecondsSinceEpoch.toDouble();
    var tSpan = tEnd - tStart;
    if (tSpan <= 0) tSpan = 1;

    // Apply zoom and pan: narrow the visible window
    final visibleSpan = tSpan / scale;
    final center = (tStart + tEnd) / 2 + (panOffset * tSpan);
    var visStart = center - visibleSpan / 2;
    var visEnd = center + visibleSpan / 2;
    if (visStart < tStart) {
      visEnd += (tStart - visStart);
      visStart = tStart;
    }
    if (visEnd > tEnd) {
      visStart -= (visEnd - tEnd);
      visEnd = tEnd;
    }
    final visSpan = visEnd - visStart;

    // Convert timestamp to x pixel
    double tsToX(double ts) {
      final norm = (ts - visStart) / visSpan;
      return chartRect.left + norm * chartRect.width;
    }

    double vToY(double v) {
      final norm = (v - minY) / (maxY - minY);
      return chartRect.bottom - norm * chartRect.height;
    }

    // ─── BACKGROUND GRID ──────────────────────────────────────────────────
    final gridPaint = Paint()
      ..color = Colors.white.withOpacity(0.06)
      ..strokeWidth = 0.5;
    final dashGridPaint = Paint()
      ..color = Colors.white.withOpacity(0.04)
      ..strokeWidth = 0.5;

    // Horizontal gridlines with labels
    final labelStyle = TextStyle(
      color: Colors.white.withOpacity(0.5),
      fontSize: 9,
      fontWeight: FontWeight.w600,
    );

    const gridLines = 4;
    for (int i = 0; i <= gridLines; i++) {
      final t = i / gridLines;
      final y = chartRect.bottom - t * chartRect.height;
      canvas.drawLine(
        Offset(chartRect.left, y),
        Offset(chartRect.right, y),
        gridPaint,
      );
      final value = minY + t * (maxY - minY);
      String label;
      if (vitalType == VitalType.weight || vitalType == VitalType.temperature) {
        label = value.toStringAsFixed(1);
      } else {
        label = value.toInt().toString();
      }
      final tp = TextPainter(
        text: TextSpan(text: label, style: labelStyle),
        textDirection: ui.TextDirection.ltr,
      )..layout();
      tp.paint(
        canvas,
        Offset(chartRect.left - tp.width - 4, y - tp.height / 2),
      );
    }

    // Vertical date ticks
    final dateCount = 4;
    for (int i = 0; i <= dateCount; i++) {
      final t = i / dateCount;
      final x = chartRect.left + t * chartRect.width;
      canvas.drawLine(
        Offset(x, chartRect.top),
        Offset(x, chartRect.bottom),
        dashGridPaint,
      );
      final ts = visStart + t * visSpan;
      final date = DateTime.fromMillisecondsSinceEpoch(ts.toInt());
      final label = '${date.month}/${date.day}';
      final tp = TextPainter(
        text: TextSpan(text: label, style: labelStyle),
        textDirection: ui.TextDirection.ltr,
      )..layout();
      tp.paint(
        canvas,
        Offset(x - tp.width / 2, chartRect.bottom + 6),
      );
    }

    // ─── GOAL LINES ─────────────────────────────────────────────────────────
    for (int i = 0; i < goalLines.length; i++) {
      final gv = goalLines[i];
      if (gv < minY || gv > maxY) continue;
      final gc = goalLineColors[i % goalLineColors.length];
      final y = vToY(gv);
      final goalPaint = Paint()
        ..color = gc.withOpacity(0.6)
        ..strokeWidth = 1.2;
      _drawDashedLine(
        canvas,
        Offset(chartRect.left, y),
        Offset(chartRect.right, y),
        goalPaint,
      );
      // Small label on right
      final labelTp = TextPainter(
        text: TextSpan(
          text: vitalType == VitalType.weight ||
                  vitalType == VitalType.temperature
              ? gv.toStringAsFixed(1)
              : gv.toInt().toString(),
          style: TextStyle(
            color: gc,
            fontSize: 8.5,
            fontWeight: FontWeight.w700,
          ),
        ),
        textDirection: ui.TextDirection.ltr,
      )..layout();
      final labelBg = Paint()..color = const Color(0xFF0F1A2E);
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(
              chartRect.right - labelTp.width - 6,
              y - labelTp.height / 2 - 1,
              labelTp.width + 4,
              labelTp.height + 2),
          const Radius.circular(3),
        ),
        labelBg,
      );
      labelTp.paint(
        canvas,
        Offset(chartRect.right - labelTp.width - 4, y - labelTp.height / 2),
      );
    }

    // ─── ANNOTATIONS (med start lines) ─────────────────────────────────────
    for (final ann in annotations) {
      final ts = ann.timestamp.millisecondsSinceEpoch.toDouble();
      if (ts < visStart || ts > visEnd) continue;
      final x = tsToX(ts);
      final annPaint = Paint()
        ..color = ann.color.withOpacity(0.7)
        ..strokeWidth = 1.2;
      _drawDashedLine(
        canvas,
        Offset(x, chartRect.top),
        Offset(x, chartRect.bottom),
        annPaint,
      );
      // Small tag at top
      canvas.drawCircle(
          Offset(x, chartRect.top + 4), 3, Paint()..color = ann.color);
      // Label
      final labelTp = TextPainter(
        text: TextSpan(
          text: ann.label,
          style: TextStyle(
            color: ann.color,
            fontSize: 8.5,
            fontWeight: FontWeight.w700,
          ),
        ),
        textDirection: ui.TextDirection.ltr,
      )..layout(maxWidth: 90);
      final bgRect = Rect.fromLTWH(
        (x + 5).clamp(0, chartRect.right - labelTp.width - 4),
        chartRect.top - 2,
        labelTp.width + 4,
        labelTp.height + 2,
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(bgRect, const Radius.circular(3)),
        Paint()..color = const Color(0xFF0F1A2E).withOpacity(0.9),
      );
      labelTp.paint(canvas, Offset(bgRect.left + 2, bgRect.top + 1));
    }

    // ─── DATA SERIES ───────────────────────────────────────────────────────
    // Primary line
    final primaryPoints = <Offset>[];
    for (final r in readings) {
      if (r.value == null) continue;
      final ts = r.timestamp.millisecondsSinceEpoch.toDouble();
      if (ts < visStart - visSpan * 0.02 || ts > visEnd + visSpan * 0.02) {
        continue;
      }
      primaryPoints.add(Offset(tsToX(ts), vToY(r.value!)));
    }

    if (primaryPoints.length >= 2) {
      // Filled area
      final areaPath = Path()..moveTo(primaryPoints.first.dx, chartRect.bottom);
      for (final p in primaryPoints) {
        areaPath.lineTo(p.dx, p.dy);
      }
      areaPath.lineTo(primaryPoints.last.dx, chartRect.bottom);
      areaPath.close();

      canvas.drawPath(
        areaPath,
        Paint()
          ..shader = LinearGradient(
            colors: [
              primaryColor.withOpacity(0.32),
              primaryColor.withOpacity(0.02),
            ],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ).createShader(chartRect),
      );

      // Line
      final linePath = Path()
        ..moveTo(primaryPoints.first.dx, primaryPoints.first.dy);
      for (int i = 1; i < primaryPoints.length; i++) {
        linePath.lineTo(primaryPoints[i].dx, primaryPoints[i].dy);
      }
      canvas.drawPath(
        linePath,
        Paint()
          ..color = primaryColor
          ..strokeWidth = 2.2
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round,
      );

      // Points
      for (final p in primaryPoints) {
        canvas.drawCircle(p, 3, Paint()..color = const Color(0xFF0F1A2E));
        canvas.drawCircle(p, 2.2, Paint()..color = primaryColor);
      }
    } else if (primaryPoints.length == 1) {
      canvas.drawCircle(primaryPoints.first, 4, Paint()..color = primaryColor);
    }

    // Secondary (BP diastolic)
    if (secondaryColor != null) {
      final secPoints = <Offset>[];
      for (final r in readings) {
        if (r.secondary == null) continue;
        final ts = r.timestamp.millisecondsSinceEpoch.toDouble();
        if (ts < visStart - visSpan * 0.02 || ts > visEnd + visSpan * 0.02) {
          continue;
        }
        secPoints.add(Offset(tsToX(ts), vToY(r.secondary!)));
      }
      if (secPoints.length >= 2) {
        final path = Path()..moveTo(secPoints.first.dx, secPoints.first.dy);
        for (int i = 1; i < secPoints.length; i++) {
          path.lineTo(secPoints[i].dx, secPoints[i].dy);
        }
        canvas.drawPath(
          path,
          Paint()
            ..color = secondaryColor!
            ..strokeWidth = 1.8
            ..style = PaintingStyle.stroke
            ..strokeCap = StrokeCap.round,
        );
        for (final p in secPoints) {
          canvas.drawCircle(p, 2.5, Paint()..color = const Color(0xFF0F1A2E));
          canvas.drawCircle(p, 1.8, Paint()..color = secondaryColor!);
        }
      }
    }

    // ─── CROSSHAIR / TOOLTIP ──────────────────────────────────────────────
    if (cursorX != null && readings.isNotEmpty) {
      final cx = cursorX!.clamp(0.0, 1.0) * size.width;
      // Find nearest reading to cursor
      VitalReading? nearest;
      double bestDist = double.infinity;
      for (final r in readings) {
        final ts = r.timestamp.millisecondsSinceEpoch.toDouble();
        if (ts < visStart || ts > visEnd) continue;
        final x = tsToX(ts);
        final d = (x - cx).abs();
        if (d < bestDist) {
          bestDist = d;
          nearest = r;
        }
      }

      if (nearest != null && nearest.value != null) {
        final ts = nearest.timestamp.millisecondsSinceEpoch.toDouble();
        final snapX = tsToX(ts);

        // Crosshair line
        canvas.drawLine(
          Offset(snapX, chartRect.top),
          Offset(snapX, chartRect.bottom),
          Paint()
            ..color = Colors.white.withOpacity(0.4)
            ..strokeWidth = 1,
        );

        // Dot
        final y = vToY(nearest.value!);
        canvas.drawCircle(Offset(snapX, y), 6,
            Paint()..color = primaryColor.withOpacity(0.3));
        canvas.drawCircle(Offset(snapX, y), 4, Paint()..color = Colors.white);
        canvas.drawCircle(Offset(snapX, y), 2.5, Paint()..color = primaryColor);

        // Build tooltip content
        final dt = nearest.timestamp;
        final hour = dt.hour == 0
            ? 12
            : dt.hour > 12
                ? dt.hour - 12
                : dt.hour;
        final period = dt.hour >= 12 ? 'PM' : 'AM';
        final minute = dt.minute.toString().padLeft(2, '0');
        final valueStr = nearest.displayValue;
        final dateStr = '${dt.month}/${dt.day} · $hour:$minute $period';

        final valuePainter = TextPainter(
          text: TextSpan(
            text: '$valueStr ${vitalType.unit}',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w800,
            ),
          ),
          textDirection: ui.TextDirection.ltr,
        )..layout();
        final datePainter = TextPainter(
          text: TextSpan(
            text: dateStr,
            style: TextStyle(
              color: Colors.white.withOpacity(0.7),
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
          textDirection: ui.TextDirection.ltr,
        )..layout();

        final boxW = math.max(valuePainter.width, datePainter.width) + 14;
        final boxH = valuePainter.height + datePainter.height + 10;
        var boxLeft = snapX + 10;
        if (boxLeft + boxW > size.width) boxLeft = snapX - boxW - 10;
        if (boxLeft < 0) boxLeft = 4;
        var boxTop = y - boxH - 8;
        if (boxTop < 0) boxTop = y + 10;

        final boxRect = Rect.fromLTWH(boxLeft, boxTop, boxW, boxH);
        canvas.drawRRect(
          RRect.fromRectAndRadius(boxRect, const Radius.circular(8)),
          Paint()..color = const Color(0xFF0F1A2E).withOpacity(0.95),
        );
        canvas.drawRRect(
          RRect.fromRectAndRadius(boxRect, const Radius.circular(8)),
          Paint()
            ..color = primaryColor.withOpacity(0.5)
            ..strokeWidth = 1
            ..style = PaintingStyle.stroke,
        );

        valuePainter.paint(canvas, Offset(boxLeft + 7, boxTop + 5));
        datePainter.paint(
            canvas, Offset(boxLeft + 7, boxTop + 5 + valuePainter.height));
      }
    }
  }

  void _drawDashedLine(Canvas canvas, Offset start, Offset end, Paint paint) {
    const dashLen = 4.0;
    const gapLen = 3.0;
    final dx = end.dx - start.dx;
    final dy = end.dy - start.dy;
    final dist = math.sqrt(dx * dx + dy * dy);
    final step = dashLen + gapLen;
    final steps = (dist / step).floor();
    final nx = dx / dist;
    final ny = dy / dist;
    for (int i = 0; i <= steps; i++) {
      final s = i * step;
      final e = math.min(s + dashLen, dist);
      if (s >= dist) break;
      canvas.drawLine(
        Offset(start.dx + nx * s, start.dy + ny * s),
        Offset(start.dx + nx * e, start.dy + ny * e),
        paint,
      );
    }
  }

  void _drawEmpty(Canvas canvas, Size size) {
    final tp = TextPainter(
      text: TextSpan(
        text: 'No data',
        style: TextStyle(
          color: Colors.white.withOpacity(0.3),
          fontSize: 13,
          fontWeight: FontWeight.w600,
        ),
      ),
      textDirection: ui.TextDirection.ltr,
    )..layout();
    tp.paint(
      canvas,
      Offset(size.width / 2 - tp.width / 2, size.height / 2 - tp.height / 2),
    );
  }

  @override
  bool shouldRepaint(covariant _InteractiveChartPainter old) {
    return old.readings != readings ||
        old.cursorX != cursorX ||
        old.scale != scale ||
        old.panOffset != panOffset ||
        old.vitalType != vitalType;
  }
}
