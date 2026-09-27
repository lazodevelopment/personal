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
// JOVI HEALTH - LANDING PAGE (REBRANDED + PET LOGIC)
// Version: 2026.09.22-r3 (Apple HIG pass: press feedback, no looping motion,
//          draggable quote sheet fixed, Reduce Motion, navy toasts)
// r2:      2026.04.16 (pet plan + clinic visits + plan terminology)
// Build: JC-LP-0922-003
// Section 1 of 3: Imports, Constants, Breed Lists, Bottom Sheet State
// ============================================================

import 'package:flutter/services.dart'; // For haptic feedback
import 'package:flutter/cupertino.dart';
import 'dart:async'; // For Timer
import 'dart:ui' as ui_dart; // For display features
import 'package:firebase_analytics/firebase_analytics.dart'; // For analytics

/// Enumerations for device categorization
enum ScreenType { compact, medium, expanded, large }

/// Configuration object for responsive layouts
class ResponsiveConfig {
  final double paddingH;
  final double paddingV;
  final double contentMax;
  final double headingSize;
  final double bodySize;
  final double logoScale;
  final double buttonHeight;
  final double iconSize;
  final bool wideMode;
  final bool hasHinge;
  final bool useTwoColumnLayout;
  final bool useGridLayout;

  ResponsiveConfig({
    required this.paddingH,
    required this.paddingV,
    required this.contentMax,
    required this.headingSize,
    required this.bodySize,
    required this.logoScale,
    required this.buttonHeight,
    required this.iconSize,
    required this.wideMode,
    required this.hasHinge,
    this.useTwoColumnLayout = false,
    this.useGridLayout = false,
  });
}

// Jovi Health Brand Colors
const Color joviCoral = Color(0xFFFF6B4A);
const Color joviCoralLight = Color(0xFFFF8F73);
const Color joviNavy = Color(0xFF1A2744);
const Color joviNavyDark = Color(0xFF0F1A2E);
const Color joviWarmWhite = Color(0xFFFFF8F5);
const Color joviMint = Color(0xFF00D4AA);
const Color joviMintDark = Color(0xFF00B894);
const Color joviGold = Color(0xFFFFD166);
const Color joviSoftStone = Color(0xFFF0EFEB);

// Pet breed lists (from onboarding widget)
const List<String> dogBreeds = [
  'Affenpinscher',
  'Afghan Hound',
  'Airedale Terrier',
  'Akita',
  'Alaskan Malamute',
  'American Bulldog',
  'American Eskimo Dog',
  'American Staffordshire Terrier',
  'Australian Cattle Dog',
  'Australian Shepherd',
  'Basenji',
  'Basset Hound',
  'Beagle',
  'Bearded Collie',
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
  'Chow Chow',
  'Cocker Spaniel',
  'Collie',
  'Corgi',
  'Dachshund',
  'Dalmatian',
  'Doberman Pinscher',
  'English Setter',
  'English Springer Spaniel',
  'French Bulldog',
  'German Shepherd',
  'German Shorthaired Pointer',
  'Golden Retriever',
  'Great Dane',
  'Great Pyrenees',
  'Greyhound',
  'Havanese',
  'Irish Setter',
  'Irish Wolfhound',
  'Jack Russell Terrier',
  'Japanese Chin',
  'Labrador Retriever',
  'Lhasa Apso',
  'Maltese',
  'Mastiff',
  'Miniature Pinscher',
  'Miniature Schnauzer',
  'Newfoundland',
  'Old English Sheepdog',
  'Papillon',
  'Pekingese',
  'Pembroke Welsh Corgi',
  'Pomeranian',
  'Poodle',
  'Pug',
  'Rhodesian Ridgeback',
  'Rottweiler',
  'Saint Bernard',
  'Samoyed',
  'Scottish Terrier',
  'Shetland Sheepdog',
  'Shiba Inu',
  'Shih Tzu',
  'Siberian Husky',
  'Staffordshire Bull Terrier',
  'Vizsla',
  'Weimaraner',
  'West Highland White Terrier',
  'Whippet',
  'Yorkshire Terrier',
  'Mixed Breed',
  'Other',
];

const List<String> catBreeds = [
  'Abyssinian',
  'American Shorthair',
  'Bengal',
  'Birman',
  'Bombay',
  'British Shorthair',
  'Burmese',
  'Chartreux',
  'Devon Rex',
  'Egyptian Mau',
  'Exotic Shorthair',
  'Himalayan',
  'Maine Coon',
  'Manx',
  'Norwegian Forest Cat',
  'Oriental',
  'Persian',
  'Ragdoll',
  'Russian Blue',
  'Scottish Fold',
  'Siamese',
  'Siberian',
  'Sphynx',
  'Tonkinese',
  'Turkish Angora',
  'Domestic Shorthair',
  'Domestic Longhair',
  'Mixed Breed',
  'Other',
];

const Map<String, int> dogBreedMaxAge = {
  'Affenpinscher': 15,
  'Afghan Hound': 14,
  'Airedale Terrier': 13,
  'Akita': 13,
  'Alaskan Malamute': 12,
  'American Bulldog': 15,
  'American Eskimo Dog': 16,
  'American Staffordshire Terrier': 14,
  'Australian Cattle Dog': 16,
  'Australian Shepherd': 15,
  'Basenji': 14,
  'Basset Hound': 13,
  'Beagle': 15,
  'Bearded Collie': 14,
  'Belgian Malinois': 14,
  'Bernese Mountain Dog': 8,
  'Bichon Frise': 16,
  'Bloodhound': 10,
  'Border Collie': 15,
  'Border Terrier': 14,
  'Boston Terrier': 13,
  'Boxer': 12,
  'Brittany': 14,
  'Brussels Griffon': 15,
  'Bull Terrier': 13,
  'Bulldog': 10,
  'Bullmastiff': 9,
  'Cairn Terrier': 15,
  'Cane Corso': 10,
  'Cavalier King Charles Spaniel': 14,
  'Chesapeake Bay Retriever': 13,
  'Chihuahua': 18,
  'Chinese Crested': 16,
  'Chow Chow': 12,
  'Cocker Spaniel': 14,
  'Collie': 14,
  'Corgi': 15,
  'Dachshund': 16,
  'Dalmatian': 13,
  'Doberman Pinscher': 12,
  'English Setter': 14,
  'English Springer Spaniel': 14,
  'French Bulldog': 12,
  'German Shepherd': 11,
  'German Shorthaired Pointer': 14,
  'Golden Retriever': 12,
  'Great Dane': 8,
  'Great Pyrenees': 12,
  'Greyhound': 13,
  'Havanese': 16,
  'Irish Setter': 14,
  'Irish Wolfhound': 8,
  'Jack Russell Terrier': 16,
  'Japanese Chin': 14,
  'Labrador Retriever': 13,
  'Lhasa Apso': 15,
  'Maltese': 15,
  'Mastiff': 10,
  'Miniature Pinscher': 15,
  'Miniature Schnauzer': 14,
  'Newfoundland': 10,
  'Old English Sheepdog': 12,
  'Papillon': 16,
  'Pekingese': 14,
  'Pembroke Welsh Corgi': 15,
  'Pomeranian': 16,
  'Poodle': 15,
  'Pug': 14,
  'Rhodesian Ridgeback': 12,
  'Rottweiler': 10,
  'Saint Bernard': 10,
  'Samoyed': 14,
  'Scottish Terrier': 13,
  'Shetland Sheepdog': 14,
  'Shiba Inu': 16,
  'Shih Tzu': 16,
  'Siberian Husky': 14,
  'Staffordshire Bull Terrier': 14,
  'Vizsla': 14,
  'Weimaraner': 13,
  'West Highland White Terrier': 15,
  'Whippet': 14,
  'Yorkshire Terrier': 16,
  'Mixed Breed': 14,
  'Other': 14,
};

const Map<String, int> catBreedMaxAge = {
  'Abyssinian': 15,
  'American Shorthair': 17,
  'Bengal': 16,
  'Birman': 16,
  'Bombay': 18,
  'British Shorthair': 17,
  'Burmese': 18,
  'Chartreux': 16,
  'Devon Rex': 15,
  'Egyptian Mau': 15,
  'Exotic Shorthair': 15,
  'Himalayan': 15,
  'Maine Coon': 14,
  'Manx': 16,
  'Norwegian Forest Cat': 16,
  'Oriental': 15,
  'Persian': 15,
  'Ragdoll': 17,
  'Russian Blue': 18,
  'Scottish Fold': 15,
  'Siamese': 20,
  'Siberian': 18,
  'Sphynx': 15,
  'Tonkinese': 16,
  'Turkish Angora': 18,
  'Domestic Shorthair': 17,
  'Domestic Longhair': 17,
  'Mixed Breed': 17,
  'Other': 16,
};

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration select = Duration(milliseconds: 220);
  static const Duration enter = Duration(milliseconds: 420);
  static const Curve settle = Curves.easeOutCubic;
}

/// Reads the platform Reduce Motion flag without needing a BuildContext, so
/// it is safe from initState.
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
    return Listener(
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

// ============================================================
// PREMIUM PREVIEW BOTTOM SHEET WIDGET (with Pet Support)
// ============================================================

class PremiumPreviewBottomSheetWidget extends StatefulWidget {
  const PremiumPreviewBottomSheetWidget({
    Key? key,
    required this.width,
    required this.height,
    this.scrollController,
  }) : super(key: key);

  final double width;
  final double height;

  /// Provided by DraggableScrollableSheet so the sheet can be dragged
  /// taller/shorter; without it the sheet was stuck at its initial size.
  final ScrollController? scrollController;

  @override
  PremiumPreviewBottomSheetWidgetState createState() =>
      PremiumPreviewBottomSheetWidgetState();
}

class PremiumPreviewBottomSheetWidgetState
    extends State<PremiumPreviewBottomSheetWidget>
    with TickerProviderStateMixin {
  // Form Controllers
  final _birthdate = TextEditingController();
  final _spouseBirth = TextEditingController();
  final _depBirth = <TextEditingController>[];

  // Family Options
  bool _spouse = false;
  int _numDeps = 0;

  // Coverage Options
  bool _tobacco = false;
  bool _dental = false;
  bool _vision = false;

  // ===== PET STATE (mirrors onboarding widget) =====
  int _numPets = 0;
  final _petName = <TextEditingController>[];
  final _petAge = <TextEditingController>[];
  final _petBirthdate = <TextEditingController>[];
  final _petType = <String>[];
  final _petBreed = <String>[];
  final List<bool> _petPreExistingAck = [];
  final List<TextEditingController> _petPreExistingControllers = [];
  final List<bool> _petCoverageExpanded = [];
  final List<String?> _petAgeWarnings = [];

  // Quote Data
  double _lastLoggedGrandTotal = -1; // only log analytics when the quote changes
  double _totalPremium = 0;
  double _petTotalPremium = 0;
  List<Map<String, dynamic>> _quotes = [];
  List<Map<String, dynamic>> _petQuotes = [];
  bool _showQuoteSummary = false;

  // Animation Controllers
  late AnimationController _slideController;
  late AnimationController _fadeController;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();

    // The modal route already slides the sheet up; a second full-height
    // slide on top of it read as a stutter. Keep a short settle + fade.
    _slideController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    _fadeController = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );

    _slideAnimation = Tween<Offset>(
      begin: _platformReduceMotion() ? Offset.zero : const Offset(0, 0.03),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _slideController, curve: _Motion.settle));

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _fadeController, curve: Curves.easeOut));

    _slideController.forward();
    _fadeController.forward();

    FirebaseAnalytics.instance.logEvent(name: 'premium_preview_opened');
  }

  @override
  void dispose() {
    _birthdate.dispose();
    _spouseBirth.dispose();
    for (var controller in _depBirth) {
      controller.dispose();
    }
    for (var controller in _petName) controller.dispose();
    for (var controller in _petAge) controller.dispose();
    for (var controller in _petBirthdate) controller.dispose();
    for (var controller in _petPreExistingControllers) controller.dispose();
    _slideController.dispose();
    _fadeController.dispose();
    super.dispose();
  }

  // ============================================================
  // PET LOGIC METHODS (from onboarding widget)
  // ============================================================

  // Same $60 base + $7/year formula as onboarding
  double _calculatePetPremium(int ageInMonths) {
    if (ageInMonths >= 8 && ageInMonths <= 11) return 60.0;
    int ageInYears = (ageInMonths / 12).floor();
    if (ageInYears >= 1 && ageInYears <= 20) {
      return 60.0 + ((ageInYears - 1) * 7.0);
    }
    return 60.0;
  }

  int _parseAgeToMonths(String ageText) {
    try {
      ageText = ageText.toLowerCase().trim();
      int totalMonths = 0;
      if (ageText.contains('year')) {
        final yearMatch = RegExp(r'(\d+)\s*year').firstMatch(ageText);
        if (yearMatch != null) {
          totalMonths += int.parse(yearMatch.group(1)!) * 12;
        }
      }
      if (ageText.contains('month')) {
        final monthMatch = RegExp(r'(\d+)\s*month').firstMatch(ageText);
        if (monthMatch != null) {
          totalMonths += int.parse(monthMatch.group(1)!);
        }
      }
      if (totalMonths == 0) {
        totalMonths =
            int.tryParse(ageText.replaceAll(RegExp(r'[^\d]'), '')) ?? 0;
      }
      return totalMonths;
    } catch (e) {
      return 0;
    }
  }

  void _updatePetAgeFromBirthdate(int petIndex) {
    if (petIndex >= _petBirthdate.length) return;
    final text = _petBirthdate[petIndex].text.trim();
    if (text.isEmpty) return;
    try {
      DateTime? birth;
      final parts = text.split('/');
      if (parts.length == 3) {
        final m = int.tryParse(parts[0]);
        final d = int.tryParse(parts[1]);
        final y = int.tryParse(parts[2]);
        if (m != null && d != null && y != null) birth = DateTime(y, m, d);
      }
      if (birth == null) return;
      final now = DateTime.now();
      if (birth.isAfter(now)) return;

      int years = now.year - birth.year;
      int months = now.month - birth.month;
      if (now.day < birth.day) months--;
      if (months < 0) {
        years--;
        months += 12;
      }

      String ageString;
      if (years == 0) {
        ageString = '$months month${months == 1 ? "" : "s"}';
      } else if (months == 0) {
        ageString = '$years year${years == 1 ? "" : "s"}';
      } else {
        ageString =
            '$years year${years == 1 ? "" : "s"} $months month${months == 1 ? "" : "s"}';
      }

      setState(() {
        while (_petAge.length <= petIndex) _petAge.add(TextEditingController());
        _petAge[petIndex].text = ageString;
      });
      _validatePetAge(petIndex);
      _computeQuote();
    } catch (e) {
      debugPrint('Error computing pet age from birthdate: $e');
    }
  }

  String _getPetAgeLabel(int petIndex) {
    if (petIndex >= _petAge.length || _petAge[petIndex].text.isEmpty) return '';
    final months = _parseAgeToMonths(_petAge[petIndex].text);
    final type = petIndex < _petType.length ? _petType[petIndex] : 'Dog';
    final isDog = type == 'Dog';
    if (months < 2) return '';
    if (months < 12) return isDog ? '\u{1F436} Puppy' : '\u{1F431} Kitten';
    if (isDog) {
      if (months < 84) return '\u{1F415} Adult';
      return '\u{1F415}\u{200D}\u{1F9BA} Senior';
    } else {
      if (months < 84) return '\u{1F408} Adult';
      return '\u{1F408}\u{200D}\u{2B1B} Senior';
    }
  }

  void _validatePetAge(int petIndex) {
    if (petIndex >= _petAge.length) return;
    final months = _parseAgeToMonths(_petAge[petIndex].text);
    final years = months / 12.0;
    final type = petIndex < _petType.length ? _petType[petIndex] : 'Dog';
    final breed = petIndex < _petBreed.length ? _petBreed[petIndex] : '';
    while (_petAgeWarnings.length <= petIndex) _petAgeWarnings.add(null);

    if (months < 2 && months > 0) {
      setState(() {
        _petAgeWarnings[petIndex] =
            'Minimum enrollment age is 8 weeks (2 months).';
      });
      return;
    }
    if (breed.isNotEmpty && breed != 'Other' && breed != 'Mixed Breed') {
      final maxAgeMap = type == 'Cat' ? catBreedMaxAge : dogBreedMaxAge;
      final expectedMax = maxAgeMap[breed];
      if (expectedMax != null && years > expectedMax + 2) {
        setState(() {
          _petAgeWarnings[petIndex] =
              'The average lifespan for ${breed}s is ~$expectedMax years. Please double-check.';
        });
        return;
      }
    }
    if (type == 'Dog' && years > 20) {
      setState(() {
        _petAgeWarnings[petIndex] =
            'Age exceeds typical dog lifespan. Please verify.';
      });
      return;
    }
    if (type == 'Cat' && years > 22) {
      setState(() {
        _petAgeWarnings[petIndex] =
            'Age exceeds typical cat lifespan. Please verify.';
      });
      return;
    }
    setState(() {
      _petAgeWarnings[petIndex] = null;
    });
  }

  void _ensurePetListsForIndex(int i) {
    while (_petName.length <= i) _petName.add(TextEditingController());
    while (_petAge.length <= i) _petAge.add(TextEditingController());
    while (_petBirthdate.length <= i)
      _petBirthdate.add(TextEditingController());
    while (_petType.length <= i) _petType.add('Dog');
    while (_petBreed.length <= i) _petBreed.add('');
    while (_petPreExistingAck.length <= i) _petPreExistingAck.add(false);
    while (_petPreExistingControllers.length <= i) {
      _petPreExistingControllers.add(TextEditingController());
    }
    while (_petCoverageExpanded.length <= i) _petCoverageExpanded.add(false);
    while (_petAgeWarnings.length <= i) _petAgeWarnings.add(null);
  }

  Future<void> _pickPetBirthdate(int petIndex) async {
    _ensurePetListsForIndex(petIndex);
    final now = DateTime.now();
    final earliest = DateTime(now.year - 22, now.month, now.day);
    final picked = await showDatePicker(
      context: context,
      initialDate: now.subtract(Duration(days: 365)),
      firstDate: earliest,
      lastDate: now,
      helpText: 'Select your pet\'s birthdate',
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: ColorScheme.light(
              primary: joviCoral,
              onPrimary: Colors.white,
              surface: Colors.white,
              onSurface: joviNavy,
            ),
          ),
          child: child!,
        );
      },
    );
    if (picked != null) {
      setState(() {
        _petBirthdate[petIndex].text =
            "${picked.month.toString().padLeft(2, '0')}/${picked.day.toString().padLeft(2, '0')}/${picked.year}";
      });
      _updatePetAgeFromBirthdate(petIndex);
    }
  }

  // Calculate age from birthdate string (MM-DD-YYYY format)
  int _calcAge(String birthdate) {
    if (birthdate.isEmpty) return 0;
    try {
      final parts = birthdate.split('-');
      final birth = DateTime(
        int.parse(parts[2]),
        int.parse(parts[0]),
        int.parse(parts[1]),
      );
      final now = DateTime.now();
      var age = now.year - birth.year;
      if (now.month < birth.month ||
          (now.month == birth.month && now.day < birth.day)) {
        age--;
      }
      return age;
    } catch (e) {
      debugPrint('Error calculating age: $e');
      return 0;
    }
  }

  // ============================================================
  // QUOTE COMPUTATION (with pets)
  // ============================================================

  void _computeQuote() {
    final list = <Map<String, dynamic>>[];
    double total = 0;

    final membersData = [
      {'label': 'Primary', 'date': _birthdate.text, 'primary': true},
      if (_spouse)
        {'label': 'Spouse', 'date': _spouseBirth.text, 'primary': false},
      for (var i = 0; i < _numDeps; i++)
        {
          'label': 'Dependent ${i + 1}',
          'date': i < _depBirth.length ? _depBirth[i].text : '',
          'primary': false
        },
    ];

    for (var i = 0; i < membersData.length; i++) {
      final member = membersData[i];
      final dateStr = member['date'] as String;
      if (dateStr.isEmpty) continue;

      final age = _calcAge(dateStr);

      double premium = age <= 29
          ? 150
          : age <= 39
              ? 200
              : age <= 49
                  ? 250
                  : age <= 59
                      ? 300
                      : 350;

      if (member['primary'] == true && _tobacco) premium *= 1.15;
      if (_dental) premium += 35;
      if (_vision) premium += 15;

      total += premium;

      final isa = age <= 26
          ? 1500
          : age <= 45
              ? 2000
              : age <= 60
                  ? 2500
                  : 3000;

      list.add({
        'name': member['label'],
        'age': age,
        'premium': premium,
        'isa': isa,
      });
    }

    // Compute pet quote
    final petList = <Map<String, dynamic>>[];
    double petTotal = 0;
    for (var i = 0; i < _numPets; i++) {
      if (i >= _petAge.length || _petAge[i].text.isEmpty) continue;
      final ageInMonths = _parseAgeToMonths(_petAge[i].text);
      if (ageInMonths < 2 || ageInMonths > 240) continue;
      final premium = _calculatePetPremium(ageInMonths);
      petTotal += premium;
      petList.add({
        'name': i < _petName.length && _petName[i].text.isNotEmpty
            ? _petName[i].text
            : 'Pet ${i + 1}',
        'type': i < _petType.length ? _petType[i] : 'Dog',
        'breed': i < _petBreed.length ? _petBreed[i] : '',
        'ageInMonths': ageInMonths,
        'premium': premium,
      });
    }

    setState(() {
      _quotes = list;
      _totalPremium = total;
      _petQuotes = petList;
      _petTotalPremium = petTotal;
      _showQuoteSummary = list.isNotEmpty || petList.isNotEmpty;
    });

    // Track analytics — once per distinct total, not on every keystroke.
    final grand = total + petTotal;
    if ((list.isNotEmpty || petList.isNotEmpty) &&
        grand != _lastLoggedGrandTotal) {
      _lastLoggedGrandTotal = grand;
      FirebaseAnalytics.instance.logEvent(
        name: 'premium_preview_calculated',
        parameters: {
          'total_premium': total,
          'pet_premium': petTotal,
          'grand_total': total + petTotal,
          'family_size': list.length,
          'has_spouse': _spouse,
          'num_dependents': _numDeps,
          'num_pets': _numPets,
        },
      );
    }
  }

  // Date picker for human birthdates
  Future<void> _pickDate(
      BuildContext context, TextEditingController controller) async {
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime(2000),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
      builder: (context, child) => Theme(
        data: Theme.of(context).copyWith(
          colorScheme: ColorScheme.light(
            primary: joviCoral,
            secondary: joviCoral,
            surface: Colors.white,
          ),
        ),
        child: child!,
      ),
    );

    if (date != null) {
      controller.text =
          '${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}-${date.year}';
      _computeQuote();
    }
  }

  // Manage dependent controllers
  void _manageDependentControllers() {
    while (_depBirth.length < _numDeps) {
      _depBirth.add(TextEditingController());
    }
    while (_depBirth.length > _numDeps) {
      _depBirth.removeLast().dispose();
    }
  }

  // Manage pet controllers
  void _managePetControllers() {
    for (int i = 0; i < _numPets; i++) {
      _ensurePetListsForIndex(i);
    }
  }

  // Navigate to create account
  void _navigateToCreateAccount() {
    HapticFeedback.lightImpact();

    FirebaseAnalytics.instance.logEvent(
      name: 'premium_preview_enroll_clicked',
      parameters: {
        'total_premium': _totalPremium,
        'pet_premium': _petTotalPremium,
        'grand_total': _totalPremium + _petTotalPremium,
        'family_size': _quotes.length,
        'num_pets': _numPets,
      },
    );

    // Grab the router before popping: after pop this context is gone.
    final router = GoRouter.of(context);
    Navigator.of(context).pop(); // Close bottom sheet
    router.pushNamed('createAccount');
  }

  // ============================================================
  // BUILD METHOD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideAnimation,
      child: FadeTransition(
        opacity: _fadeAnimation,
        child: Container(
          width: widget.width,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.only(
              topLeft: Radius.circular(24),
              topRight: Radius.circular(24),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 20,
                offset: Offset(0, -5),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Handle bar
              Container(
                width: 40,
                height: 4,
                margin: EdgeInsets.only(top: 12),
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),

              // Header
              Padding(
                padding: EdgeInsets.all(20),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Container(
                          padding: EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: joviCoral.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Icon(
                            Icons.calculate,
                            color: joviCoral,
                            size: 24,
                          ),
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Get Your Quote',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                  color: joviNavy,
                                ),
                              ),
                              Text(
                                'See what you\'ll pay before you enroll',
                                style: TextStyle(
                                  fontSize: 15,
                                  color: Colors.grey[600],
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          onPressed: () => Navigator.of(context).pop(),
                          tooltip: 'Close',
                          constraints: const BoxConstraints(
                              minWidth: 44, minHeight: 44),
                          icon: Icon(Icons.close, color: Colors.grey[600]),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // Form Content
              Flexible(
                child: SingleChildScrollView(
                  controller: widget.scrollController,
                  padding: EdgeInsets.symmetric(horizontal: 20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Primary Member Birthday
                      _buildSectionTitle('Your Information'),
                      SizedBox(height: 12),
                      _buildDateField(
                        controller: _birthdate,
                        label: 'Your Date of Birth',
                        isRequired: true,
                      ),

                      SizedBox(height: 20),

                      // Family Options
                      _buildSectionTitle('Family Members'),
                      SizedBox(height: 12),

                      // Spouse checkbox
                      CheckboxListTile(
                        title: Text('Include Spouse'),
                        value: _spouse,
                        onChanged: (value) {
                          setState(() {
                            _spouse = value ?? false;
                            if (_spouse && _spouseBirth.text.isNotEmpty) {
                              _computeQuote();
                            }
                          });
                        },
                        activeColor: joviCoral,
                        contentPadding: EdgeInsets.zero,
                      ),

                      if (_spouse) ...[
                        SizedBox(height: 8),
                        _buildDateField(
                          controller: _spouseBirth,
                          label: 'Spouse Date of Birth',
                        ),
                      ],

                      SizedBox(height: 16),

                      // Dependents
                      DropdownButtonFormField<int>(
                        value: _numDeps,
                        decoration: InputDecoration(
                          labelText: 'Number of Dependents',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          contentPadding: EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 16,
                          ),
                        ),
                        items: List.generate(
                          6,
                          (i) => DropdownMenuItem(
                            value: i,
                            child: Text(
                                '$i ${i == 1 ? 'Dependent' : 'Dependents'}'),
                          ),
                        ),
                        onChanged: (value) {
                          setState(() {
                            _numDeps = value ?? 0;
                            _manageDependentControllers();
                            _computeQuote();
                          });
                        },
                      ),

                      // Dependent birthdays
                      for (int i = 0; i < _numDeps; i++) ...[
                        SizedBox(height: 12),
                        _buildDateField(
                          controller: _depBirth[i],
                          label: 'Dependent ${i + 1} Date of Birth',
                        ),
                      ],

                      SizedBox(height: 20),

                      // ===== PET SECTION =====
                      _buildPetSection(),

                      SizedBox(height: 20),

                      // Coverage Options
                      _buildSectionTitle('Coverage Options'),
                      SizedBox(height: 8),

                      CheckboxListTile(
                        title: Text('Tobacco/Marijuana Use'),
                        subtitle:
                            Text('Additional 15% premium on primary member'),
                        value: _tobacco,
                        onChanged: (value) {
                          setState(() {
                            _tobacco = value ?? false;
                            _computeQuote();
                          });
                        },
                        activeColor: joviCoral,
                        contentPadding: EdgeInsets.zero,
                      ),

                      CheckboxListTile(
                        title: Text('Dental Plan'),
                        subtitle: Text('+\$35/month per person'),
                        value: _dental,
                        onChanged: (value) {
                          setState(() {
                            _dental = value ?? false;
                            _computeQuote();
                          });
                        },
                        activeColor: joviCoral,
                        contentPadding: EdgeInsets.zero,
                      ),

                      CheckboxListTile(
                        title: Text('Vision Plan'),
                        subtitle: Text('+\$15/month per person'),
                        value: _vision,
                        onChanged: (value) {
                          setState(() {
                            _vision = value ?? false;
                            _computeQuote();
                          });
                        },
                        activeColor: joviCoral,
                        contentPadding: EdgeInsets.zero,
                      ),

                      // Quote Summary
                      if (_showQuoteSummary) ...[
                        SizedBox(height: 20),
                        _buildQuoteSummary(),
                        SizedBox(height: 20),
                        _buildEnrollButton(),
                      ],

                      SizedBox(height: 20),
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

  // ============================================================
  // UI WIDGETS
  // ============================================================

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: joviNavy,
      ),
    );
  }

  Widget _buildDateField({
    required TextEditingController controller,
    required String label,
    bool isRequired = false,
  }) {
    return TextFormField(
      controller: controller,
      readOnly: true,
      decoration: InputDecoration(
        labelText: label + (isRequired ? ' *' : ''),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        suffixIcon: Icon(Icons.calendar_today, color: joviCoral),
        contentPadding: EdgeInsets.symmetric(
          horizontal: 12,
          vertical: 16,
        ),
      ),
      onTap: () => _pickDate(context, controller),
    );
  }

  // ============================================================
  // PET UI
  // ============================================================

  Widget _buildPetSection() {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: joviWarmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: joviCoral.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.pets, color: joviCoral, size: 20),
              SizedBox(width: 8),
              Text(
                'Pet Plan',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: joviNavy,
                ),
              ),
            ],
          ),
          SizedBox(height: 8),
          Container(
            padding: EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: joviMint.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: joviMint.withOpacity(0.3)),
            ),
            child: Row(
              children: [
                Icon(Icons.check_circle, color: joviMint, size: 16),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Accident + Illness • 90% Reimbursement • \$500 Out-of-Pocket',
                    style: TextStyle(
                      color: joviMintDark,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: 12),
          DropdownButtonFormField<int>(
            value: _numPets,
            decoration: InputDecoration(
              labelText: 'Number of Pets',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              filled: true,
              fillColor: Colors.white,
              contentPadding: EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 16,
              ),
            ),
            items: List.generate(
              5,
              (i) => DropdownMenuItem(
                value: i,
                child: Text('$i ${i == 1 ? 'Pet' : 'Pets'}'),
              ),
            ),
            onChanged: (value) {
              setState(() {
                _numPets = value ?? 0;
                _managePetControllers();
                _computeQuote();
              });
            },
          ),
          for (int i = 0; i < _numPets; i++) ...[
            SizedBox(height: 16),
            _buildPetCard(i),
          ],
        ],
      ),
    );
  }

  Widget _buildPetCard(int i) {
    _ensurePetListsForIndex(i);
    return Container(
      padding: EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: joviCoral.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.pets, color: joviCoral, size: 18),
              SizedBox(width: 8),
              Text(
                'Pet ${i + 1}',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: joviNavy,
                  fontSize: 15,
                ),
              ),
            ],
          ),
          SizedBox(height: 12),
          // Pet Name
          TextFormField(
            controller: _petName[i],
            decoration: InputDecoration(
              labelText: 'Pet Name',
              prefixIcon: Icon(Icons.badge, color: joviCoral, size: 20),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
              ),
              filled: true,
              fillColor: joviSoftStone.withOpacity(0.3),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            ),
            onChanged: (v) => _computeQuote(),
          ),
          SizedBox(height: 10),
          // Type dropdown
          DropdownButtonFormField<String>(
            value: _petType[i],
            decoration: InputDecoration(
              labelText: 'Type',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
              ),
              filled: true,
              fillColor: joviSoftStone.withOpacity(0.3),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            ),
            items: ['Dog', 'Cat']
                .map((type) => DropdownMenuItem(value: type, child: Text(type)))
                .toList(),
            onChanged: (v) {
              setState(() {
                _petType[i] = v!;
                _petBreed[i] = ''; // Reset breed when type changes
              });
              _validatePetAge(i);
              _computeQuote();
            },
          ),
          SizedBox(height: 10),
          // Breed picker
          _buildBreedPicker(i),
          SizedBox(height: 10),
          // Birthdate picker with manual age fallback
          Container(
            padding: EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: joviCoral.withOpacity(0.04),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: joviCoral.withOpacity(0.15)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Pet Birthdate',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: joviNavy,
                  ),
                ),
                SizedBox(height: 6),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _petBirthdate[i],
                        readOnly: true,
                        decoration: InputDecoration(
                          hintText: 'MM/DD/YYYY',
                          prefixIcon: Icon(Icons.calendar_today,
                              color: joviCoral, size: 18),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          filled: true,
                          fillColor: Colors.white,
                          contentPadding: EdgeInsets.symmetric(
                              vertical: 10, horizontal: 10),
                        ),
                        onTap: () => _pickPetBirthdate(i),
                      ),
                    ),
                    SizedBox(width: 6),
                    ElevatedButton(
                      onPressed: () => _pickPetBirthdate(i),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: joviCoral,
                        foregroundColor: Colors.white,
                        padding:
                            EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: Icon(Icons.cake, size: 16),
                    ),
                  ],
                ),
                if (_petAge[i].text.isNotEmpty) ...[
                  SizedBox(height: 6),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: joviMint.withOpacity(0.3)),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.auto_awesome, size: 14, color: joviMintDark),
                        SizedBox(width: 4),
                        Expanded(
                          child: Text.rich(
                            TextSpan(
                              style: TextStyle(
                                fontSize: 12,
                                color: joviNavy,
                              ),
                              children: [
                                TextSpan(
                                  text: 'Age: ',
                                  style: TextStyle(fontWeight: FontWeight.w600),
                                ),
                                TextSpan(text: '${_petAge[i].text}'),
                                if (_getPetAgeLabel(i).isNotEmpty) ...[
                                  TextSpan(text: '  '),
                                  TextSpan(
                                    text: _getPetAgeLabel(i),
                                    style: TextStyle(
                                        fontWeight: FontWeight.w600,
                                        color: joviCoral),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          SizedBox(height: 10),
          // Manual age input (fallback)
          TextFormField(
            controller: _petAge[i],
            decoration: InputDecoration(
              labelText: 'Or enter age manually (e.g., "3 years")',
              prefixIcon: Icon(Icons.cake, color: joviCoral, size: 20),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
              ),
              filled: true,
              fillColor: joviSoftStone.withOpacity(0.3),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            ),
            onChanged: (v) {
              _validatePetAge(i);
              _computeQuote();
            },
          ),
          SizedBox(height: 4),
          Text(
            'Min: 8 weeks (2 months) • Max: 20 years',
            style: TextStyle(
              fontSize: 10,
              color: Colors.grey[600],
              fontStyle: FontStyle.italic,
            ),
          ),
          // Age warning
          if (i < _petAgeWarnings.length && _petAgeWarnings[i] != null) ...[
            SizedBox(height: 6),
            Container(
              padding: EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.orange[50],
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: Colors.orange[200]!),
              ),
              child: Row(
                children: [
                  Icon(Icons.warning_amber,
                      size: 14, color: Colors.orange[700]),
                  SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      _petAgeWarnings[i]!,
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.orange[800],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          // Premium display
          if (_petAge[i].text.isNotEmpty) ...[
            SizedBox(height: 10),
            Container(
              padding: EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: joviCoral.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(Icons.monetization_on, color: joviCoral, size: 18),
                  SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Monthly Contribution: \$${_calculatePetPremium(_parseAgeToMonths(_petAge[i].text)).toStringAsFixed(2)}',
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        color: joviNavy,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          SizedBox(height: 10),
          // Coverage accordion
          _buildPetCoverageAccordion(i),
          SizedBox(height: 10),
          // Pre-existing conditions section
          _buildPreExistingSection(i),
        ],
      ),
    );
  }

  Widget _buildBreedPicker(int i) {
    final breeds = _petType[i] == 'Cat' ? catBreeds : dogBreeds;
    // InputDecorator instead of a TextFormField whose controller was
    // re-created (and never disposed) on every rebuild.
    return _Pressable(
      pressedScale: 0.99,
      onTap: () async {
        final selected = await showDialog<String>(
          context: context,
          builder: (BuildContext context) {
            String searchQuery = '';
            return StatefulBuilder(builder: (context, setState) {
              final filteredBreeds = breeds
                  .where((breed) =>
                      breed.toLowerCase().contains(searchQuery.toLowerCase()))
                  .toList();
              return AlertDialog(
                title: Text('Select Breed'),
                content: Container(
                  width: double.maxFinite,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextField(
                        autofocus: true,
                        autocorrect: false,
                        decoration: InputDecoration(
                          labelText: 'Search breeds',
                          prefixIcon: Icon(Icons.search),
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12)),
                        ),
                        onChanged: (value) {
                          setState(() {
                            searchQuery = value;
                          });
                        },
                      ),
                      SizedBox(height: 16),
                      Expanded(
                        child: ListView.builder(
                          shrinkWrap: true,
                          itemCount: filteredBreeds.length,
                          itemBuilder: (context, index) {
                            return ListTile(
                              title: Text(filteredBreeds[index]),
                              onTap: () => Navigator.of(context)
                                  .pop(filteredBreeds[index]),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text('Cancel'),
                  ),
                ],
              );
            });
          },
        );
        if (selected != null) {
          setState(() {
            _petBreed[i] = selected;
          });
          _validatePetAge(i);
          _computeQuote();
        }
      },
      child: InputDecorator(
        isEmpty: _petBreed[i].isEmpty,
        decoration: InputDecoration(
          labelText: 'Breed',
          hintText: 'Tap to search',
          prefixIcon: Icon(Icons.pets, color: joviCoral, size: 20),
          suffixIcon: Icon(Icons.search, color: joviCoral, size: 20),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
          filled: true,
          fillColor: joviSoftStone.withOpacity(0.3),
          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        ),
        child: Text(
          _petBreed[i],
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(color: joviNavy, fontSize: 16),
        ),
      ),
    );
  }

  Widget _buildPetCoverageAccordion(int i) {
    final isExpanded = _petCoverageExpanded[i];
    final type = i < _petType.length ? _petType[i] : 'Dog';
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey[200]!),
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () => setState(() {
              _petCoverageExpanded[i] = !_petCoverageExpanded[i];
            }),
            borderRadius: BorderRadius.circular(8),
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                children: [
                  Icon(Icons.shield_outlined, size: 18, color: joviCoral),
                  SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      "What's Shared for ${i < _petName.length && _petName[i].text.isNotEmpty ? _petName[i].text : 'this pet'}",
                      style: TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                        color: joviNavy,
                      ),
                    ),
                  ),
                  AnimatedRotation(
                    turns: isExpanded ? 0.5 : 0,
                    duration: _Motion.select,
                    child: Icon(Icons.keyboard_arrow_down, color: joviCoral),
                  ),
                ],
              ),
            ),
          ),
          AnimatedCrossFade(
            firstChild: SizedBox.shrink(),
            secondChild: Padding(
              padding: EdgeInsets.only(left: 12, right: 12, bottom: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Divider(height: 1, color: Colors.grey[200]),
                  SizedBox(height: 10),
                  _buildAccordionCategory(
                      '🩺 Accidents',
                      [
                        'Broken bones & fractures',
                        'Toxic ingestion',
                        'Cuts & bite wounds',
                        'Emergency vet visits',
                      ],
                      Colors.green),
                  SizedBox(height: 8),
                  _buildAccordionCategory(
                      '💊 Illnesses',
                      [
                        'Cancer treatment',
                        'Diabetes management',
                        'Allergies & skin conditions',
                        type == 'Dog'
                            ? 'Hip dysplasia'
                            : 'Urinary tract conditions',
                      ],
                      Colors.blue),
                  SizedBox(height: 8),
                  _buildAccordionCategory(
                      '🏥 Vet Services',
                      [
                        'Exam fees',
                        'Diagnostics (X-rays, MRI)',
                        'Surgery & hospitalization',
                        'Prescription medications',
                      ],
                      Colors.purple),
                  SizedBox(height: 10),
                  Container(
                    padding: EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.red[50],
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: Colors.red[200]!),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Not Shared:',
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 11,
                            color: Colors.red[800],
                          ),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Pre-existing conditions • Cosmetic procedures • Breeding costs • Preventive care',
                          style: TextStyle(
                            fontSize: 10,
                            color: Colors.red[700],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            crossFadeState: isExpanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
            duration: _Motion.select,
          ),
        ],
      ),
    );
  }

  Widget _buildAccordionCategory(
      String title, List<String> items, MaterialColor color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            fontWeight: FontWeight.w600,
            fontSize: 12,
            color: color[800],
          ),
        ),
        SizedBox(height: 3),
        ...items.map((item) => Padding(
              padding: EdgeInsets.only(left: 4, bottom: 1),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.check, size: 12, color: color[600]),
                  SizedBox(width: 3),
                  Flexible(
                    child: Text(
                      item,
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey[700],
                      ),
                    ),
                  ),
                ],
              ),
            )),
      ],
    );
  }

  Widget _buildPreExistingSection(int i) {
    final isAcked = _petPreExistingAck[i];
    return Container(
      padding: EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.amber[50],
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.amber[200]!),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.medical_information,
                  size: 16, color: Colors.amber[800]),
              SizedBox(width: 6),
              Expanded(
                child: Text(
                  'Pre-Existing Conditions',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                    color: Colors.amber[900],
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: 6),
          Text(
            'Does ${i < _petName.length && _petName[i].text.isNotEmpty ? _petName[i].text : 'this pet'} have any pre-existing conditions?',
            style: TextStyle(fontSize: 11, color: Colors.grey[700]),
          ),
          SizedBox(height: 6),
          Row(
            children: [
              SizedBox(
                width: 20,
                height: 20,
                child: Checkbox(
                  value: isAcked,
                  activeColor: joviCoral,
                  onChanged: (v) {
                    setState(() {
                      _petPreExistingAck[i] = v ?? false;
                    });
                  },
                ),
              ),
              SizedBox(width: 6),
              Expanded(
                child: Text(
                  'Yes, pre-existing conditions',
                  style: TextStyle(fontSize: 11, color: Colors.grey[800]),
                ),
              ),
            ],
          ),
          if (isAcked) ...[
            SizedBox(height: 8),
            TextFormField(
              controller: _petPreExistingControllers[i],
              maxLines: 2,
              decoration: InputDecoration(
                hintText: 'Describe any conditions or diagnoses...',
                hintStyle: TextStyle(fontSize: 11),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(6),
                ),
                filled: true,
                fillColor: Colors.white,
                contentPadding: EdgeInsets.all(8),
              ),
            ),
            SizedBox(height: 6),
            Container(
              padding: EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: joviCoral.withOpacity(0.05),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, size: 12, color: joviCoral),
                  SizedBox(width: 4),
                  Flexible(
                    child: Text(
                      'Pre-existing conditions are generally not eligible. Curable conditions may qualify after 180 days symptom-free.',
                      style: TextStyle(
                        fontSize: 10,
                        color: joviNavy,
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

  Widget _buildQuoteSummary() {
    final grandTotal = _totalPremium + _petTotalPremium;
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [joviCoral, joviCoralLight],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: joviCoral.withOpacity(0.3),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.star, color: Colors.white, size: 24),
              SizedBox(width: 8),
              Text(
                'Your Plan Summary',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ],
          ),
          SizedBox(height: 16),

          // Grand Total Display
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.15),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Total Monthly Plan',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      '\$${grandTotal.toStringAsFixed(2)}',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Plan Type',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      (_spouse || _numDeps > 0)
                          ? 'Family Plan'
                          : 'Individual Plan',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Covered',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      '${_quotes.length} ${_quotes.length == 1 ? 'Person' : 'People'}${_numPets > 0 ? ' + $_numPets ${_numPets == 1 ? 'Pet' : 'Pets'}' : ''}',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          SizedBox(height: 16),

          // Health breakdown
          if (_quotes.isNotEmpty) ...[
            Row(
              children: [
                Icon(Icons.people, color: Colors.white70, size: 16),
                SizedBox(width: 6),
                Text(
                  'Health Plan',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            SizedBox(height: 6),
            ...(_quotes
                .map((quote) => Padding(
                      padding: EdgeInsets.only(bottom: 3, left: 20),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              '${quote['name']} (Age ${quote['age']})',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          Text(
                            '\$${quote['premium'].toStringAsFixed(2)}/mo',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ))
                .toList()),
            SizedBox(height: 4),
            Padding(
              padding: EdgeInsets.only(left: 20),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Health subtotal',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    '\$${_totalPremium.toStringAsFixed(2)}/mo',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ],

          // Pet breakdown
          if (_petQuotes.isNotEmpty) ...[
            SizedBox(height: 12),
            Row(
              children: [
                Icon(Icons.pets, color: Colors.white70, size: 16),
                SizedBox(width: 6),
                Text(
                  'Pet Plan',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            SizedBox(height: 6),
            ...(_petQuotes
                .map((pq) => Padding(
                      padding: EdgeInsets.only(bottom: 3, left: 20),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              '${pq['name']} (${pq['type']}${(pq['breed'] as String).isNotEmpty ? ' - ${pq['breed']}' : ''})',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 13,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          Text(
                            '\$${(pq['premium'] as double).toStringAsFixed(2)}/mo',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ))
                .toList()),
            SizedBox(height: 4),
            Padding(
              padding: EdgeInsets.only(left: 20),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Pet subtotal',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    '\$${_petTotalPremium.toStringAsFixed(2)}/mo',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ],

          SizedBox(height: 12),

          // Responsibility amounts
          Container(
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(
              children: [
                if (_quotes.isNotEmpty)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Your Responsibility (Health)',
                        style: TextStyle(color: Colors.white70, fontSize: 13),
                      ),
                      Text(
                        '\$${_quotes.first['isa']}',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                if (_petQuotes.isNotEmpty) ...[
                  SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Out-of-Pocket (Pet${_numPets > 1 ? ', each' : ''})',
                        style: TextStyle(color: Colors.white70, fontSize: 13),
                      ),
                      Text(
                        '\$500',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),

          SizedBox(height: 12),

          // Benefits highlight
          Container(
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'What\'s Included:',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  '• Choose any provider\n• Quick reimbursements\n• No pre-authorizations\n• Telehealth included${_petQuotes.isNotEmpty ? '\n• 90% pet reimbursement at any vet' : ''}',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEnrollButton() {
    return _Pressable(
      feedbackOnly: true,
      child: SizedBox(
      width: double.infinity,
      child: ElevatedButton(
        onPressed: _navigateToCreateAccount,
        style: ElevatedButton.styleFrom(
          backgroundColor: joviNavy,
          foregroundColor: Colors.white,
          padding: EdgeInsets.symmetric(vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          elevation: 4,
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.rocket_launch, size: 20),
            SizedBox(width: 8),
            Text(
              'Enroll Today',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.2,
              ),
            ),
          ],
        ),
      ),
    ));
  }
}

class PremiumLandingPageWidget extends StatefulWidget {
  const PremiumLandingPageWidget({
    super.key,
    this.width,
    this.height,
    this.deepLink, // Support for deep linking
  });

  final double? width;
  final double? height;
  final String? deepLink; // Deep link parameter

  @override
  State<PremiumLandingPageWidget> createState() =>
      _PremiumLandingPageWidgetState();
}

class _PremiumLandingPageWidgetState extends State<PremiumLandingPageWidget>
    with TickerProviderStateMixin {
  // Version constant
  static const String appVersion = 'v1.0';

  // Responsive Layout Variables
  ScreenType currentScreenType = ScreenType.compact;
  ResponsiveConfig layoutSettings = ResponsiveConfig(
    paddingH: 24,
    paddingV: 20,
    contentMax: 380.0,
    headingSize: 30,
    bodySize: 16,
    logoScale: 1.0,
    buttonHeight: 60,
    iconSize: 28,
    wideMode: false,
    hasHinge: false,
  );

  // Track previous screen configuration to prevent unnecessary rebuilds
  double? _lastScreenWidth;
  bool? _lastHasHinge;

  bool get _reduceMotion =>
      MediaQuery.maybeOf(context)?.disableAnimations ?? false;

  void _toast(String message, {Color accent = joviCoral, IconData? icon}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)
        ?.showSnackBar(_joviToast(message, accent: accent, icon: icon));
  }

  // Loading states for buttons
  bool _isCreateAccountLoading = false;
  bool _isSignInLoading = false;
  bool _isFinalCTALoading = false;

  // Animation counter for clinic feature
  late AnimationController _clinicFeatureController;

  late AnimationController _heroController;
  late AnimationController _benefitsController;
  late AnimationController _howItWorksController;
  late AnimationController _testimonialsController;
  late AnimationController _faqController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  // Shimmer animation for loading
  late AnimationController _shimmerController;
  late Animation<double> _shimmerAnimation;

  // Page controller for testimonials
  final PageController _testimonialController = PageController();
  int _currentTestimonial = 0;
  Timer? _testimonialTimer;

  // Benefit card animations
  late List<AnimationController> _cardControllers;
  late List<Animation<double>> _cardFadeAnimations;
  late List<Animation<Offset>> _cardSlideAnimations;

  // Track expanded FAQ items
  Set<int> _expandedFaqs = {};

  // Heartbeat animation
  late AnimationController _heartbeatController;
  late Animation<double> _heartbeatAnimation;

  @override
  void initState() {
    super.initState();

    // Handle deep linking
    _handleDeepLink();

    // Hero animation setup
    _heroController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _heroController,
      curve: Curves.easeOut,
    ));

    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.04),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _heroController,
      curve: _Motion.settle,
    ));

    // Shimmer animation setup — started only while the logo is loading
    // (see the loadingBuilder), not left running for the page's lifetime.
    _shimmerController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );

    _shimmerAnimation = Tween<double>(
      begin: -1.0,
      end: 2.0,
    ).animate(CurvedAnimation(
      parent: _shimmerController,
      curve: Curves.easeInOut,
    ));

    // Heart: a single settle on entrance instead of a perpetual beat —
    // an endlessly pulsing element is the kind of motion Apple's guidance
    // (and vestibular-sensitive users) ask apps to avoid.
    _heartbeatController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );

    _heartbeatAnimation = Tween<double>(
      begin: 0.9,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _heartbeatController,
      curve: _Motion.settle,
    ));

    // Clinic feature animation
    _clinicFeatureController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );

    // Other section animations
    _benefitsController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );

    _howItWorksController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );

    _testimonialsController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );

    _faqController = AnimationController(
      duration: _Motion.enter,
      vsync: this,
    );

    // Initialize card animations (5 benefit cards now)
    _cardControllers = List.generate(
      5,
      (index) => AnimationController(
        duration: _Motion.enter,
        vsync: this,
      ),
    );

    _cardFadeAnimations = _cardControllers.map((controller) {
      return Tween<double>(
        begin: 0.0,
        end: 1.0,
      ).animate(CurvedAnimation(
        parent: controller,
        curve: Curves.easeOut,
      ));
    }).toList();

    _cardSlideAnimations = _cardControllers.map((controller) {
      return Tween<Offset>(
        begin: const Offset(0, 0.06),
        end: Offset.zero,
      ).animate(CurvedAnimation(
        parent: controller,
        curve: _Motion.settle,
      ));
    }).toList();

    // Listen to page changes for testimonials
    _testimonialController.addListener(() {
      final page = _testimonialController.page;
      if (page == null) return;
      final rounded = page.round();
      // Only rebuild when the page index actually changes, not every frame.
      if (rounded != _currentTestimonial && mounted) {
        setState(() => _currentTestimonial = rounded);
      }
    });

    // Start auto-rotate for testimonials
    _startTestimonialAutoRotate();

    // Start animations in sequence
    _startAnimations();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    analyzeScreenConfiguration();
  }

  // Responsive Layout Methods — IDENTICAL logic, no changes needed
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

    // Runs from didChangeDependencies (before build); no setState needed.
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
          headingSize: 40,
          bodySize: 18,
          logoScale: 1.4,
          buttonHeight: 72,
          iconSize: 36,
          wideMode: true,
          hasHinge: true,
          useTwoColumnLayout: width >= 900,
          useGridLayout: true,
        );
      case ScreenType.large:
        return ResponsiveConfig(
          paddingH: 40,
          paddingV: 28,
          contentMax: double.infinity,
          headingSize: 36,
          bodySize: 18,
          logoScale: 1.3,
          buttonHeight: 68,
          iconSize: 32,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 1100,
          useGridLayout: true,
        );
      case ScreenType.medium:
        return ResponsiveConfig(
          paddingH: 32,
          paddingV: 24,
          contentMax: double.infinity,
          headingSize: 32,
          bodySize: 17,
          logoScale: 1.2,
          buttonHeight: 64,
          iconSize: 30,
          wideMode: true,
          hasHinge: false,
          useTwoColumnLayout: width >= 900,
          useGridLayout: width >= 768,
        );
      case ScreenType.compact:
      default:
        return ResponsiveConfig(
          paddingH: width < 375 ? 16 : 24,
          paddingV: 20,
          contentMax: 380.0,
          headingSize: width < 375
              ? 26
              : width >= 414
                  ? 34
                  : 30,
          bodySize: width < 375
              ? 14
              : width >= 414
                  ? 17
                  : 16,
          logoScale: width < 375
              ? 0.75
              : width >= 414
                  ? 1.15
                  : 1.0,
          buttonHeight: 60,
          iconSize: width < 375 ? 24 : 28,
          wideMode: false,
          hasHinge: false,
          useTwoColumnLayout: false,
          useGridLayout: false,
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
    if (layoutSettings.contentMax < double.infinity) {
      return Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: layoutSettings.contentMax),
          child: child,
        ),
      );
    }
    return child;
  }

  void _handleDeepLink() {
    if (widget.deepLink != null) {
      if (widget.deepLink!.contains('signup')) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _navigateWithErrorHandling('createAccount');
        });
      } else if (widget.deepLink!.contains('login')) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          _navigateWithErrorHandling('logIn');
        });
      }
    }
  }

  void _startTestimonialAutoRotate() {
    _testimonialTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (!mounted || !_testimonialController.hasClients) return;
      final nextPage = (_currentTestimonial + 1) % 3;
      if (_reduceMotion) {
        _testimonialController.jumpToPage(nextPage);
      } else {
        _testimonialController.animateToPage(
          nextPage,
          duration: const Duration(milliseconds: 450),
          curve: _Motion.settle,
        );
      }
    });
  }

  Future<void> _navigateWithErrorHandling(String routeName,
      {String location = ''}) async {
    try {
      await FirebaseAnalytics.instance.logEvent(
        name: routeName == 'Tour' ? 'tour_clicked' : 'landing_cta_clicked',
        parameters: {
          'button': routeName == 'createAccount'
              ? 'create_account'
              : routeName == 'logIn'
                  ? 'sign_in'
                  : 'tour',
          'location': location,
          'timestamp': DateTime.now().toIso8601String(),
        },
      );

      HapticFeedback.lightImpact();
      if (mounted) {
        context.pushNamed(routeName);
      }
    } catch (e) {
      _toast('Unable to proceed. Please try again.',
          accent: const Color(0xFFEF4444),
          icon: CupertinoIcons.exclamationmark_circle);
    }
  }

  // Show premium preview bottom sheet
  void _showPremiumPreview() {
    HapticFeedback.lightImpact();
    FirebaseAnalytics.instance.logEvent(name: 'premium_preview_button_clicked');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.8,
        minChildSize: 0.5,
        maxChildSize: 0.95,
        builder: (context, scrollController) => PremiumPreviewBottomSheetWidget(
          width: MediaQuery.of(context).size.width,
          height: MediaQuery.of(context).size.height,
          scrollController: scrollController,
        ),
      ),
    );
  }

  void _startAnimations() async {
    if (_platformReduceMotion()) {
      // Reduce Motion: everything lands in place, no staggered reveal.
      for (final c in [
        _heroController,
        _benefitsController,
        _clinicFeatureController,
        _howItWorksController,
        _testimonialsController,
        _faqController,
        _heartbeatController,
        ..._cardControllers,
      ]) {
        c.value = 1.0;
      }
      return;
    }
    _heroController.forward();
    _heartbeatController.forward();

    await Future.delayed(const Duration(milliseconds: 400));
    if (mounted) {
      _benefitsController.forward();
      _clinicFeatureController.forward();
      for (int i = 0; i < _cardControllers.length; i++) {
        Future.delayed(Duration(milliseconds: 50 * i), () {
          if (mounted) _cardControllers[i].forward();
        });
      }
    }

    await Future.delayed(const Duration(milliseconds: 200));
    if (mounted) _howItWorksController.forward();

    await Future.delayed(const Duration(milliseconds: 200));
    if (mounted) _testimonialsController.forward();

    await Future.delayed(const Duration(milliseconds: 200));
    if (mounted) _faqController.forward();
  }

  Future<void> _handleRefresh() async {
    _heroController.reset();
    _benefitsController.reset();
    _howItWorksController.reset();
    _testimonialsController.reset();
    _faqController.reset();
    _heartbeatController.reset();
    for (var controller in _cardControllers) {
      controller.reset();
    }

    setState(() {
      _expandedFaqs.clear();
      _currentTestimonial = 0;
    });

    if (_testimonialController.hasClients) {
      _testimonialController.jumpToPage(0);
    }

    await Future.delayed(const Duration(milliseconds: 300));
    _startAnimations();
  }

  @override
  void dispose() {
    _heroController.dispose();
    _benefitsController.dispose();
    _howItWorksController.dispose();
    _testimonialsController.dispose();
    _faqController.dispose();
    _shimmerController.dispose();
    _heartbeatController.dispose();
    _clinicFeatureController.dispose();
    _testimonialController.dispose();
    _testimonialTimer?.cancel();
    for (var controller in _cardControllers) {
      controller.dispose();
    }
    super.dispose();
  }

  // Shimmer loading widget
  Widget _buildShimmerLoader(double width, double height) {
    return AnimatedBuilder(
      animation: _shimmerAnimation,
      builder: (context, child) {
        return Container(
          width: width,
          height: height,
          decoration: BoxDecoration(
            color: joviSoftStone,
            borderRadius: BorderRadius.circular(16),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Stack(
              children: [
                Positioned(
                  left: _shimmerAnimation.value * width,
                  top: 0,
                  bottom: 0,
                  child: Container(
                    width: width * 0.3,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.centerLeft,
                        end: Alignment.centerRight,
                        colors: [
                          joviSoftStone,
                          joviWarmWhite,
                          joviSoftStone,
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final screenHeight = MediaQuery.of(context).size.height;

    // Calculate responsive logo dimensions
    final logoWidth = layoutSettings.wideMode
        ? (400 * layoutSettings.logoScale)
        : currentScreenType == ScreenType.compact
            ? (280 * layoutSettings.logoScale)
            : (320 * layoutSettings.logoScale);
    final logoHeight = layoutSettings.wideMode
        ? (200 * layoutSettings.logoScale)
        : currentScreenType == ScreenType.compact
            ? (140 * layoutSettings.logoScale)
            : (160 * layoutSettings.logoScale);

    return Container(
      width: widget.width ?? screenWidth,
      height: widget.height ?? screenHeight,
      color: joviNavy,
      child: SafeArea(
        top: false,
        bottom: false,
        child: RefreshIndicator(
          onRefresh: _handleRefresh,
          color: joviCoral,
          child: CustomScrollView(
            physics: const BouncingScrollPhysics(
              parent: AlwaysScrollableScrollPhysics(),
            ),
            slivers: [
              // Hero Section
              SliverToBoxAdapter(
                child: FadeTransition(
                  opacity: _fadeAnimation,
                  child: SlideTransition(
                    position: _slideAnimation,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [joviNavy, joviNavyDark],
                        ),
                      ),
                      padding: EdgeInsets.only(
                        left: layoutSettings.paddingH,
                        right: layoutSettings.paddingH,
                        top: MediaQuery.of(context).padding.top + 8,
                        bottom: 0,
                      ),
                      child: wrapWithConstraints(
                        child: Stack(
                          children: [
                            // Decorative coral gradient orb behind logo
                            Positioned(
                              top: 20,
                              left: 0,
                              right: 0,
                              child: Center(
                                child: Container(
                                  width: 220 * layoutSettings.logoScale,
                                  height: 220 * layoutSettings.logoScale,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    gradient: RadialGradient(
                                      colors: [
                                        joviCoral.withOpacity(0.12),
                                        joviCoral.withOpacity(0.04),
                                        Colors.transparent,
                                      ],
                                      stops: const [0.0, 0.5, 1.0],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            // Secondary subtle mint orb
                            Positioned(
                              bottom: 200,
                              left: -40,
                              child: Container(
                                width: 150,
                                height: 150,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  gradient: RadialGradient(
                                    colors: [
                                      joviMint.withOpacity(0.06),
                                      Colors.transparent,
                                    ],
                                  ),
                                ),
                              ),
                            ),
                            // Main content
                            Column(
                              children: [
                                // Logo — Jovi wordmark image with coral glow
                                TweenAnimationBuilder<double>(
                                  tween: Tween(
                                      begin: _reduceMotion ? 1.0 : 0.94,
                                      end: 1.0),
                                  duration: _Motion.enter,
                                  curve: _Motion.settle,
                                  builder: (context, value, child) {
                                    return Transform.scale(
                                      scale: value,
                                      child: SizedBox(
                                        width: logoWidth * 0.8,
                                        height: logoHeight * 0.75,
                                        child: Image.network(
                                          'https://storage.googleapis.com/flutterflow-io-6f20.appspot.com/projects/kurv-health-3vcfmp/assets/gveqn2eoe4nf/jovi_header_logo_master.png',
                                          fit: BoxFit.contain,
                                          loadingBuilder: (context, child,
                                              loadingProgress) {
                                            if (loadingProgress == null) {
                                              if (_shimmerController
                                                  .isAnimating) {
                                                _shimmerController.stop();
                                              }
                                              return child;
                                            }
                                            if (!_shimmerController
                                                    .isAnimating &&
                                                !_reduceMotion) {
                                              _shimmerController.repeat();
                                            }
                                            return _buildShimmerLoader(
                                                logoWidth * 0.8,
                                                logoHeight * 0.75);
                                          },
                                          errorBuilder:
                                              (context, error, stackTrace) {
                                            return Center(
                                              child: Text(
                                                'jovi',
                                                style: TextStyle(
                                                  fontSize: layoutSettings
                                                          .headingSize *
                                                      2.2,
                                                  fontWeight: FontWeight.w800,
                                                  color: Colors.white,
                                                  letterSpacing: -3,
                                                ),
                                              ),
                                            );
                                          },
                                        ),
                                      ),
                                    );
                                  },
                                ),

                                const SizedBox(height: 20),

                                // Two-tone headline: white + coral
                                Text.rich(
                                  TextSpan(
                                    style: TextStyle(
                                      fontSize: layoutSettings.headingSize,
                                      fontWeight: FontWeight.w800,
                                      height: 1.1,
                                      letterSpacing: -1.0,
                                    ),
                                    children: [
                                      const TextSpan(
                                        text: 'Healthcare for\n',
                                        style: TextStyle(color: Colors.white),
                                      ),
                                      TextSpan(
                                        text: 'every life you love',
                                        style: TextStyle(color: joviCoral),
                                      ),
                                    ],
                                  ),
                                  textAlign: TextAlign.center,
                                ),

                                const SizedBox(height: 16),

                                // Coral accent line under headline
                                Container(
                                  width: 60,
                                  height: 3,
                                  decoration: BoxDecoration(
                                    gradient: const LinearGradient(
                                      colors: [joviCoral, joviCoralLight],
                                    ),
                                    borderRadius: BorderRadius.circular(2),
                                  ),
                                ),

                                const SizedBox(height: 20),

                                // Family icons row
                                TweenAnimationBuilder<double>(
                                  tween: Tween(begin: 0.0, end: 1.0),
                                  duration: _Motion.enter,
                                  curve: Curves.easeOut,
                                  builder: (context, value, child) {
                                    return Opacity(
                                      opacity: value,
                                      child: Row(
                                        mainAxisAlignment:
                                            MainAxisAlignment.center,
                                        children: [
                                          Icon(Icons.person_rounded,
                                              color:
                                                  Colors.white.withOpacity(0.5),
                                              size: 22),
                                          const SizedBox(width: 8),
                                          Icon(Icons.favorite_rounded,
                                              color: joviCoral.withOpacity(0.6),
                                              size: 16),
                                          const SizedBox(width: 8),
                                          Icon(Icons.pets_rounded,
                                              color:
                                                  Colors.white.withOpacity(0.5),
                                              size: 20),
                                        ],
                                      ),
                                    );
                                  },
                                ),

                                const SizedBox(height: 20),

                                // Updated subheading
                                Container(
                                  padding: EdgeInsets.symmetric(
                                      horizontal: layoutSettings.wideMode
                                          ? 40
                                          : currentScreenType ==
                                                  ScreenType.compact
                                              ? 0
                                              : 20),
                                  child: Text(
                                    'Affordable monthly plans for your whole family — humans and pets. Low out-of-pocket costs, quick reimbursements, and the freedom to choose your own provider.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.7),
                                      fontSize: layoutSettings.bodySize,
                                      height: 1.5,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ),

                                const SizedBox(height: 28),

                                // Animated stat counters
                                TweenAnimationBuilder<double>(
                                  tween: Tween(begin: 0.0, end: 1.0),
                                  duration: _Motion.enter,
                                  curve: _Motion.settle,
                                  builder: (context, value, child) {
                                    return Opacity(
                                      opacity: value,
                                      child: Transform.translate(
                                        offset: Offset(
                                            0,
                                            _reduceMotion
                                                ? 0
                                                : 6 * (1 - value)),
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(
                                              vertical: 16, horizontal: 20),
                                          decoration: BoxDecoration(
                                            color:
                                                Colors.white.withOpacity(0.05),
                                            borderRadius:
                                                BorderRadius.circular(16),
                                            border: Border.all(
                                              color: Colors.white
                                                  .withOpacity(0.08),
                                              width: 1,
                                            ),
                                          ),
                                          child: Row(
                                            mainAxisAlignment:
                                                MainAxisAlignment.spaceEvenly,
                                            children: [
                                              _buildStatCounter('1K+',
                                                  'Members', Colors.white),
                                              Container(
                                                  width: 1,
                                                  height: 30,
                                                  color: Colors.white
                                                      .withOpacity(0.1)),
                                              _buildStatCounter('70%',
                                                  'Avg. Savings', joviCoral),
                                              Container(
                                                  width: 1,
                                                  height: 30,
                                                  color: Colors.white
                                                      .withOpacity(0.1)),
                                              _buildStatCounter(
                                                  '4.9★', 'Rating', joviGold),
                                            ],
                                          ),
                                        ),
                                      ),
                                    );
                                  },
                                ),

                                const SizedBox(height: 32),

                                // CTA Buttons
                                Container(
                                  width: double.infinity,
                                  constraints: BoxConstraints(
                                      maxWidth:
                                          layoutSettings.wideMode ? 600 : 380),
                                  padding: EdgeInsets.symmetric(
                                      horizontal: currentScreenType ==
                                              ScreenType.compact
                                          ? 0
                                          : 20),
                                  child: layoutSettings.useTwoColumnLayout
                                      ? Row(
                                          children: [
                                            Expanded(
                                                child:
                                                    _buildCreateAccountButton()),
                                            const SizedBox(width: 16),
                                            Expanded(
                                                child: _buildSignInButton()),
                                          ],
                                        )
                                      : Column(
                                          children: [
                                            _buildCreateAccountButton(),
                                            const SizedBox(height: 16),
                                            _buildSignInButton(),
                                          ],
                                        ),
                                ),

                                const SizedBox(height: 20),
                                _buildPremiumPreviewButton(),
                                const SizedBox(height: 16),
                                _buildTourButton(),
                                const SizedBox(height: 40),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              // Gradient transition
              SliverToBoxAdapter(
                child: Container(
                  height: 40,
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [joviNavyDark, joviNavy],
                    ),
                  ),
                ),
              ),

              // Benefits Section
              SliverToBoxAdapter(
                child: FadeTransition(
                  opacity: _benefitsController,
                  child: Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [joviNavy, joviNavyDark],
                      ),
                    ),
                    padding: EdgeInsets.symmetric(
                      horizontal: layoutSettings.paddingH,
                      vertical: 40,
                    ),
                    child: wrapWithConstraints(
                      child: Column(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 6),
                            decoration: BoxDecoration(
                              color: joviCoral.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              'WHY JOVI',
                              style: TextStyle(
                                color: joviCoral,
                                fontSize: layoutSettings.bodySize * 0.75,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.5,
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),
                          Text.rich(
                            TextSpan(
                              style: TextStyle(
                                fontSize: layoutSettings.headingSize * 0.9,
                                fontWeight: FontWeight.bold,
                                height: 1.2,
                                letterSpacing: -0.6,
                              ),
                              children: [
                                const TextSpan(
                                  text: 'Simple. ',
                                  style: TextStyle(color: Colors.white),
                                ),
                                TextSpan(
                                  text: 'Transparent. ',
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.4),
                                  ),
                                ),
                                const TextSpan(
                                  text: 'Affordable Health Plans',
                                  style: TextStyle(color: Colors.white),
                                ),
                              ],
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 16),
                          Container(
                            padding: EdgeInsets.symmetric(
                                horizontal: layoutSettings.wideMode
                                    ? 60
                                    : currentScreenType == ScreenType.compact
                                        ? 0
                                        : 20),
                            child: Text(
                              'Finally, a healthcare solution that puts you first with no middleman, no surprises, and real savings.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Colors.white.withOpacity(0.9),
                                fontSize: layoutSettings.bodySize,
                                height: 1.4,
                              ),
                            ),
                          ),
                          const SizedBox(height: 32),

                          // Benefit Cards
                          if (layoutSettings.useGridLayout)
                            Wrap(
                              spacing: 16,
                              runSpacing: 16,
                              children: _buildAnimatedBenefitCardsForGrid(),
                            )
                          else
                            ..._buildAnimatedBenefitCards(),

                          const SizedBox(height: 24),

                          // Clinic Feature
                          FadeTransition(
                            opacity: _clinicFeatureController,
                            child: _buildClinicFeatureContainer(),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // Gradient transition
              SliverToBoxAdapter(
                child: Container(
                  height: 30,
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [joviNavyDark, joviNavyDark],
                    ),
                  ),
                ),
              ),

              // How It Works Section
              SliverToBoxAdapter(
                child: FadeTransition(
                  opacity: _howItWorksController,
                  child: Container(
                    color: joviNavyDark,
                    padding: EdgeInsets.symmetric(
                      horizontal: layoutSettings.paddingH,
                      vertical: 40,
                    ),
                    child: wrapWithConstraints(
                      child: Column(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 6),
                            decoration: BoxDecoration(
                              color: joviCoral.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              'OUR PROCESS',
                              style: TextStyle(
                                color: joviCoral,
                                fontSize: layoutSettings.bodySize * 0.75,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.5,
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'How It Works',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: layoutSettings.headingSize * 0.9,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 32),
                          if (layoutSettings.useTwoColumnLayout)
                            Row(
                              children: [
                                Expanded(
                                    child: _buildProcessStepForGrid(
                                        1,
                                        Icons.person_add_rounded,
                                        'Create An Account',
                                        'Get started in minutes with our simple onboarding process.')),
                                _buildVerticalConnector(),
                                Expanded(
                                    child: _buildProcessStepForGrid(
                                        2,
                                        Icons.medical_services_rounded,
                                        'Choose Your Plan',
                                        'One simple, affordable plan with no hidden fees or surprises.')),
                                _buildVerticalConnector(),
                                Expanded(
                                    child: _buildProcessStepForGrid(
                                        3,
                                        Icons.savings_rounded,
                                        'Save More, Worry Less',
                                        'File claims instantly and save up to 70% on medical expenses.')),
                              ],
                            )
                          else
                            Column(
                              children: [
                                _buildProcessStep(
                                    1,
                                    Icons.person_add_rounded,
                                    'Create An Account',
                                    'Get started in minutes with our simple onboarding process.'),
                                const SizedBox(height: 20),
                                _buildConnector(),
                                const SizedBox(height: 20),
                                _buildProcessStep(
                                    2,
                                    Icons.medical_services_rounded,
                                    'Choose Your Plan',
                                    'One simple, affordable plan with no hidden fees or surprises.'),
                                const SizedBox(height: 20),
                                _buildConnector(),
                                const SizedBox(height: 20),
                                _buildProcessStep(
                                    3,
                                    Icons.savings_rounded,
                                    'Save More, Worry Less',
                                    'File claims instantly and save up to 70% on medical expenses.'),
                              ],
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // Gradient transition
              SliverToBoxAdapter(
                child: Container(
                  height: 30,
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [joviNavyDark, joviNavy],
                    ),
                  ),
                ),
              ),

              // Testimonials Section
              SliverToBoxAdapter(
                child: FadeTransition(
                  opacity: _testimonialsController,
                  child: Container(
                    color: joviNavy,
                    padding: const EdgeInsets.only(top: 40, bottom: 30),
                    child: wrapWithConstraints(
                      child: Column(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 6),
                            decoration: BoxDecoration(
                              color: joviMint.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              'TESTIMONIALS',
                              style: TextStyle(
                                color: joviMint,
                                fontSize: layoutSettings.bodySize * 0.75,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.5,
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'What Our Members Say',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: layoutSettings.headingSize * 0.9,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 32),
                          if (layoutSettings.useGridLayout)
                            Padding(
                              padding: EdgeInsets.symmetric(
                                  horizontal: layoutSettings.paddingH),
                              child: Row(
                                children: [
                                  Expanded(
                                      child: _buildTestimonialCard(
                                          'Emily T.',
                                          'Denver, CO',
                                          'Jovi Health\'s membership is hands-down the best alternative to traditional health insurance. I get direct access to providers without the insurance middleman. I wish I had signed up sooner!',
                                          0)),
                                  const SizedBox(width: 16),
                                  Expanded(
                                      child: _buildTestimonialCard(
                                          'Michael T.',
                                          'Scottsdale, AZ',
                                          'I used to pay outrageous premiums for traditional insurance, only to be hit with high out-of-pocket costs. With Jovi Health, I get unlimited access to quality care for a flat monthly fee—no hidden costs.',
                                          0)),
                                  const SizedBox(width: 16),
                                  Expanded(
                                      child: _buildTestimonialCard(
                                          'James R.',
                                          'Dallas, TX',
                                          'Since switching to Jovi Health, I have peace of mind. I pay one predictable monthly fee, and that\'s it. The membership covers everything I need, and the care is always top-notch.',
                                          0)),
                                ],
                              ),
                            )
                          else
                            SizedBox(
                              height: 320,
                              child: PageView(
                                controller: _testimonialController,
                                physics: const BouncingScrollPhysics(),
                                children: [
                                  _buildTestimonialCard(
                                      'Emily T.',
                                      'Denver, CO',
                                      'Jovi Health\'s membership is hands-down the best alternative to traditional health insurance. I get direct access to providers without the insurance middleman. I wish I had signed up sooner!',
                                      layoutSettings.paddingH),
                                  _buildTestimonialCard(
                                      'Michael T.',
                                      'Scottsdale, AZ',
                                      'I used to pay outrageous premiums for traditional insurance, only to be hit with high out-of-pocket costs. With Jovi Health, I get unlimited access to quality care for a flat monthly fee—no hidden costs.',
                                      layoutSettings.paddingH),
                                  _buildTestimonialCard(
                                      'James R.',
                                      'Colorado Springs, CO',
                                      'Since switching to Jovi Health, I have peace of mind. I pay one predictable monthly fee, and that\'s it. The membership covers everything I need, and the care is always top-notch.',
                                      layoutSettings.paddingH),
                                ],
                              ),
                            ),
                          if (!layoutSettings.useGridLayout) ...[
                            const SizedBox(height: 20),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: List.generate(
                                  3,
                                  (index) => AnimatedContainer(
                                        duration: _Motion.select,
                                        margin: const EdgeInsets.symmetric(
                                            horizontal: 4),
                                        width: _currentTestimonial == index
                                            ? 24
                                            : 8,
                                        height: 8,
                                        decoration: BoxDecoration(
                                          borderRadius:
                                              BorderRadius.circular(4),
                                          color: _currentTestimonial == index
                                              ? joviCoral
                                              : joviCoral.withOpacity(0.3),
                                        ),
                                      )),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // Gradient transition
              SliverToBoxAdapter(
                child: Container(
                  height: 30,
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [joviNavy, joviNavyDark],
                    ),
                  ),
                ),
              ),

              // FAQ Section
              SliverToBoxAdapter(
                child: FadeTransition(
                  opacity: _faqController,
                  child: Container(
                    color: joviNavyDark,
                    padding: EdgeInsets.symmetric(
                      horizontal: layoutSettings.paddingH,
                      vertical: 40,
                    ),
                    child: wrapWithConstraints(
                      child: Column(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 6),
                            decoration: BoxDecoration(
                              color: joviCoral.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              'FAQ',
                              style: TextStyle(
                                color: joviCoral,
                                fontSize: layoutSettings.bodySize * 0.75,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.5,
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          Center(
                            child: Text(
                              'Frequently Asked Questions',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: layoutSettings.headingSize * 0.9,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          const SizedBox(height: 32),
                          if (layoutSettings.useTwoColumnLayout)
                            Column(
                              children: [
                                Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Expanded(
                                          child: _buildExpandableFaq(
                                              0,
                                              'How does Jovi Health save me money?',
                                              'Studies show that paying out of pocket can save you up to 70% on medical bills. We pass these savings directly to you through our cash-pay model, eliminating the insurance middleman.')),
                                      const SizedBox(width: 16),
                                      Expanded(
                                          child: _buildExpandableFaq(
                                              1,
                                              'What if I can\'t pay upfront?',
                                              'No problem! If you don\'t have money to pay for your prescription or medical service, just upload the bill and we will reimburse your pharmacy or doctor directly.')),
                                    ]),
                                Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Expanded(
                                          child: _buildExpandableFaq(
                                              2,
                                              'How quickly do I get reimbursed?',
                                              'Our app makes it easy to upload receipts and get reimbursed quickly. Simply submit your receipt through the app, and we\'ll process your reimbursement directly—hassle-free.')),
                                      const SizedBox(width: 16),
                                      Expanded(
                                          child: _buildExpandableFaq(
                                              3,
                                              'Can I choose my own doctor?',
                                              'Yes! You choose your provider. No more in-network vs out-of-network confusion, no pre-authorization, and no coverage restrictions.')),
                                    ]),
                              ],
                            )
                          else
                            Column(
                              children: [
                                _buildExpandableFaq(
                                    0,
                                    'How does Jovi Health save me money?',
                                    'Studies show that paying out of pocket can save you up to 70% on medical bills. We pass these savings directly to you through our cash-pay model, eliminating the insurance middleman.'),
                                _buildExpandableFaq(
                                    1,
                                    'What if I can\'t pay upfront?',
                                    'No problem! If you don\'t have money to pay for your prescription or medical service, just upload the bill and we will reimburse your pharmacy or doctor directly.'),
                                _buildExpandableFaq(
                                    2,
                                    'How quickly do I get reimbursed?',
                                    'Our app makes it easy to upload receipts and get reimbursed quickly. Simply submit your receipt through the app, and we\'ll process your reimbursement directly—hassle-free.'),
                                _buildExpandableFaq(
                                    3,
                                    'Can I choose my own doctor?',
                                    'Yes! You choose your provider. No more in-network vs out-of-network confusion, no pre-authorization, and no coverage restrictions.'),
                              ],
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // Final CTA Section
              SliverToBoxAdapter(
                child: Container(
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [joviCoral, joviCoralLight],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: joviCoral.withOpacity(0.2),
                        blurRadius: 20,
                        offset: const Offset(0, -10),
                      ),
                    ],
                  ),
                  padding: EdgeInsets.symmetric(
                    horizontal: layoutSettings.paddingH,
                    vertical: 40,
                  ),
                  child: wrapWithConstraints(
                    child: Column(
                      children: [
                        // Animated beating heart
                        AnimatedBuilder(
                          animation: _heartbeatAnimation,
                          builder: (context, child) {
                            return Transform.scale(
                              scale: _heartbeatAnimation.value,
                              child: Container(
                                width: layoutSettings.iconSize * 2.5,
                                height: layoutSettings.iconSize * 2.5,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  gradient: RadialGradient(
                                    colors: [
                                      Colors.white.withOpacity(0.3),
                                      Colors.white.withOpacity(0.1),
                                    ],
                                  ),
                                ),
                                child: Icon(
                                  Icons.favorite_rounded,
                                  color: Colors.white,
                                  size: layoutSettings.iconSize * 1.4,
                                  shadows: [
                                    Shadow(
                                      color: Colors.white.withOpacity(0.5),
                                      blurRadius: 12,
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                        const SizedBox(height: 20),
                        Text(
                          'Ready to Transform\nYour Healthcare?',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: layoutSettings.headingSize * 1.1,
                            fontWeight: FontWeight.w800,
                            height: 1.1,
                            letterSpacing: -0.8,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Join thousands who are saving money and getting better care',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.9),
                            fontSize: layoutSettings.bodySize,
                          ),
                        ),
                        const SizedBox(height: 32),

                        _buildFinalCTAButton(),

                        const SizedBox(height: 40),

                        // Trust badges
                        Container(
                          constraints: BoxConstraints(
                              maxWidth: layoutSettings.wideMode ? 600 : 400),
                          child: GridView.count(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            crossAxisCount: 2,
                            childAspectRatio: 3.5,
                            mainAxisSpacing: 10,
                            crossAxisSpacing: 10,
                            children: [
                              _buildUniformTrustBadge(
                                  Icons.security_rounded, 'HIPAA Compliant'),
                              _buildUniformTrustBadge(
                                  Icons.lock_rounded, 'Secure & Private'),
                              _buildUniformTrustBadge(
                                  Icons.headset_mic_rounded, '24/7 Support'),
                              _buildUniformTrustBadge(
                                  Icons.shield_rounded, 'Bank Encryption'),
                            ],
                          ),
                        ),

                        const SizedBox(height: 30),

                        // Copyright and Version
                        Center(
                          child: Column(
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 16, vertical: 6),
                                decoration: BoxDecoration(
                                  color: Colors.white.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Center(
                                  child: Text(
                                    '© 2026 Jovi Health LLC. All rights reserved.',
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.85),
                                      fontSize: layoutSettings.bodySize * 0.8,
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(height: 8),
                              Center(
                                child: Text(
                                  appVersion,
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    color: Colors.white.withOpacity(0.6),
                                    fontSize: layoutSettings.bodySize * 0.7,
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
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // HELPER METHODS
  // ============================================================

  Widget _buildCreateAccountButton() {
    return Semantics(
      label: 'Create an account button',
      button: true,
      child: _Pressable(
          enabled: !_isCreateAccountLoading,
          feedbackOnly: true,
          child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        elevation: 8,
        shadowColor: joviCoral.withOpacity(0.3),
        child: InkWell(
          onTap: _isCreateAccountLoading
              ? null
              : () async {
                  if (_isCreateAccountLoading) return;
                  setState(() => _isCreateAccountLoading = true);
                  await _navigateWithErrorHandling('createAccount',
                      location: 'hero');
                  if (mounted) setState(() => _isCreateAccountLoading = false);
                },
          borderRadius: BorderRadius.circular(16),
          child: Ink(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: _isCreateAccountLoading
                    ? [
                        joviCoral.withOpacity(0.7),
                        joviCoralLight.withOpacity(0.7)
                      ]
                    : [joviCoral, joviCoralLight],
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Container(
              height: layoutSettings.buttonHeight,
              alignment: Alignment.center,
              child: _isCreateAccountLoading
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                          strokeWidth: 2.5,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(Colors.white)))
                  : Text('Create An Account',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: layoutSettings.bodySize + 2,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.2)),
            ),
          ),
        ),
      )),
    );
  }

  Widget _buildSignInButton() {
    return Semantics(
      label: 'Sign in to your account button',
      button: true,
      child: _Pressable(
          enabled: !_isSignInLoading,
          feedbackOnly: true,
          child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: _isSignInLoading
              ? null
              : () async {
                  if (_isSignInLoading) return;
                  setState(() => _isSignInLoading = true);
                  await _navigateWithErrorHandling('logIn', location: 'hero');
                  if (mounted) setState(() => _isSignInLoading = false);
                },
          borderRadius: BorderRadius.circular(16),
          child: Container(
            height: layoutSettings.buttonHeight,
            decoration: BoxDecoration(
              color: _isSignInLoading
                  ? Colors.white.withOpacity(0.1)
                  : Colors.transparent,
              border: Border.all(
                  color: _isSignInLoading
                      ? Colors.white.withOpacity(0.5)
                      : Colors.white,
                  width: 2.5),
              borderRadius: BorderRadius.circular(16),
            ),
            alignment: Alignment.center,
            child: _isSignInLoading
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(
                        strokeWidth: 2.5,
                        valueColor:
                            AlwaysStoppedAnimation<Color>(Colors.white)))
                : Text('Sign In',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: layoutSettings.bodySize + 2,
                        fontWeight: FontWeight.w700,
                        letterSpacing: -0.2)),
          ),
        ),
      )),
    );
  }

  Widget _buildPremiumPreviewButton() {
    return Semantics(
      label: 'Get premium preview',
      button: true,
      child: Container(
        width: double.infinity,
        constraints:
            BoxConstraints(maxWidth: layoutSettings.wideMode ? 300 : 280),
        padding: EdgeInsets.symmetric(
            horizontal: currentScreenType == ScreenType.compact ? 0 : 20),
        child: _Pressable(
            feedbackOnly: true,
            child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          child: InkWell(
            onTap: _showPremiumPreview,
            borderRadius: BorderRadius.circular(20),
            child: Container(
              height: 42,
              decoration: BoxDecoration(
                color: Colors.transparent,
                borderRadius: BorderRadius.circular(20),
                border:
                    Border.all(color: Colors.white.withOpacity(0.2), width: 1),
              ),
              alignment: Alignment.center,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.calculate_outlined,
                      color: Colors.white.withOpacity(0.6), size: 18),
                  const SizedBox(width: 8),
                  Text('Get My Quote',
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: layoutSettings.bodySize - 2,
                          fontWeight: FontWeight.w500,
                          letterSpacing: 0.2)),
                ],
              ),
            ),
          ),
        )),
      ),
    );
  }

  Widget _buildTourButton() {
    return Semantics(
      label: 'Take a tour of Jovi Health',
      button: true,
      child: Container(
        width: double.infinity,
        constraints:
            BoxConstraints(maxWidth: layoutSettings.wideMode ? 400 : 380),
        padding: EdgeInsets.symmetric(
            horizontal: currentScreenType == ScreenType.compact ? 0 : 20),
        child: _Pressable(
            feedbackOnly: true,
            child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(30),
          child: InkWell(
            onTap: () async {
              await _navigateWithErrorHandling('Tour', location: 'hero');
            },
            borderRadius: BorderRadius.circular(30),
            child: Container(
              height: 48,
              decoration: BoxDecoration(
                  color: Colors.transparent,
                  borderRadius: BorderRadius.circular(30)),
              alignment: Alignment.center,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.play_circle_outline_rounded,
                      color: Colors.white.withOpacity(0.7),
                      size: layoutSettings.iconSize * 0.9),
                  const SizedBox(width: 8),
                  Text('Take a Tour',
                      style: TextStyle(
                          color: Colors.white.withOpacity(0.7),
                          fontSize: layoutSettings.bodySize,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.3)),
                ],
              ),
            ),
          ),
        )),
      ),
    );
  }

  Widget _buildFinalCTAButton() {
    return Semantics(
      label: 'Create an account - bottom call to action',
      button: true,
      child: Container(
        constraints: BoxConstraints(
            maxWidth: layoutSettings.wideMode ? 400 : double.infinity),
        child: _Pressable(
            enabled: !_isFinalCTALoading,
            feedbackOnly: true,
            child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(16),
          elevation: 8,
          shadowColor: Colors.black.withOpacity(0.3),
          child: InkWell(
            onTap: _isFinalCTALoading
                ? null
                : () async {
                    if (_isFinalCTALoading) return;
                    setState(() => _isFinalCTALoading = true);
                    await _navigateWithErrorHandling('createAccount',
                        location: 'footer_cta');
                    if (mounted) setState(() => _isFinalCTALoading = false);
                  },
            borderRadius: BorderRadius.circular(16),
            child: Ink(
              decoration: BoxDecoration(
                color: _isFinalCTALoading
                    ? Colors.white.withOpacity(0.8)
                    : Colors.white,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Container(
                height: layoutSettings.buttonHeight + 12,
                padding: const EdgeInsets.symmetric(horizontal: 40),
                alignment: Alignment.center,
                child: _isFinalCTALoading
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            valueColor:
                                AlwaysStoppedAnimation<Color>(joviCoral)))
                    : Text('Create An Account',
                        style: TextStyle(
                            color: joviCoral,
                            fontSize: layoutSettings.bodySize + 4,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.2)),
              ),
            ),
          ),
        )),
      ),
    );
  }

  Widget _buildVerticalConnector() {
    return Container(
      width: 30,
      height: 2,
      margin: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        gradient: LinearGradient(
            colors: [joviCoral.withOpacity(0.3), joviCoral.withOpacity(0.1)]),
      ),
    );
  }

  Widget _buildConnector() {
    return Container(
      width: 2,
      height: 30,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [joviCoral.withOpacity(0.3), joviCoral.withOpacity(0.1)],
        ),
      ),
    );
  }

  Widget _buildProcessStepForGrid(
      int number, IconData icon, String title, String description) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
              color: joviCoral.withOpacity(0.08),
              blurRadius: 20,
              offset: const Offset(0, 8))
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          onTap: null,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(20),
            child: Column(children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: [
                    joviCoral.withOpacity(0.1),
                    joviCoral.withOpacity(0.05)
                  ]),
                  shape: BoxShape.circle,
                ),
                child: Stack(alignment: Alignment.center, children: [
                  Icon(icon, color: joviCoral, size: 32),
                  Positioned(
                      top: 0,
                      right: 0,
                      child: Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                              colors: [joviMint, joviMintDark]),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                                color: joviMint.withOpacity(0.3),
                                blurRadius: 8,
                                offset: const Offset(0, 2))
                          ],
                        ),
                        child: Center(
                            child: Text('$number',
                                style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold))),
                      )),
                ]),
              ),
              const SizedBox(height: 16),
              Text(title,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: joviNavy,
                      fontSize: 18,
                      fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              Text(description,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      color: const Color(0xFF6B7280),
                      fontSize: layoutSettings.bodySize - 1,
                      height: 1.4)),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _buildProcessStep(
      int number, IconData icon, String title, String description) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
              color: joviCoral.withOpacity(0.08),
              blurRadius: 20,
              offset: const Offset(0, 8))
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        child: InkWell(
          onTap: null,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(20),
            child: Row(children: [
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: [
                    joviCoral.withOpacity(0.1),
                    joviCoral.withOpacity(0.05)
                  ]),
                  shape: BoxShape.circle,
                ),
                child: Stack(alignment: Alignment.center, children: [
                  Icon(icon, color: joviCoral, size: 32),
                  Positioned(
                      top: 0,
                      right: 0,
                      child: Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                              colors: [joviMint, joviMintDark]),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                                color: joviMint.withOpacity(0.3),
                                blurRadius: 8,
                                offset: const Offset(0, 2))
                          ],
                        ),
                        child: Center(
                            child: Text('$number',
                                style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold))),
                      )),
                ]),
              ),
              const SizedBox(width: 20),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    Text(title,
                        style: TextStyle(
                            color: joviNavy,
                            fontSize: currentScreenType == ScreenType.compact
                                ? 16
                                : 18,
                            fontWeight: FontWeight.bold)),
                    const SizedBox(height: 6),
                    Text(description,
                        style: TextStyle(
                            color: const Color(0xFF6B7280),
                            fontSize: layoutSettings.bodySize - 1,
                            height: 1.4)),
                  ])),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _buildTestimonialCard(
      String name, String location, String testimonial, double padding) {
    return Container(
      margin: EdgeInsets.symmetric(horizontal: padding),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Colors.white, Color(0xFFFAFBFC)]),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
              color: joviCoral.withOpacity(0.08),
              blurRadius: 20,
              offset: const Offset(0, 10))
        ],
      ),
      child: Container(
        padding: const EdgeInsets.all(24),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                gradient:
                    const LinearGradient(colors: [joviCoral, joviCoralLight]),
                shape: BoxShape.circle,
              ),
              child: Center(
                  child: Text(name.substring(0, 1),
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold))),
            ),
            const SizedBox(width: 12),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name,
                  style: TextStyle(
                      color: joviNavy,
                      fontSize: layoutSettings.bodySize,
                      fontWeight: FontWeight.bold)),
              Text(location,
                  style: TextStyle(
                      color: const Color(0xFF6B7280),
                      fontSize: layoutSettings.bodySize - 2)),
            ]),
            const Spacer(),
            Icon(Icons.format_quote_rounded,
                color: joviCoral.withOpacity(0.2), size: 32),
          ]),
          const SizedBox(height: 20),
          Row(
              children: List.generate(
                  5,
                  (index) =>
                      Icon(Icons.star_rounded, color: joviGold, size: 18))),
          const SizedBox(height: 16),
          Expanded(
              child: Text('"$testimonial"',
                  style: TextStyle(
                      color: const Color(0xFF374151),
                      fontSize: layoutSettings.bodySize,
                      height: 1.6,
                      fontStyle: FontStyle.italic))),
        ]),
      ),
    );
  }

  Widget _buildExpandableFaq(int index, String question, String answer) {
    final isExpanded = _expandedFaqs.contains(index);
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
            color: isExpanded
                ? joviCoral.withOpacity(0.3)
                : const Color(0xFFE5E7EB),
            width: isExpanded ? 2 : 1),
        boxShadow: isExpanded
            ? [
                BoxShadow(
                    color: joviCoral.withOpacity(0.08),
                    blurRadius: 16,
                    offset: const Offset(0, 6))
              ]
            : [
                BoxShadow(
                    color: Colors.black.withOpacity(0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 2))
              ],
      ),
      child: _Pressable(
          feedbackOnly: true,
          pressedScale: 0.985,
          child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: () {
            HapticFeedback.selectionClick();
            setState(() {
              if (isExpanded) {
                _expandedFaqs.remove(index);
              } else {
                _expandedFaqs.add(index);
              }
            });
          },
          borderRadius: BorderRadius.circular(16),
          child: AnimatedContainer(
            duration: _Motion.select,
            padding: EdgeInsets.all(isExpanded ? 24 : 20),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                      color: isExpanded
                          ? joviCoral.withOpacity(0.1)
                          : const Color(0xFFF3F4F6),
                      shape: BoxShape.circle),
                  child: Center(
                      child: Text('${index + 1}',
                          style: TextStyle(
                              color: isExpanded
                                  ? joviCoral
                                  : const Color(0xFF6B7280),
                              fontWeight: FontWeight.bold,
                              fontSize: 14))),
                ),
                const SizedBox(width: 12),
                Expanded(
                    child: Text(question,
                        style: TextStyle(
                            color: joviNavy,
                            fontSize: layoutSettings.bodySize,
                            fontWeight: FontWeight.w700))),
                AnimatedRotation(
                  turns: isExpanded ? 0.5 : 0,
                  duration: _Motion.select,
                  child: Icon(Icons.expand_more_rounded,
                      color: isExpanded ? joviCoral : const Color(0xFF6B7280),
                      size: 28),
                ),
              ]),
              AnimatedCrossFade(
                firstChild: const SizedBox.shrink(),
                secondChild: Padding(
                  padding: const EdgeInsets.only(top: 16, left: 44),
                  child: Text(answer,
                      style: TextStyle(
                          color: const Color(0xFF4B5563),
                          fontSize: layoutSettings.bodySize - 1,
                          height: 1.6)),
                ),
                crossFadeState: isExpanded
                    ? CrossFadeState.showSecond
                    : CrossFadeState.showFirst,
                duration: _Motion.select,
              ),
            ]),
          ),
        ),
      )),
    );
  }

  Widget _buildStatCounter(String value, String label, Color valueColor) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(
            fontSize: layoutSettings.bodySize + 2,
            fontWeight: FontWeight.w800,
            color: valueColor,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: TextStyle(
            fontSize: layoutSettings.bodySize * 0.7,
            fontWeight: FontWeight.w500,
            color: Colors.white.withOpacity(0.4),
          ),
        ),
      ],
    );
  }

  Widget _buildUniformTrustBadge(IconData icon, String text) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.3), width: 1.5),
        boxShadow: [
          BoxShadow(
              color: Colors.white.withOpacity(0.1),
              blurRadius: 8,
              offset: const Offset(0, 2))
        ],
      ),
      child: Center(
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        Icon(icon, color: Colors.white, size: layoutSettings.iconSize * 0.6),
        const SizedBox(width: 6),
        Flexible(
            child: Text(text,
                style: TextStyle(
                    color: Colors.white,
                    fontSize: layoutSettings.bodySize * 0.7,
                    fontWeight: FontWeight.w600),
                overflow: TextOverflow.ellipsis)),
      ])),
    );
  }

  Widget _buildClinicFeatureContainer() {
    return Container(
      constraints: BoxConstraints(
          maxWidth: layoutSettings.wideMode ? 700 : double.infinity),
      decoration: BoxDecoration(
        gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.white.withOpacity(0.95),
              Colors.white.withOpacity(0.90)
            ]),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.3), width: 2),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 20,
              offset: const Offset(0, 10))
        ],
      ),
      padding: EdgeInsets.all(layoutSettings.wideMode ? 32 : 24),
      child: Column(children: [
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Container(
            width: layoutSettings.wideMode ? 64 : 56,
            height: layoutSettings.wideMode ? 64 : 56,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [joviMint, joviMintDark]),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                    color: joviMint.withOpacity(0.3),
                    blurRadius: 12,
                    offset: const Offset(0, 4))
              ],
            ),
            child: Icon(Icons.local_hospital_rounded,
                color: Colors.white, size: layoutSettings.wideMode ? 36 : 30),
          ),
          const SizedBox(width: 16),
          Container(
            width: layoutSettings.wideMode ? 64 : 56,
            height: layoutSettings.wideMode ? 64 : 56,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                  colors: [Color(0xFF10B981), Color(0xFF059669)]),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                    color: const Color(0xFF10B981).withOpacity(0.3),
                    blurRadius: 12,
                    offset: const Offset(0, 4))
              ],
            ),
            child: Icon(Icons.home_work_rounded,
                color: Colors.white, size: layoutSettings.wideMode ? 36 : 30),
          ),
        ]),
        const SizedBox(height: 20),
        Text('Flexible Care Options',
            style: TextStyle(
                color: joviNavy,
                fontSize: layoutSettings.headingSize * 0.7,
                fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          decoration: BoxDecoration(
            color: joviMint.withOpacity(0.1),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: joviMint.withOpacity(0.3), width: 1),
          ),
          child: Text('NO CO-PAY AT JOVI CLINICS',
              style: TextStyle(
                  color: joviMint,
                  fontSize: layoutSettings.bodySize * 0.8,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.2)),
        ),
        const SizedBox(height: 20),
        Container(
          padding: EdgeInsets.symmetric(
              horizontal: layoutSettings.wideMode ? 40 : 0),
          child: Text(
              'Get care your way - schedule in-person clinic visits or schedule telehealth from home. Your health, your choice.',
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: const Color(0xFF374151),
                  fontSize: layoutSettings.bodySize,
                  height: 1.5)),
        ),
        const SizedBox(height: 24),
        Row(mainAxisAlignment: MainAxisAlignment.spaceEvenly, children: [
          Expanded(
              child: Column(children: [
            Container(
                width: layoutSettings.wideMode ? 56 : 48,
                height: layoutSettings.wideMode ? 56 : 48,
                decoration: BoxDecoration(
                    color: joviCoral.withOpacity(0.1), shape: BoxShape.circle),
                child: Icon(Icons.business_rounded,
                    color: joviCoral, size: layoutSettings.wideMode ? 28 : 24)),
            const SizedBox(height: 8),
            Text('In-Person',
                style: TextStyle(
                    color: joviNavy,
                    fontSize: layoutSettings.bodySize * 0.85,
                    fontWeight: FontWeight.bold),
                textAlign: TextAlign.center),
            Text('Walk-ins Welcome',
                style: TextStyle(
                    color: const Color(0xFF6B7280),
                    fontSize: layoutSettings.bodySize * 0.7),
                textAlign: TextAlign.center),
          ])),
          Expanded(
              child: Column(children: [
            Container(
                width: layoutSettings.wideMode ? 56 : 48,
                height: layoutSettings.wideMode ? 56 : 48,
                decoration: BoxDecoration(
                    color: joviNavy.withOpacity(0.1), shape: BoxShape.circle),
                child: Icon(Icons.video_call_rounded,
                    color: joviNavy, size: layoutSettings.wideMode ? 28 : 24)),
            const SizedBox(height: 8),
            Text('Telehealth',
                style: TextStyle(
                    color: joviNavy,
                    fontSize: layoutSettings.bodySize * 0.85,
                    fontWeight: FontWeight.bold),
                textAlign: TextAlign.center),
            Text('24/7 Available',
                style: TextStyle(
                    color: const Color(0xFF6B7280),
                    fontSize: layoutSettings.bodySize * 0.7),
                textAlign: TextAlign.center),
          ])),
          Expanded(
              child: Column(children: [
            Container(
                width: layoutSettings.wideMode ? 56 : 48,
                height: layoutSettings.wideMode ? 56 : 48,
                decoration: BoxDecoration(
                    color: joviGold.withOpacity(0.15), shape: BoxShape.circle),
                child: Icon(Icons.local_hospital_rounded,
                    color: joviGold, size: layoutSettings.wideMode ? 28 : 24)),
            const SizedBox(height: 8),
            Text('Clinic Visits',
                style: TextStyle(
                    color: joviNavy,
                    fontSize: layoutSettings.bodySize * 0.85,
                    fontWeight: FontWeight.bold),
                textAlign: TextAlign.center),
            Text('No Co-Pay',
                style: TextStyle(
                    color: const Color(0xFF6B7280),
                    fontSize: layoutSettings.bodySize * 0.7),
                textAlign: TextAlign.center),
          ])),
        ]),
      ]),
    );
  }

  List<Widget> _buildAnimatedBenefitCardsForGrid() {
    final benefits = [
      {
        'icon': Icons.money_off_rounded,
        'color': joviCoral,
        'title': 'No More High Costs',
        'subtitle':
            'Your coverage kicks in quick. No hidden fees, no surprise bills.'
      },
      {
        'icon': Icons.medical_services_rounded,
        'color': joviNavy,
        'title': 'You Choose Your Provider',
        'subtitle':
            'No more in-network vs out-of-network confusion or restrictions.'
      },
      {
        'icon': Icons.phone_iphone_rounded,
        'color': joviMint,
        'title': 'Easy Mobile App',
        'subtitle':
            'Submit claims, get instant reimbursements, and track your out-of-pocket spending.'
      },
      {
        'icon': Icons.savings_rounded,
        'color': joviGold,
        'title': 'Save Up to 70%',
        'subtitle':
            'On medical bills with our cash-pay model that cuts out the middleman.'
      },
      {
        'icon': Icons.speed_rounded,
        'color': joviCoralLight,
        'title': 'Low Out-of-Pocket',
        'subtitle':
            'Simple, easy-to-meet out-of-pocket amount before the community kicks in for you.'
      },
    ];
    return List.generate(benefits.length, (index) {
      return SlideTransition(
          position: _cardSlideAnimations[index],
          child: FadeTransition(
              opacity: _cardFadeAnimations[index],
              child: Container(
                width: (MediaQuery.of(context).size.width -
                        layoutSettings.paddingH * 2 -
                        32) /
                    2,
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                          color: Colors.black.withOpacity(0.08),
                          blurRadius: 16,
                          offset: const Offset(0, 6))
                    ]),
                child: Material(
                    color: Colors.transparent,
                    borderRadius: BorderRadius.circular(16),
                    child: InkWell(
                        onTap: null,
                        borderRadius: BorderRadius.circular(16),
                        child: Container(
                          padding: const EdgeInsets.all(18),
                          child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                    width: 52,
                                    height: 52,
                                    decoration: BoxDecoration(
                                        gradient: LinearGradient(colors: [
                                          (benefits[index]['color'] as Color)
                                              .withOpacity(0.15),
                                          (benefits[index]['color'] as Color)
                                              .withOpacity(0.05)
                                        ]),
                                        borderRadius:
                                            BorderRadius.circular(14)),
                                    child: Icon(
                                        benefits[index]['icon'] as IconData,
                                        color:
                                            benefits[index]['color'] as Color,
                                        size: 28)),
                                const SizedBox(height: 12),
                                Text(benefits[index]['title'] as String,
                                    style: TextStyle(
                                        color: joviNavy,
                                        fontSize: 17,
                                        fontWeight: FontWeight.bold)),
                                const SizedBox(height: 8),
                                Text(benefits[index]['subtitle'] as String,
                                    style: TextStyle(
                                        fontSize: layoutSettings.bodySize - 1,
                                        color: const Color(0xFF6B7280),
                                        height: 1.4)),
                              ]),
                        ))),
              )));
    });
  }

  List<Widget> _buildAnimatedBenefitCards() {
    final benefits = [
      {
        'icon': Icons.money_off_rounded,
        'color': joviCoral,
        'title': 'No More High Costs',
        'subtitle':
            'Your coverage kicks in quick. No hidden fees, no surprise bills.'
      },
      {
        'icon': Icons.medical_services_rounded,
        'color': joviNavy,
        'title': 'You Choose Your Provider',
        'subtitle':
            'No more in-network vs out-of-network confusion or restrictions.'
      },
      {
        'icon': Icons.phone_iphone_rounded,
        'color': joviMint,
        'title': 'Easy Mobile App',
        'subtitle':
            'Submit claims, get instant reimbursements, and track your out-of-pocket spending.'
      },
      {
        'icon': Icons.savings_rounded,
        'color': joviGold,
        'title': 'Save Up to 70%',
        'subtitle':
            'On medical bills with our cash-pay model that cuts out the middleman.'
      },
      {
        'icon': Icons.speed_rounded,
        'color': joviCoralLight,
        'title': 'Low Out-of-Pocket',
        'subtitle':
            'Simple, easy-to-meet out-of-pocket amount before the community kicks in for you.'
      },
    ];
    return List.generate(benefits.length, (index) {
      return Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: SlideTransition(
              position: _cardSlideAnimations[index],
              child: FadeTransition(
                  opacity: _cardFadeAnimations[index],
                  child: Container(
                    decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                              color: Colors.black.withOpacity(0.08),
                              blurRadius: 16,
                              offset: const Offset(0, 6))
                        ]),
                    child: Material(
                        color: Colors.transparent,
                        borderRadius: BorderRadius.circular(16),
                        child: InkWell(
                            onTap: null,
                            borderRadius: BorderRadius.circular(16),
                            child: Container(
                              padding: const EdgeInsets.all(18),
                              child: Row(children: [
                                Container(
                                    width: 52,
                                    height: 52,
                                    decoration: BoxDecoration(
                                        gradient: LinearGradient(colors: [
                                          (benefits[index]['color'] as Color)
                                              .withOpacity(0.15),
                                          (benefits[index]['color'] as Color)
                                              .withOpacity(0.05)
                                        ]),
                                        borderRadius:
                                            BorderRadius.circular(14)),
                                    child: Icon(
                                        benefits[index]['icon'] as IconData,
                                        color:
                                            benefits[index]['color'] as Color,
                                        size: 28)),
                                const SizedBox(width: 16),
                                Expanded(
                                    child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                      Text(benefits[index]['title'] as String,
                                          style: TextStyle(
                                              color: joviNavy,
                                              fontSize: currentScreenType ==
                                                      ScreenType.compact
                                                  ? 15
                                                  : 17,
                                              fontWeight: FontWeight.bold)),
                                      const SizedBox(height: 4),
                                      Text(
                                          benefits[index]['subtitle'] as String,
                                          style: TextStyle(
                                              fontSize:
                                                  layoutSettings.bodySize - 1,
                                              color: const Color(0xFF6B7280),
                                              height: 1.4)),
                                    ])),
                              ]),
                            ))),
                  ))));
    });
  }
}
