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
// JOVI HEALTH - UPDATE MEMBERSHIP WIDGET (REBRANDED)
// Version: 2026.09.22-r3 (Apple HIG pass: press feedback, painted glass
//          sections, readable dialogs, camera/library picker, Reduce Motion,
//          navy toasts, mounted guards). Payment is still simulated — see
//          _processPayment; Zoho Payments wiring is pending.
// r2:      2026.04.16-navy (coral pets + jovi terminology + coral confetti)
// Build: JC-OU-0922-002
// Part 1 of 10: Imports, Constants, Breed Lists, Enums, Config
// ============================================================

import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' as ui_dart;

import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';

// ─── Dog Breeds ─────────────────────────────────────────────
const List<String> dogBreeds = [
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

// ─── Cat Breeds ─────────────────────────────────────────────
const List<String> catBreeds = [
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

// ─── Dog Breed Max Age (years) ──────────────────────────────
const Map<String, int> dogBreedMaxAge = {
  'Affenpinscher': 15,
  'Afghan Hound': 14,
  'Airedale Terrier': 12,
  'Akita': 12,
  'Alaskan Malamute': 12,
  'American Bulldog': 15,
  'American Eskimo Dog': 15,
  'American Foxhound': 13,
  'American Pit Bull Terrier': 14,
  'American Staffordshire Terrier': 14,
  'Australian Cattle Dog': 16,
  'Australian Shepherd': 15,
  'Basenji': 14,
  'Basset Hound': 12,
  'Beagle': 15,
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
  'Chinese Crested': 15,
  'Chinese Shar-Pei': 10,
  'Chow Chow': 12,
  'Cocker Spaniel': 14,
  'Collie': 14,
  'Corgi (Pembroke Welsh)': 14,
  'Corgi (Cardigan Welsh)': 14,
  'Dachshund': 16,
  'Dalmatian': 13,
  'Doberman Pinscher': 12,
  'English Setter': 14,
  'English Springer Spaniel': 14,
  'French Bulldog': 12,
  'German Shepherd': 13,
  'German Shorthaired Pointer': 14,
  'Golden Retriever': 12,
  'Gordon Setter': 12,
  'Great Dane': 8,
  'Great Pyrenees': 12,
  'Greyhound': 13,
  'Havanese': 16,
  'Irish Setter': 14,
  'Irish Wolfhound': 8,
  'Italian Greyhound': 15,
  'Jack Russell Terrier': 16,
  'Japanese Chin': 14,
  'Keeshond': 13,
  'Kerry Blue Terrier': 13,
  'Labrador Retriever': 13,
  'Lhasa Apso': 15,
  'Maltese': 15,
  'Mastiff': 10,
  'Miniature Pinscher': 15,
  'Miniature Schnauzer': 14,
  'Newfoundland': 10,
  'Norfolk Terrier': 14,
  'Norwegian Elkhound': 14,
  'Old English Sheepdog': 12,
  'Papillon': 16,
  'Pekingese': 14,
  'Pointer': 14,
  'Pomeranian': 16,
  'Poodle (Standard)': 14,
  'Poodle (Miniature)': 16,
  'Poodle (Toy)': 16,
  'Pug': 14,
  'Rhodesian Ridgeback': 12,
  'Rottweiler': 10,
  'Saint Bernard': 10,
  'Samoyed': 14,
  'Schipperke': 15,
  'Scottish Terrier': 13,
  'Shetland Sheepdog': 14,
  'Shiba Inu': 15,
  'Shih Tzu': 16,
  'Siberian Husky': 14,
  'Soft Coated Wheaten Terrier': 14,
  'Staffordshire Bull Terrier': 14,
  'Vizsla': 14,
  'Weimaraner': 13,
  'West Highland White Terrier': 15,
  'Whippet': 14,
  'Wire Fox Terrier': 15,
  'Yorkshire Terrier': 16,
  'Mixed Breed (Small)': 16,
  'Mixed Breed (Medium)': 14,
  'Mixed Breed (Large)': 12,
  'Other': 14,
};

// ─── Cat Breed Max Age (years) ──────────────────────────────
const Map<String, int> catBreedMaxAge = {
  'Abyssinian': 15,
  'American Bobtail': 15,
  'American Curl': 16,
  'American Shorthair': 18,
  'American Wirehair': 16,
  'Balinese': 20,
  'Bengal': 16,
  'Birman': 16,
  'Bombay': 17,
  'British Longhair': 15,
  'British Shorthair': 17,
  'Burmese': 18,
  'Burmilla': 15,
  'Chartreux': 15,
  'Chausie': 14,
  'Cornish Rex': 16,
  'Devon Rex': 15,
  'Domestic Longhair': 17,
  'Domestic Medium Hair': 17,
  'Domestic Shorthair': 18,
  'Egyptian Mau': 15,
  'Exotic Shorthair': 15,
  'Havana Brown': 15,
  'Himalayan': 15,
  'Japanese Bobtail': 16,
  'Javanese': 15,
  'Korat': 15,
  'LaPerm': 15,
  'Maine Coon': 15,
  'Manx': 14,
  'Munchkin': 14,
  'Nebelung': 16,
  'Norwegian Forest Cat': 16,
  'Ocicat': 15,
  'Oriental Longhair': 15,
  'Oriental Shorthair': 15,
  'Persian': 17,
  'Peterbald': 14,
  'Pixie-Bob': 14,
  'Ragamuffin': 16,
  'Ragdoll': 17,
  'Russian Blue': 18,
  'Savannah': 17,
  'Scottish Fold': 15,
  'Selkirk Rex': 15,
  'Siamese': 20,
  'Siberian': 17,
  'Singapura': 15,
  'Snowshoe': 16,
  'Somali': 14,
  'Sphynx': 15,
  'Thai': 16,
  'Tonkinese': 16,
  'Toyger': 15,
  'Turkish Angora': 17,
  'Turkish Van': 17,
  'Mixed Breed': 17,
  'Other': 16,
};

// ─── Promo Code Definitions ─────────────────────────────────
const Map<String, double> promoCodes = {
  'WELCOME10': 10.0,
  'SAVE25': 25.0,
  'FIRSTMONTH': 100.0, // 100% off first month
  'FAMILY20': 20.0,
};

// ─── Enums ──────────────────────────────────────────────────
enum OnboardingUpdateStep {
  review, // 0 – Review current info
  editPersonal, // 1 – Edit personal details
  editSpouse, // 2 – Edit spouse
  editDependents, // 3 – Edit dependents
  editCoverage, // 4 – Edit plan options
  editPets, // 5 – Edit pet plan
  quoteSummary, // 6 – Quote & promo codes
  payment, // 7 – Payment
  confirmation, // 8 – Confirmation
}

// ─── Responsive Config ──────────────────────────────────────
class ResponsiveConfig {
  final double maxWidth;
  final double horizontalPadding;
  final double fieldSpacing;
  final double sectionSpacing;
  final int columnsPerRow;
  final double fontSize;
  final double headerFontSize;
  final double buttonHeight;
  final double avatarRadius;
  final bool showLabelsAbove;

  const ResponsiveConfig({
    required this.maxWidth,
    required this.horizontalPadding,
    required this.fieldSpacing,
    required this.sectionSpacing,
    required this.columnsPerRow,
    required this.fontSize,
    required this.headerFontSize,
    required this.buttonHeight,
    required this.avatarRadius,
    required this.showLabelsAbove,
  });

  static ResponsiveConfig of(BuildContext context) {
    final w = MediaQuery.of(context).size.width;
    if (w < 600) {
      return const ResponsiveConfig(
        maxWidth: double.infinity,
        horizontalPadding: 16,
        fieldSpacing: 12,
        sectionSpacing: 20,
        columnsPerRow: 1,
        fontSize: 14,
        headerFontSize: 22,
        buttonHeight: 48,
        avatarRadius: 40,
        showLabelsAbove: true,
      );
    } else if (w < 900) {
      return const ResponsiveConfig(
        maxWidth: 680,
        horizontalPadding: 24,
        fieldSpacing: 14,
        sectionSpacing: 24,
        columnsPerRow: 2,
        fontSize: 14.5,
        headerFontSize: 24,
        buttonHeight: 50,
        avatarRadius: 48,
        showLabelsAbove: true,
      );
    } else {
      return const ResponsiveConfig(
        maxWidth: 840,
        horizontalPadding: 32,
        fieldSpacing: 16,
        sectionSpacing: 28,
        columnsPerRow: 3,
        fontSize: 15,
        headerFontSize: 26,
        buttonHeight: 52,
        avatarRadius: 52,
        showLabelsAbove: false,
      );
    }
  }
}

// ─── Jovi Brand Color Constants ─────────────────────────────
const Color joviCoral = Color(0xFFFF6B4A);
const Color joviCoralLight = Color(0xFFFF8F73);
const Color joviNavy = Color(0xFF1A2744);
const Color joviNavyDark = Color(0xFF0F1A2E);
const Color joviWarmWhite = Color(0xFFFFF8F5);
const Color joviMint = Color(0xFF00D4AA);
const Color joviMintDark = Color(0xFF00B894);
const Color joviGold = Color(0xFFFFD166);
const Color joviSoftStone = Color(0xFFF0EFEB);

// ─── Legacy aliases (mapped to Jovi palette) ───────────────
const Color kPrimaryBlue = joviNavy; // primary actions → navy
const Color kPrimaryLight = joviCoralLight; // secondary accents → coral light
const Color kAccentGreen = joviMint; // success/positive → mint
const Color kWarningOrange = joviGold; // warnings → gold
const Color kErrorRed = Color(0xFFE53935); // kept standard red for errors
const Color kSurfaceGrey = Color(0xFF1E2D4A); // surface → dark navy glass
const Color kBorderGrey = Color(0x26FFFFFF); // white @ 15%
const Color kTextDark = Colors.white; // text → white on navy bg
const Color kTextMedium = Color(0xB3FFFFFF); // white @ 70%
const Color kTextLight = Color(0x80FFFFFF); // white @ 50%
const Color kPetPurple = joviCoral; // pets → coral (unified)
const Color kPetPurpleLight =
    Color(0x1FFF6B4A); // coral @ 12% (matches onboarding pet accent)

// ============================================================
// Part 2 of 10: Widget Declaration & State Variables
// ============================================================

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

class OnboardingUpdateWidget extends StatefulWidget {
  const OnboardingUpdateWidget({
    super.key,
    this.width,
    this.height,
  });

  final double? width;
  final double? height;

  @override
  State<OnboardingUpdateWidget> createState() => _OnboardingUpdateWidgetState();
}

class _OnboardingUpdateWidgetState extends State<OnboardingUpdateWidget>
    with TickerProviderStateMixin {
  // ─── Navigation ─────────────────────────────────────────
  OnboardingUpdateStep _currentStep = OnboardingUpdateStep.review;
  bool _isLoading = true;
  bool _isSaving = false;
  String? _errorMessage;

  // ─── Auth ───────────────────────────────────────────────
  User? _currentUser;
  String _userId = '';

  // ─── Primary Member ─────────────────────────────────────
  final _firstNameCtrl = TextEditingController();
  final _lastNameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _dobCtrl = TextEditingController();
  final _ssnCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  final _stateCtrl = TextEditingController();
  final _zipCtrl = TextEditingController();
  String _gender = 'Male';
  Uint8List? _profilePhotoBytes;
  String _profilePhotoUrl = '';

  // ─── Spouse ─────────────────────────────────────────────
  bool _hasSpouse = false;
  final _spouseFirstNameCtrl = TextEditingController();
  final _spouseLastNameCtrl = TextEditingController();
  final _spouseDobCtrl = TextEditingController();
  final _spouseSsnCtrl = TextEditingController();
  String _spouseGender = 'Female';
  Uint8List? _spousePhotoBytes;
  String _spousePhotoUrl = '';

  // ─── Dependents ─────────────────────────────────────────
  int _numDependents = 0;
  final List<TextEditingController> _depFirstName = [];
  final List<TextEditingController> _depLastName = [];
  final List<TextEditingController> _depDob = [];
  final List<TextEditingController> _depSsn = [];
  final List<String> _depGender = [];
  final List<String> _depRelationship = [];
  final List<Uint8List?> _depPhotoBytes = [];
  final List<String> _depPhotoUrls = [];

  // ─── Plan Options ───────────────────────────────────────
  bool _hasTobacco = false;
  bool _spouseHasTobacco = false;
  bool _hasDental = false;
  bool _hasVision = false;
  String _planTier = 'Individual'; // Individual, Couple, Family
  double _healthDeductible = 1500.0;

  // ─── Pet Plan ───────────────────────────────────────────
  int _numPets = 0;
  final List<TextEditingController> _petName = [];
  final List<TextEditingController> _petAge = [];
  final List<TextEditingController> _petBirthdate = [];
  final List<String> _petType = []; // 'Dog' or 'Cat'
  final List<String> _petGender = []; // 'Male' or 'Female'
  final List<String> _petBreed = [];
  final List<Uint8List?> _petPhotoBytes = [];
  final List<String> _petPhotoUrls = [];
  final List<bool> _petPreExistingAck = [];
  final List<TextEditingController> _petPreExistingControllers = [];
  final List<bool> _petCardExpanded = [];
  final List<bool> _petCoverageExpanded = [];
  final List<String?> _petAgeWarnings = [];
  final List<String?> _petNameWarnings = [];
  final List<AnimationController?> _petAnimControllers = [];
  final List<Animation<double>?> _petAnimations = [];
  List<Map<String, dynamic>> _petQuotes = [];
  double _petTotalPremium = 0;

  // ─── Promo / Referral Codes ────────────────────────────
  final _promoCodeCtrl = TextEditingController();
  final _referralCodeCtrl = TextEditingController();
  double _discountAmount = 0.0;
  double _discountPercentage = 0.0;
  String _promoCodeApplied = '';
  bool _hasReferralDiscount = false;

  // ─── Quote ──────────────────────────────────────────────
  double _primaryPremium = 0;
  double _spousePremium = 0;
  double _dependentPremium = 0;
  double _totalHealthPremium = 0;
  double _grandTotal = 0;
  bool _quoteReady = false;

  // ─── Payment ────────────────────────────────────────────
  final _cardNumberCtrl = TextEditingController();
  final _cardExpCtrl = TextEditingController();
  final _cardCvcCtrl = TextEditingController();
  final _cardNameCtrl = TextEditingController();
  final _cardZipCtrl = TextEditingController();
  bool _isProcessingPayment = false;
  bool _paymentSuccess = false;

  // ─── Confetti (custom – no external package) ───────────
  bool _showConfetti = false;
  late AnimationController _confettiAnimController;
  final List<_ConfettiParticle> _confettiParticles = [];

  // ─── Scroll ─────────────────────────────────────────────
  final _scrollController = ScrollController();

  // ─── Original Data (for change detection) ───────────────
  Map<String, dynamic> _originalData = {};

  // ─── Form Keys ──────────────────────────────────────────
  final _personalFormKey = GlobalKey<FormState>();
  final _spouseFormKey = GlobalKey<FormState>();
  final _dependentFormKey = GlobalKey<FormState>();
  final _coverageFormKey = GlobalKey<FormState>();
  final _petFormKey = GlobalKey<FormState>();
  final _paymentFormKey = GlobalKey<FormState>();

  // ============================================================
  // Part 3 of 10: Lifecycle, Auth, Data Loading & Saving
  // ============================================================

  @override
  void initState() {
    super.initState();
    _confettiAnimController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..addStatusListener((status) {
        if (status == AnimationStatus.completed) {
          setState(() => _showConfetti = false);
        }
      });
    _initAuth();
  }

  void _playConfetti() {
    if (_platformReduceMotion()) return; // Reduce Motion: no particle burst
    final rand = Random();
    _confettiParticles.clear();
    for (int i = 0; i < 80; i++) {
      _confettiParticles.add(_ConfettiParticle(
        x: rand.nextDouble(),
        y: -rand.nextDouble() * 0.3,
        speed: 0.3 + rand.nextDouble() * 0.7,
        drift: (rand.nextDouble() - 0.5) * 0.4,
        size: 4 + rand.nextDouble() * 6,
        color: [
          joviCoral,
          joviCoralLight,
          joviMint,
          joviGold,
          joviNavy,
          Colors.white,
        ][rand.nextInt(6)],
        rotation: rand.nextDouble() * 6.28,
        rotSpeed: (rand.nextDouble() - 0.5) * 4,
      ));
    }
    setState(() => _showConfetti = true);
    _confettiAnimController.forward(from: 0);
  }

  Future<void> _initAuth() async {
    try {
      _currentUser = FirebaseAuth.instance.currentUser;
      if (_currentUser == null) {
        if (!mounted) return;
        setState(() {
          _isLoading = false;
          _errorMessage = 'Please sign in to update your membership.';
        });
        return;
      }
      _userId = _currentUser!.uid;
      await _loadUserData();
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to initialize: $e';
      });
    }
  }

  Future<void> _loadUserData() async {
    try {
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(_userId)
          .get();

      if (!mounted) return;
      if (!doc.exists) {
        setState(() {
          _isLoading = false;
          _errorMessage =
              'No membership data found. Please complete onboarding first.';
        });
        return;
      }

      final data = doc.data()!;
      _originalData = Map<String, dynamic>.from(data);

      // ── Primary Member ──
      _firstNameCtrl.text = data['firstName'] ?? '';
      _lastNameCtrl.text = data['lastName'] ?? '';
      _emailCtrl.text = data['email'] ?? '';
      _phoneCtrl.text = data['phone'] ?? '';
      _dobCtrl.text = data['dob'] ?? '';
      _ssnCtrl.text = data['ssn'] ?? '';
      _addressCtrl.text = data['address'] ?? '';
      _cityCtrl.text = data['city'] ?? '';
      _stateCtrl.text = data['state'] ?? '';
      _zipCtrl.text = data['zip'] ?? '';
      _gender = data['gender'] ?? 'Male';
      _profilePhotoUrl = data['profilePhotoUrl'] ?? '';

      // ── Spouse ──
      _hasSpouse = data['hasSpouse'] ?? false;
      if (_hasSpouse) {
        _spouseFirstNameCtrl.text = data['spouseFirstName'] ?? '';
        _spouseLastNameCtrl.text = data['spouseLastName'] ?? '';
        _spouseDobCtrl.text = data['spouseDob'] ?? '';
        _spouseSsnCtrl.text = data['spouseSsn'] ?? '';
        _spouseGender = data['spouseGender'] ?? 'Female';
        _spousePhotoUrl = data['spousePhotoUrl'] ?? '';
      }

      // ── Dependents ──
      _numDependents = data['numDependents'] ?? 0;
      final depList = data['dependents'] as List<dynamic>? ?? [];
      for (int i = 0; i < _numDependents && i < depList.length; i++) {
        final dep = depList[i] is String
            ? jsonDecode(depList[i] as String) as Map<String, dynamic>
            : depList[i] as Map<String, dynamic>;
        _addDependentSlot(
          firstName: dep['firstName'] ?? '',
          lastName: dep['lastName'] ?? '',
          dob: dep['dob'] ?? '',
          ssn: dep['ssn'] ?? '',
          gender: dep['gender'] ?? 'Male',
          relationship: dep['relationship'] ?? 'Child',
          photoUrl: dep['photo_url'] ?? '',
        );
      }

      // ── Plan Options ──
      _hasTobacco = data['hasTobacco'] ?? false;
      _spouseHasTobacco = data['spouseHasTobacco'] ?? false;
      _hasDental = data['hasDental'] ?? false;
      _hasVision = data['hasVision'] ?? false;
      _planTier = data['planTier'] ?? 'Individual';
      _healthDeductible = (data['healthDeductible'] ?? 1500).toDouble();

      // ── Pet Plan ──
      final hasPets = data['hasPetInsurance'] ?? false;
      _numPets = data['numPets'] ?? 0;
      if (hasPets && _numPets > 0) {
        final petList = data['pets'] as List<dynamic>? ?? [];
        for (int i = 0; i < _numPets && i < petList.length; i++) {
          final pet = petList[i] is String
              ? jsonDecode(petList[i] as String) as Map<String, dynamic>
              : petList[i] as Map<String, dynamic>;
          _addPetSlot(
            name: pet['name'] ?? '',
            type: pet['type'] ?? 'Dog',
            breed: pet['breed'] ?? '',
            gender: pet['gender'] ?? 'Male',
            ageInMonths: pet['ageInMonths'] ?? 0,
            birthdate: pet['birthdate'] ?? '',
            photoUrl: pet['photo_url'] ?? '',
            hasPreExisting: pet['hasPreExistingConditions'] ?? false,
            preExistingNotes: pet['preExistingNotes'] ?? '',
            premium: (pet['premium'] ?? 60.0).toDouble(),
            petId: pet['petId'] ?? '',
            expanded: false,
          );
        }
        _petTotalPremium = (data['petTotalPremium'] ?? 0).toDouble();
      }

      // ── Promo Codes ──
      _promoCodeApplied = data['promoCodeApplied'] ?? '';
      _discountPercentage = (data['discountPercentage'] ?? 0).toDouble();
      _discountAmount = (data['discountAmount'] ?? 0).toDouble();
      _hasReferralDiscount = data['hasReferralDiscount'] ?? false;
      if (_promoCodeApplied.isNotEmpty) {
        _promoCodeCtrl.text = _promoCodeApplied;
      }

      // ── Compute initial quote ──
      _computeQuote();

      setState(() => _isLoading = false);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = 'Failed to load data: $e';
      });
    }
  }

  // ─── Add Dependent Slot ────────────────────────────────
  void _addDependentSlot({
    String firstName = '',
    String lastName = '',
    String dob = '',
    String ssn = '',
    String gender = 'Male',
    String relationship = 'Child',
    String photoUrl = '',
  }) {
    _depFirstName.add(TextEditingController(text: firstName));
    _depLastName.add(TextEditingController(text: lastName));
    _depDob.add(TextEditingController(text: dob));
    _depSsn.add(TextEditingController(text: ssn));
    _depGender.add(gender);
    _depRelationship.add(relationship);
    _depPhotoBytes.add(null);
    _depPhotoUrls.add(photoUrl);
  }

  // ─── Add Pet Slot ──────────────────────────────────────
  void _addPetSlot({
    String name = '',
    String type = 'Dog',
    String breed = '',
    String gender = 'Male',
    int ageInMonths = 0,
    String birthdate = '',
    String photoUrl = '',
    bool hasPreExisting = false,
    String preExistingNotes = '',
    double premium = 60.0,
    String petId = '',
    bool expanded = true,
  }) {
    _petName.add(TextEditingController(text: name));
    _petType.add(type);
    _petBreed.add(breed);
    _petGender.add(gender);

    // Convert ageInMonths back to display string
    String ageText = '';
    if (ageInMonths > 0) {
      final years = ageInMonths ~/ 12;
      final months = ageInMonths % 12;
      if (years > 0 && months > 0) {
        ageText = '${years}y ${months}m';
      } else if (years > 0) {
        ageText = '${years}y';
      } else {
        ageText = '${months}m';
      }
    }
    _petAge.add(TextEditingController(text: ageText));
    _petBirthdate.add(TextEditingController(text: birthdate));

    _petPhotoBytes.add(null);
    _petPhotoUrls.add(photoUrl);
    _petPreExistingAck.add(hasPreExisting);
    _petPreExistingControllers
        .add(TextEditingController(text: preExistingNotes));
    _petCardExpanded.add(expanded);
    _petCoverageExpanded.add(false);
    _petAgeWarnings.add(null);
    _petNameWarnings.add(null);

    // Animation controller for card slide-in
    final animCtrl = AnimationController(
      vsync: this,
      duration: _Motion.enter,
    );
    final anim = CurvedAnimation(parent: animCtrl, curve: _Motion.settle);
    _petAnimControllers.add(animCtrl);
    _petAnimations.add(anim);

    if (expanded) {
      animCtrl.forward();
    } else {
      animCtrl.value = 1.0;
    }

    _petQuotes.add({
      'petId': petId.isNotEmpty ? petId : _generatePetId(),
      'premium': premium,
      'deductible': 500,
      'reimbursement': 90,
    });
  }

  String _generatePetId() {
    final rand = Random();
    return 'pet_${DateTime.now().millisecondsSinceEpoch}_${rand.nextInt(9999)}';
  }

  // ─── Remove Dependent ──────────────────────────────────
  void _removeDependent(int index) {
    if (index < 0 || index >= _numDependents) return;
    _depFirstName[index].dispose();
    _depLastName[index].dispose();
    _depDob[index].dispose();
    _depSsn[index].dispose();
    _depFirstName.removeAt(index);
    _depLastName.removeAt(index);
    _depDob.removeAt(index);
    _depSsn.removeAt(index);
    _depGender.removeAt(index);
    _depRelationship.removeAt(index);
    _depPhotoBytes.removeAt(index);
    _depPhotoUrls.removeAt(index);
    setState(() => _numDependents--);
    _computeQuote();
  }

  // ─── Remove Pet ───────────────────────────────────────
  void _removePet(int index) {
    if (index < 0 || index >= _numPets) return;
    _petName[index].dispose();
    _petAge[index].dispose();
    _petBirthdate[index].dispose();
    _petPreExistingControllers[index].dispose();
    _petAnimControllers[index]?.dispose();

    _petName.removeAt(index);
    _petAge.removeAt(index);
    _petBirthdate.removeAt(index);
    _petType.removeAt(index);
    _petGender.removeAt(index);
    _petBreed.removeAt(index);
    _petPhotoBytes.removeAt(index);
    _petPhotoUrls.removeAt(index);
    _petPreExistingAck.removeAt(index);
    _petPreExistingControllers.removeAt(index);
    _petCardExpanded.removeAt(index);
    _petCoverageExpanded.removeAt(index);
    _petAgeWarnings.removeAt(index);
    _petNameWarnings.removeAt(index);
    _petAnimControllers.removeAt(index);
    _petAnimations.removeAt(index);
    _petQuotes.removeAt(index);

    setState(() => _numPets--);
    _computePetQuotes();
    _computeQuote();
  }

  // ─── Save All Data ─────────────────────────────────────
  Future<bool> _saveData() async {
    setState(() => _isSaving = true);
    try {
      // Build dependents array
      final dependents = List<String>.generate(
          _numDependents,
          (i) => jsonEncode({
                'firstName': _depFirstName[i].text.trim(),
                'lastName': _depLastName[i].text.trim(),
                'dob': _depDob[i].text.trim(),
                'ssn': _depSsn[i].text.trim(),
                'gender': _depGender[i],
                'relationship': _depRelationship[i],
                'photo_url': _depPhotoUrls[i],
              }));

      // Build pets array
      final pets = List<String>.generate(
          _numPets,
          (i) => jsonEncode({
                'name': _petName[i].text.trim(),
                'type': _petType[i],
                'breed': _petBreed[i],
                'gender': _petGender[i],
                'ageInMonths': _parseAgeToMonths(_petAge[i].text),
                'birthdate': _petBirthdate[i].text.trim(),
                'petId': _petQuotes[i]['petId'],
                'premium': _petQuotes[i]['premium'],
                'deductible': 500,
                'reimbursement': 90,
                'photo_url': _petPhotoUrls[i],
                'hasPreExistingConditions': _petPreExistingAck[i],
                'preExistingNotes': _petPreExistingControllers[i].text.trim(),
              }));

      final updateData = <String, dynamic>{
        // Primary Member
        'firstName': _firstNameCtrl.text.trim(),
        'lastName': _lastNameCtrl.text.trim(),
        'email': _emailCtrl.text.trim(),
        'phone': _phoneCtrl.text.trim(),
        'dob': _dobCtrl.text.trim(),
        'ssn': _ssnCtrl.text.trim(),
        'address': _addressCtrl.text.trim(),
        'city': _cityCtrl.text.trim(),
        'state': _stateCtrl.text.trim(),
        'zip': _zipCtrl.text.trim(),
        'gender': _gender,
        'profilePhotoUrl': _profilePhotoUrl,

        // Spouse
        'hasSpouse': _hasSpouse,
        'spouseFirstName': _spouseFirstNameCtrl.text.trim(),
        'spouseLastName': _spouseLastNameCtrl.text.trim(),
        'spouseDob': _spouseDobCtrl.text.trim(),
        'spouseSsn': _spouseSsnCtrl.text.trim(),
        'spouseGender': _spouseGender,
        'spousePhotoUrl': _spousePhotoUrl,

        // Dependents
        'numDependents': _numDependents,
        'dependents': dependents,

        // Plan
        'hasTobacco': _hasTobacco,
        'spouseHasTobacco': _spouseHasTobacco,
        'hasDental': _hasDental,
        'hasVision': _hasVision,
        'planTier': _planTier,
        'healthDeductible': _healthDeductible,

        // Pet Plan
        'hasPetInsurance': _numPets > 0,
        'numPets': _numPets,
        'pets': pets,
        'petTotalPremium': _petTotalPremium,

        // Promo / Referral
        'promoCodeApplied': _promoCodeApplied,
        'discountPercentage': _discountPercentage,
        'discountAmount': _discountAmount,
        'hasReferralDiscount': _hasReferralDiscount,

        // Quote
        'totalHealthPremium': _totalHealthPremium,
        'grandTotal': _grandTotal,

        // Metadata
        'lastUpdated': FieldValue.serverTimestamp(),
        'updatedBy': _userId,
      };

      await FirebaseFirestore.instance
          .collection('users')
          .doc(_userId)
          .update(updateData);

      if (mounted) setState(() => _isSaving = false);
      return true;
    } catch (e) {
      if (mounted) {
        setState(() {
          _isSaving = false;
          _errorMessage = 'Failed to save: $e';
        });
      }
      return false;
    }
  }

  // ─── Progress Auto-Save (call between steps) ───────────
  Future<void> _autoSaveProgress() async {
    try {
      await FirebaseFirestore.instance.collection('users').doc(_userId).update({
        'updateInProgress': true,
        'updateStep': _currentStep.index,
        'lastUpdated': FieldValue.serverTimestamp(),
      });
    } catch (_) {
      // Silently fail on auto-save
    }
  }

  // ============================================================
  // Part 4 of 10: Dispose, Promo, Pet Premium, Photo, Validation
  // ============================================================

  @override
  void dispose() {
    // Primary
    _firstNameCtrl.dispose();
    _lastNameCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _dobCtrl.dispose();
    _ssnCtrl.dispose();
    _addressCtrl.dispose();
    _cityCtrl.dispose();
    _stateCtrl.dispose();
    _zipCtrl.dispose();

    // Spouse
    _spouseFirstNameCtrl.dispose();
    _spouseLastNameCtrl.dispose();
    _spouseDobCtrl.dispose();
    _spouseSsnCtrl.dispose();

    // Dependents
    for (final c in _depFirstName) {
      c.dispose();
    }
    for (final c in _depLastName) {
      c.dispose();
    }
    for (final c in _depDob) {
      c.dispose();
    }
    for (final c in _depSsn) {
      c.dispose();
    }

    // Pet Plan
    for (final c in _petName) {
      c.dispose();
    }
    for (final c in _petAge) {
      c.dispose();
    }
    for (final c in _petBirthdate) {
      c.dispose();
    }
    for (final c in _petPreExistingControllers) {
      c.dispose();
    }
    for (final c in _petAnimControllers) {
      c?.dispose();
    }

    // Promo
    _promoCodeCtrl.dispose();
    _referralCodeCtrl.dispose();

    // Payment
    _cardNumberCtrl.dispose();
    _cardExpCtrl.dispose();
    _cardCvcCtrl.dispose();
    _cardNameCtrl.dispose();
    _cardZipCtrl.dispose();

    // Confetti
    _confettiAnimController.dispose();

    // Scroll
    _scrollController.dispose();

    super.dispose();
  }

  // ─── Pet Premium Calculation ──────────────────────────
  double _calculatePetPremium(int ageInMonths) {
    // Base: $60/month for 8-11 months or 1 year
    // +$7 per year after year 1
    if (ageInMonths <= 0) return 60.0;
    if (ageInMonths >= 2 && ageInMonths <= 11) return 60.0;
    int ageInYears = (ageInMonths / 12).floor();
    if (ageInYears >= 1 && ageInYears <= 20) {
      return 60.0 + ((ageInYears - 1) * 7.0);
    }
    return 60.0;
  }

  // ─── Parse Age String to Months ───────────────────────
  int _parseAgeToMonths(String ageText) {
    if (ageText.isEmpty) return 0;
    final text = ageText.trim().toLowerCase();

    // Parse "Xy Zm" format  e.g. "2y 3m"
    final regYM = RegExp(r'(\d+)\s*y(?:ear|rs?)?\s*(\d+)\s*m(?:onth|onths|o)?');
    final matchYM = regYM.firstMatch(text);
    if (matchYM != null) {
      return int.parse(matchYM.group(1)!) * 12 + int.parse(matchYM.group(2)!);
    }

    // Parse "Xy" format  e.g. "3y" or "3 years"
    final regY = RegExp(r'(\d+)\s*y(?:ear|rs?)?$');
    final matchY = regY.firstMatch(text);
    if (matchY != null) {
      return int.parse(matchY.group(1)!) * 12;
    }

    // Parse "Xm" format  e.g. "8m" or "8 months"
    final regM = RegExp(r'(\d+)\s*m(?:onth|onths|o)?$');
    final matchM = regM.firstMatch(text);
    if (matchM != null) {
      return int.parse(matchM.group(1)!);
    }

    // Try plain number → treat as years if >= 2, else months
    final plain = int.tryParse(text);
    if (plain != null) {
      return plain >= 2 ? plain * 12 : plain;
    }

    return 0;
  }

  // ─── Birthdate → Age Calculator ───────────────────────
  void _calculateAgeFromBirthdate(int petIndex) {
    final text = _petBirthdate[petIndex].text.trim();
    if (text.isEmpty) return;

    DateTime? birthDate;
    try {
      birthDate = DateFormat('MM/dd/yyyy').parseStrict(text);
    } catch (_) {}
    if (birthDate == null) {
      try {
        birthDate = DateFormat('MM-dd-yyyy').parseStrict(text);
      } catch (_) {}
    }
    if (birthDate == null) {
      try {
        birthDate = DateFormat('yyyy-MM-dd').parseStrict(text);
      } catch (_) {}
    }

    if (birthDate == null) return;

    final now = DateTime.now();
    if (birthDate.isAfter(now)) return;

    int totalMonths =
        (now.year - birthDate.year) * 12 + (now.month - birthDate.month);
    if (now.day < birthDate.day) totalMonths--;
    if (totalMonths < 0) totalMonths = 0;

    final years = totalMonths ~/ 12;
    final months = totalMonths % 12;
    String ageStr;
    if (years > 0 && months > 0) {
      ageStr = '${years}y ${months}m';
    } else if (years > 0) {
      ageStr = '${years}y';
    } else {
      ageStr = '${months}m';
    }

    setState(() {
      _petAge[petIndex].text = ageStr;
    });
    _validatePetAge(petIndex);
    _computePetQuotes();
  }

  // ─── Validate Pet Age ─────────────────────────────────
  void _validatePetAge(int petIndex) {
    final months = _parseAgeToMonths(_petAge[petIndex].text);

    if (months > 0 && months < 2) {
      setState(() {
        _petAgeWarnings[petIndex] =
            'Minimum enrollment age is 8 weeks (2 months).';
      });
      return;
    }

    final breed = _petBreed[petIndex];
    if (breed.isEmpty) {
      setState(() => _petAgeWarnings[petIndex] = null);
      return;
    }

    final years = months / 12.0;
    final maxAgeMap =
        _petType[petIndex] == 'Cat' ? catBreedMaxAge : dogBreedMaxAge;
    final expectedMax = maxAgeMap[breed];
    if (expectedMax != null && years > expectedMax + 2) {
      setState(() {
        _petAgeWarnings[petIndex] =
            'Average lifespan for ${breed}s is ~$expectedMax years. Please verify the age.';
      });
    } else {
      setState(() => _petAgeWarnings[petIndex] = null);
    }
  }

  // ─── Validate Pet Name ────────────────────────────────
  void _validatePetName(int petIndex) {
    final name = _petName[petIndex].text.trim();
    if (name.isEmpty) {
      setState(() => _petNameWarnings[petIndex] = null);
      return;
    }
    // Check for duplicate names
    for (int i = 0; i < _numPets; i++) {
      if (i != petIndex &&
          _petName[i].text.trim().toLowerCase() == name.toLowerCase()) {
        setState(() {
          _petNameWarnings[petIndex] = 'You already have a pet named "$name".';
        });
        return;
      }
    }
    setState(() => _petNameWarnings[petIndex] = null);
  }

  // ─── Compute Pet Quotes ───────────────────────────────
  void _computePetQuotes() {
    double total = 0;
    for (int i = 0; i < _numPets; i++) {
      final ageMonths = _parseAgeToMonths(_petAge[i].text);
      final premium = _calculatePetPremium(ageMonths);
      _petQuotes[i]['premium'] = premium;
      total += premium;
    }
    _petTotalPremium = total;
  }

  // ─── Compute Full Quote ────────────────────────────────
  void _computeQuote() {
    // Base health premium per person: $250/month
    double basePremium = 250.0;

    // Primary
    _primaryPremium = basePremium;
    if (_hasTobacco) _primaryPremium *= 1.15;
    if (_hasDental) _primaryPremium += 35.0;
    if (_hasVision) _primaryPremium += 15.0;

    // Spouse
    _spousePremium = 0;
    if (_hasSpouse) {
      _spousePremium = basePremium;
      if (_spouseHasTobacco) _spousePremium *= 1.15;
      if (_hasDental) _spousePremium += 35.0;
      if (_hasVision) _spousePremium += 15.0;
    }

    // Dependents
    _dependentPremium = 0;
    for (int i = 0; i < _numDependents; i++) {
      double depPrem = basePremium * 0.6; // 60% rate for dependents
      if (_hasDental) depPrem += 25.0;
      if (_hasVision) depPrem += 10.0;
      _dependentPremium += depPrem;
    }

    _totalHealthPremium = _primaryPremium + _spousePremium + _dependentPremium;

    // Compute pet premiums
    _computePetQuotes();

    // Grand total: health + pets
    double total = _totalHealthPremium + _petTotalPremium;

    // Apply discount
    if (_discountPercentage > 0) {
      _discountAmount = total * (_discountPercentage / 100.0);
    }
    total -= _discountAmount;
    if (_hasReferralDiscount) {
      total -= 25.0; // $25 referral discount
    }
    if (total < 0) total = 0;

    _grandTotal = total;
    _quoteReady = true;

    if (mounted) setState(() {});
  }

  // ─── Apply Promo Code ──────────────────────────────────
  void _applyPromoCode() {
    final code = _promoCodeCtrl.text.trim().toUpperCase();
    if (code.isEmpty) {
      _showSnackBar('Please enter a promo code.', isError: true);
      return;
    }
    if (promoCodes.containsKey(code)) {
      setState(() {
        _promoCodeApplied = code;
        _discountPercentage = promoCodes[code]!;
      });
      _computeQuote();
      _showSnackBar(
          'Promo code "$code" applied! ${_discountPercentage.toStringAsFixed(0)}% discount.');
    } else {
      _showSnackBar('Invalid promo code.', isError: true);
    }
  }

  void _removePromoCode() {
    setState(() {
      _promoCodeApplied = '';
      _discountPercentage = 0;
      _discountAmount = 0;
      _promoCodeCtrl.clear();
    });
    _computeQuote();
    _showSnackBar('Promo code removed.');
  }

  void _applyReferralCode() {
    final code = _referralCodeCtrl.text.trim();
    if (code.isEmpty) {
      _showSnackBar('Please enter a referral code.', isError: true);
      return;
    }
    // In production, validate against Firestore
    setState(() => _hasReferralDiscount = true);
    _computeQuote();
    _showSnackBar('Referral code applied! \$25 discount added.');
  }

  // ─── Photo source (camera or library) ─────────────────
  Future<ImageSource?> _pickImageSource() {
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

  // ─── Pet Photo Upload ──────────────────────────────────
  Future<void> _pickPetPhoto(int petIndex) async {
    try {
      final source = await _pickImageSource();
      if (source == null || !mounted) return;
      final picker = ImagePicker();
      final picked = await picker.pickImage(
        source: source,
        maxWidth: 600,
        maxHeight: 600,
        imageQuality: 80,
      );
      if (picked == null) return;

      final bytes = await picked.readAsBytes();
      if (!mounted) return;
      setState(() => _petPhotoBytes[petIndex] = bytes);

      // Upload to Firebase Storage
      final ref = FirebaseStorage.instance
          .ref('pet_photos/$_userId/${_petQuotes[petIndex]['petId']}.jpg');
      await ref.putData(bytes, SettableMetadata(contentType: 'image/jpeg'));
      final url = await ref.getDownloadURL();
      if (!mounted) return;
      setState(() => _petPhotoUrls[petIndex] = url);
    } catch (e) {
      _showSnackBar('Failed to upload pet photo: $e', isError: true);
    }
  }

  // ─── Generic Photo Upload ─────────────────────────────
  Future<void> _pickProfilePhoto() async {
    try {
      final source = await _pickImageSource();
      if (source == null || !mounted) return;
      final picker = ImagePicker();
      final picked = await picker.pickImage(
        source: source,
        maxWidth: 600,
        maxHeight: 600,
        imageQuality: 80,
      );
      if (picked == null) return;

      final bytes = await picked.readAsBytes();
      if (!mounted) return;
      setState(() => _profilePhotoBytes = bytes);

      final ref =
          FirebaseStorage.instance.ref('profile_photos/$_userId/profile.jpg');
      await ref.putData(bytes, SettableMetadata(contentType: 'image/jpeg'));
      final url = await ref.getDownloadURL();
      if (!mounted) return;
      setState(() => _profilePhotoUrl = url);
    } catch (e) {
      _showSnackBar('Failed to upload photo: $e', isError: true);
    }
  }

  Future<void> _pickSpousePhoto() async {
    try {
      final source = await _pickImageSource();
      if (source == null || !mounted) return;
      final picker = ImagePicker();
      final picked = await picker.pickImage(
        source: source,
        maxWidth: 600,
        maxHeight: 600,
        imageQuality: 80,
      );
      if (picked == null) return;

      final bytes = await picked.readAsBytes();
      if (!mounted) return;
      setState(() => _spousePhotoBytes = bytes);

      final ref =
          FirebaseStorage.instance.ref('profile_photos/$_userId/spouse.jpg');
      await ref.putData(bytes, SettableMetadata(contentType: 'image/jpeg'));
      final url = await ref.getDownloadURL();
      if (!mounted) return;
      setState(() => _spousePhotoUrl = url);
    } catch (e) {
      _showSnackBar('Failed to upload photo: $e', isError: true);
    }
  }

  Future<void> _pickDependentPhoto(int depIndex) async {
    try {
      final source = await _pickImageSource();
      if (source == null || !mounted) return;
      final picker = ImagePicker();
      final picked = await picker.pickImage(
        source: source,
        maxWidth: 600,
        maxHeight: 600,
        imageQuality: 80,
      );
      if (picked == null) return;

      final bytes = await picked.readAsBytes();
      if (!mounted) return;
      setState(() => _depPhotoBytes[depIndex] = bytes);

      final ref = FirebaseStorage.instance
          .ref('profile_photos/$_userId/dep_$depIndex.jpg');
      await ref.putData(bytes, SettableMetadata(contentType: 'image/jpeg'));
      final url = await ref.getDownloadURL();
      if (!mounted) return;
      setState(() => _depPhotoUrls[depIndex] = url);
    } catch (e) {
      _showSnackBar('Failed to upload photo: $e', isError: true);
    }
  }

  // ─── Snackbar Helper ──────────────────────────────────
  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(message,
        accent: isError ? kErrorRed : joviMint,
        icon: isError
            ? CupertinoIcons.exclamationmark_circle
            : CupertinoIcons.checkmark_circle,
        duration: Duration(seconds: isError ? 4 : 3)));
  }

  // ─── Scroll to Top ────────────────────────────────────
  void _scrollToTop() {
    if (_scrollController.hasClients) {
      if (_platformReduceMotion()) {
        _scrollController.jumpTo(0);
      } else {
        _scrollController.animateTo(
          0,
          duration: _Motion.enter,
          curve: _Motion.settle,
        );
      }
    }
  }

  // ─── Step Navigation ──────────────────────────────────
  void _goToStep(OnboardingUpdateStep step) {
    setState(() {
      _currentStep = step;
      _errorMessage = null;
    });
    _scrollToTop();
    _autoSaveProgress();
  }

  void _goNext() {
    final nextIndex = _currentStep.index + 1;
    if (nextIndex < OnboardingUpdateStep.values.length) {
      _goToStep(OnboardingUpdateStep.values[nextIndex]);
    }
  }

  void _goBack() {
    final prevIndex = _currentStep.index - 1;
    if (prevIndex >= 0) {
      _goToStep(OnboardingUpdateStep.values[prevIndex]);
    }
  }

  // ============================================================
  // Part 5 of 10: Dialogs, Pickers, Payment, Breed Dropdown
  // ============================================================

  // ─── Date Picker ──────────────────────────────────────
  Future<void> _pickDate(TextEditingController ctrl,
      {bool isPet = false}) async {
    final now = DateTime.now();
    final initial = DateTime(now.year - (isPet ? 3 : 30), now.month, now.day);
    final first = DateTime(isPet ? now.year - 25 : 1920);
    final last = now;

    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: first,
      lastDate: last,
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.light(
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
      ctrl.text = DateFormat('MM/dd/yyyy').format(picked);
    }
  }

  // ─── Searchable Breed Dropdown ────────────────────────
  Future<String?> _showSearchableBreedDropdown(String petType) async {
    final breeds = petType == 'Cat' ? catBreeds : dogBreeds;
    String searchText = '';

    return showDialog<String>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(builder: (ctx, setDialogState) {
          final filtered = searchText.isEmpty
              ? breeds
              : breeds
                  .where(
                      (b) => b.toLowerCase().contains(searchText.toLowerCase()))
                  .toList();

          // Navy surface: the default light dialog rendered this widget's
          // white text and white icons on white.
          return AlertDialog(
            backgroundColor: kSurfaceGrey,
            surfaceTintColor: Colors.transparent,
            titleTextStyle: const TextStyle(
                color: Colors.white, fontSize: 17, fontWeight: FontWeight.w600),
            contentTextStyle: const TextStyle(color: Colors.white),
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                const Icon(Icons.pets, color: joviCoral),
                const SizedBox(width: 8),
                Text('Select ${petType == "Cat" ? "Cat" : "Dog"} Breed'),
              ],
            ),
            content: SizedBox(
              width: double.maxFinite,
              height: 400,
              child: Column(
                children: [
                  TextField(
                    autofocus: true,
                    autocorrect: false,
                    cursorColor: joviCoral,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintStyle: const TextStyle(color: kTextLight),
                      hintText: 'Search breeds…',
                      prefixIcon: const Icon(Icons.search, color: kTextLight),
                      filled: true,
                      fillColor: kSurfaceGrey,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 12),
                    ),
                    onChanged: (v) => setDialogState(() => searchText = v),
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: filtered.isEmpty
                        ? Center(
                            child: Text(
                              'No breeds match "$searchText"',
                              style: const TextStyle(color: kTextLight),
                            ),
                          )
                        : ListView.builder(
                            itemCount: filtered.length,
                            itemBuilder: (_, i) {
                              return ListTile(
                                dense: true,
                                title: Text(filtered[i],
                                    style:
                                        const TextStyle(color: Colors.white)),
                                leading: const Icon(Icons.pets,
                                    size: 18, color: joviCoral),
                                onTap: () => Navigator.of(ctx).pop(filtered[i]),
                              );
                            },
                          ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(null),
                child:
                    const Text('Cancel', style: TextStyle(color: kTextMedium)),
              ),
            ],
          );
        });
      },
    );
  }

  // ─── Pet Plan Details Dialog ──────────────────────────
  void _showPetCoverageDialog() {
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: kSurfaceGrey,
          surfaceTintColor: Colors.transparent,
          titleTextStyle: const TextStyle(color: Colors.white),
          contentTextStyle: const TextStyle(color: Colors.white),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: kPetPurpleLight,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.pets, color: joviCoral, size: 24),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Text(
                  'Pet Plan Coverage',
                  style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white),
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _coverageDetailRow(Icons.local_hospital, 'Accidents & Injuries',
                    'Broken bones, lacerations, ingested objects, and more.'),
                _coverageDetailRow(Icons.medical_services, 'Illnesses',
                    'Cancer, infections, digestive issues, allergies, and chronic conditions.'),
                _coverageDetailRow(Icons.healing, 'Surgery & Hospitalization',
                    'All surgical procedures and hospital stays.'),
                _coverageDetailRow(Icons.medication, 'Prescriptions',
                    'Medications prescribed by your veterinarian.'),
                _coverageDetailRow(Icons.science, 'Diagnostic Tests',
                    'Blood work, X-rays, MRIs, CT scans, and ultrasounds.'),
                _coverageDetailRow(Icons.emergency, 'Emergency Care',
                    '24/7 emergency and urgent care visits.'),
                _coverageDetailRow(Icons.favorite, 'Specialist Care',
                    'Referrals to veterinary specialists and oncologists.'),
                _coverageDetailRow(Icons.psychology, 'Behavioral Therapy',
                    'Treatment for anxiety, aggression, and behavioral issues.'),
                const Divider(height: 24),
                const Text(
                  'Plan Details',
                  style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 15),
                ),
                const SizedBox(height: 8),
                _coverageStat('Reimbursement Rate', '90%'),
                _coverageStat('Your Responsibility (annual)', '\$500'),
                _coverageStat('Annual Limit', 'Unlimited'),
                _coverageStat('Waiting Period', '14 days (accidents: none)'),
              ],
            ),
          ),
          actions: [
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx),
              style: ElevatedButton.styleFrom(
                backgroundColor: joviCoral,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8)),
              ),
              child: const Text('Got it'),
            ),
          ],
        );
      },
    );
  }

  Widget _coverageDetailRow(IconData icon, String title, String desc) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: joviCoral),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                        fontSize: 13.5)),
                const SizedBox(height: 2),
                Text(desc,
                    style: const TextStyle(color: kTextMedium, fontSize: 12.5)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _coverageStat(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: kTextMedium, fontSize: 13)),
          Text(value,
              style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 13)),
        ],
      ),
    );
  }

  // ─── Confirmation Dialog ──────────────────────────────
  Future<bool> _showConfirmDialog(String title, String message) async {
    // Removing a person or pet from the plan is destructive; iOS members
    // expect the system alert with a red action for that.
    final result = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) {
        return CupertinoAlertDialog(
          title: Text(title),
          content: Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(message),
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
              child: const Text('Remove'),
            ),
          ],
        );
      },
    );
    return result ?? false;
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

  // ─── Process Payment ──────────────────────────────────
  Future<void> _processPayment() async {
    if (!(_paymentFormKey.currentState?.validate() ?? false)) return;

    setState(() => _isProcessingPayment = true);

    try {
      // NOTE: no charge is made here. This is a placeholder delay until the
      // Zoho Payments integration lands; the card fields above are not sent
      // anywhere. Do not ship this step live without wiring the processor.
      await Future.delayed(const Duration(seconds: 2));
      if (!mounted) return;

      // Save the final data
      final saved = await _saveData();
      if (!saved) throw Exception('Failed to save membership data.');

      // Mark update complete
      await FirebaseFirestore.instance.collection('users').doc(_userId).update({
        'updateInProgress': false,
        'updateCompletedAt': FieldValue.serverTimestamp(),
        'paymentStatus': 'completed',
      });

      if (!mounted) return;
      setState(() {
        _isProcessingPayment = false;
        _paymentSuccess = true;
      });

      _goToStep(OnboardingUpdateStep.confirmation);
      _playConfetti();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isProcessingPayment = false;
        _errorMessage = 'Payment failed: $e';
      });
      _showSnackBar('Payment failed. Please try again.', isError: true);
    }
  }

  // ============================================================
  // Part 6 of 10: build(), Header, Step Router, Loading/Error
  // ============================================================

  @override
  Widget build(BuildContext context) {
    final config = ResponsiveConfig.of(context);

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: Scaffold(
        backgroundColor: joviNavy,
        body: Stack(
          children: [
            // Main content
            _isLoading
                ? _buildLoadingState()
                : _errorMessage != null &&
                        _currentStep == OnboardingUpdateStep.review
                    ? _buildErrorState()
                    : _buildMainContent(config),

            // Confetti overlay
            if (_showConfetti)
              Positioned.fill(
                child: IgnorePointer(
                  child: _ConfettiOverlay(
                    controller: _confettiAnimController,
                    particles: _confettiParticles,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildLoadingState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(color: joviCoral),
          SizedBox(height: 16),
          Text(
            'Loading your membership…',
            style: TextStyle(color: kTextMedium, fontSize: 16),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 64, color: kErrorRed),
            const SizedBox(height: 16),
            Text(
              _errorMessage ?? 'Something went wrong.',
              textAlign: TextAlign.center,
              style: const TextStyle(color: kTextMedium, fontSize: 16),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () {
                setState(() {
                  _isLoading = true;
                  _errorMessage = null;
                });
                _initAuth();
              },
              icon: const Icon(Icons.refresh),
              label: const Text('Try Again'),
              style: ElevatedButton.styleFrom(
                backgroundColor: joviCoral,
                foregroundColor: Colors.white,
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMainContent(ResponsiveConfig config) {
    return SafeArea(
      child: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: config.maxWidth),
          child: Column(
            children: [
              // Header
              _buildHeader(config),

              // Step indicator
              if (_currentStep != OnboardingUpdateStep.confirmation)
                _buildStepIndicator(config),

              // Content
              Expanded(
                child: SingleChildScrollView(
                  controller: _scrollController,
                  padding: EdgeInsets.symmetric(
                    horizontal: config.horizontalPadding,
                    vertical: 16,
                  ),
                  child: _buildStepContent(config),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(ResponsiveConfig config) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: config.horizontalPadding,
        vertical: 16,
      ),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        border:
            Border(bottom: BorderSide(color: Colors.white.withOpacity(0.1))),
      ),
      child: Row(
        children: [
          if (_currentStep == OnboardingUpdateStep.review ||
              _currentStep == OnboardingUpdateStep.confirmation)
            IconButton(
              onPressed: () {
                HapticFeedback.lightImpact();
                Navigator.of(context).maybePop();
              },
              icon: const Icon(Icons.arrow_back_ios_new, size: 20),
              color: joviCoral,
              tooltip: 'Back',
            )
          else
            IconButton(
              onPressed: () {
                HapticFeedback.lightImpact();
                _goBack();
              },
              icon: const Icon(Icons.arrow_back_ios_new, size: 20),
              color: joviCoral,
              tooltip: 'Back',
            ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Update Plan',
                  style: TextStyle(
                    fontSize: config.headerFontSize,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.5,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  _stepSubtitle(),
                  style: TextStyle(
                    fontSize: config.fontSize - 1,
                    color: Colors.white.withOpacity(0.6),
                  ),
                ),
              ],
            ),
          ),
          if (_isSaving)
            const SizedBox(
              width: 20,
              height: 20,
              child:
                  CircularProgressIndicator(strokeWidth: 2, color: joviCoral),
            ),
        ],
      ),
    );
  }

  String _stepSubtitle() {
    switch (_currentStep) {
      case OnboardingUpdateStep.review:
        return 'Review and update your plan';
      case OnboardingUpdateStep.editPersonal:
        return 'Edit your personal information';
      case OnboardingUpdateStep.editSpouse:
        return 'Edit spouse details';
      case OnboardingUpdateStep.editDependents:
        return 'Manage dependents';
      case OnboardingUpdateStep.editCoverage:
        return 'Adjust your plan options';
      case OnboardingUpdateStep.editPets:
        return 'Manage your pet plan';
      case OnboardingUpdateStep.quoteSummary:
        return 'Review your updated quote';
      case OnboardingUpdateStep.payment:
        return 'Complete your payment';
      case OnboardingUpdateStep.confirmation:
        return 'Changes confirmed!';
    }
  }

  Widget _buildStepIndicator(ResponsiveConfig config) {
    final totalSteps = OnboardingUpdateStep.values.length - 1;
    final currentIndex = _currentStep.index;

    return Container(
      color: Colors.white.withOpacity(0.03),
      padding: EdgeInsets.symmetric(
        horizontal: config.horizontalPadding,
        vertical: 12,
      ),
      child: Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: currentIndex / (totalSteps - 1),
              backgroundColor: Colors.white.withOpacity(0.1),
              valueColor: const AlwaysStoppedAnimation<Color>(joviCoral),
              minHeight: 4,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Step ${currentIndex + 1} of $totalSteps',
                style: TextStyle(
                    fontSize: config.fontSize - 2,
                    color: Colors.white.withOpacity(0.5)),
              ),
              Text(
                _stepLabel(),
                style: TextStyle(
                  fontSize: config.fontSize - 2,
                  color: joviCoral,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _stepLabel() {
    switch (_currentStep) {
      case OnboardingUpdateStep.review:
        return 'Review';
      case OnboardingUpdateStep.editPersonal:
        return 'Personal';
      case OnboardingUpdateStep.editSpouse:
        return 'Spouse';
      case OnboardingUpdateStep.editDependents:
        return 'Dependents';
      case OnboardingUpdateStep.editCoverage:
        return 'Plan Options';
      case OnboardingUpdateStep.editPets:
        return 'Pet Plan';
      case OnboardingUpdateStep.quoteSummary:
        return 'Quote';
      case OnboardingUpdateStep.payment:
        return 'Payment';
      case OnboardingUpdateStep.confirmation:
        return 'Done';
    }
  }

  // ─── Step Router ──────────────────────────────────────
  Widget _buildStepContent(ResponsiveConfig config) {
    switch (_currentStep) {
      case OnboardingUpdateStep.review:
        return _buildReviewStep(config);
      case OnboardingUpdateStep.editPersonal:
        return _buildPersonalStep(config);
      case OnboardingUpdateStep.editSpouse:
        return _buildSpouseStep(config);
      case OnboardingUpdateStep.editDependents:
        return _buildDependentsStep(config);
      case OnboardingUpdateStep.editCoverage:
        return _buildCoverageStep(config);
      case OnboardingUpdateStep.editPets:
        return _buildPetInsuranceSection(config);
      case OnboardingUpdateStep.quoteSummary:
        return _buildQuoteSummaryStep(config);
      case OnboardingUpdateStep.payment:
        return _buildPaymentStep(config);
      case OnboardingUpdateStep.confirmation:
        return _buildConfirmationStep(config);
    }
  }

  Widget _sectionCard({
    required String title,
    IconData? icon,
    Color? iconColor,
    required Widget child,
    VoidCallback? onEdit,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        // Painted glass: a live blur on every section inside the scroll view
        // was pure GPU cost over an opaque navy background.
        child: RepaintBoundary(
          child: Container(
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.12)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.15),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Section header
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.05),
                    borderRadius:
                        const BorderRadius.vertical(top: Radius.circular(12)),
                  ),
                  child: Row(
                    children: [
                      if (icon != null) ...[
                        Icon(icon, size: 20, color: iconColor ?? joviCoral),
                        const SizedBox(width: 8),
                      ],
                      Expanded(
                        child: Text(
                          title,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                      if (onEdit != null)
                        TextButton.icon(
                          onPressed: onEdit,
                          icon: const Icon(Icons.edit, size: 16),
                          label: const Text('Edit'),
                          style: TextButton.styleFrom(
                            foregroundColor: joviCoral,
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                          ),
                        ),
                    ],
                  ),
                ),
                // Section body
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: child,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ─── Helper: Info Row ─────────────────────────────────
  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: const TextStyle(color: kTextMedium, fontSize: 13),
            ),
          ),
          Expanded(
            child: Text(
              value.isNotEmpty ? value : '—',
              style: const TextStyle(
                  color: kTextDark, fontSize: 13, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  // ─── Helper: Navigation Buttons ───────────────────────
  Widget _buildNavButtons({
    String? backLabel,
    String? nextLabel,
    VoidCallback? onBack,
    VoidCallback? onNext,
    bool isNextLoading = false,
    Color? nextColor,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 24),
      child: Row(
        children: [
          if (onBack != null)
            Expanded(
              child: OutlinedButton(
                onPressed: onBack,
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  side: BorderSide(color: Colors.white.withOpacity(0.2)),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10)),
                ),
                child: Text(
                  backLabel ?? 'Back',
                  style: const TextStyle(color: kTextMedium),
                ),
              ),
            ),
          if (onBack != null && onNext != null) const SizedBox(width: 12),
          if (onNext != null)
            Expanded(
              child: ElevatedButton(
                onPressed: isNextLoading ? null : onNext,
                style: ElevatedButton.styleFrom(
                  backgroundColor: nextColor ?? joviCoral,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10)),
                  elevation: 0,
                ),
                child: isNextLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : Text(
                        nextLabel ?? 'Continue',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
              ),
            ),
        ],
      ),
    );
  }

  // ─── Helper: Form Field ───────────────────────────────
  Widget _buildFormField({
    required TextEditingController controller,
    required String label,
    String? hint,
    TextInputType? keyboardType,
    List<TextInputFormatter>? formatters,
    String? Function(String?)? validator,
    bool obscure = false,
    Widget? suffix,
    int maxLines = 1,
    bool enabled = true,
    VoidCallback? onTap,
    ValueChanged<String>? onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: TextFormField(
        controller: controller,
        cursorColor: joviCoral,
        style: TextStyle(color: Colors.white, fontSize: 14),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: TextStyle(color: Colors.white.withOpacity(0.6)),
          floatingLabelStyle: const TextStyle(color: joviCoral),
          hintText: hint,
          hintStyle: TextStyle(color: Colors.white.withOpacity(0.3)),
          suffixIcon: suffix,
          filled: true,
          fillColor: enabled
              ? Colors.white.withOpacity(0.08)
              : Colors.white.withOpacity(0.04),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: joviCoral, width: 2),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(color: kErrorRed),
          ),
          errorStyle: TextStyle(color: joviCoral.withOpacity(0.9)),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        ),
        keyboardType: keyboardType,
        inputFormatters: formatters,
        validator: validator,
        obscureText: obscure,
        maxLines: maxLines,
        enabled: enabled,
        onTap: onTap,
        onChanged: onChanged,
      ),
    );
  }

  // ============================================================
  // Part 7 of 10: Review Step, Personal Step, Spouse Step
  // ============================================================

  // ═══════════════════════════════════════════════════════
  // REVIEW STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildReviewStep(ResponsiveConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Current plan summary
        _sectionCard(
          title: 'Personal Information',
          icon: Icons.person,
          iconColor: joviNavy,
          onEdit: () => _goToStep(OnboardingUpdateStep.editPersonal),
          child: Column(
            children: [
              _buildAvatarRow(
                photoBytes: _profilePhotoBytes,
                photoUrl: _profilePhotoUrl,
                name: '${_firstNameCtrl.text} ${_lastNameCtrl.text}',
              ),
              const SizedBox(height: 12),
              _infoRow('Email', _emailCtrl.text),
              _infoRow('Phone', _phoneCtrl.text),
              _infoRow('DOB', _dobCtrl.text),
              _infoRow('Gender', _gender),
              _infoRow('Address',
                  '${_addressCtrl.text}, ${_cityCtrl.text}, ${_stateCtrl.text} ${_zipCtrl.text}'),
            ],
          ),
        ),

        // Spouse
        _sectionCard(
          title: _hasSpouse ? 'Spouse' : 'Spouse (None)',
          icon: Icons.people,
          iconColor: joviNavy,
          onEdit: () => _goToStep(OnboardingUpdateStep.editSpouse),
          child: _hasSpouse
              ? Column(
                  children: [
                    _buildAvatarRow(
                      photoBytes: _spousePhotoBytes,
                      photoUrl: _spousePhotoUrl,
                      name:
                          '${_spouseFirstNameCtrl.text} ${_spouseLastNameCtrl.text}',
                    ),
                    const SizedBox(height: 12),
                    _infoRow('DOB', _spouseDobCtrl.text),
                    _infoRow('Gender', _spouseGender),
                  ],
                )
              : const Text(
                  'No spouse on this plan. Tap Edit to add one.',
                  style: TextStyle(color: kTextLight, fontSize: 13),
                ),
        ),

        // Dependents
        _sectionCard(
          title: 'Dependents ($_numDependents)',
          icon: Icons.family_restroom,
          iconColor: joviNavy,
          onEdit: () => _goToStep(OnboardingUpdateStep.editDependents),
          child: _numDependents > 0
              ? Column(
                  children: List.generate(
                      _numDependents,
                      (i) => Padding(
                            padding: EdgeInsets.only(
                                bottom: i < _numDependents - 1 ? 12 : 0),
                            child: Row(
                              children: [
                                _buildSmallAvatar(
                                  photoBytes: _depPhotoBytes[i],
                                  photoUrl: _depPhotoUrls[i],
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '${_depFirstName[i].text} ${_depLastName[i].text}',
                                        style: const TextStyle(
                                            fontWeight: FontWeight.w600,
                                            fontSize: 13.5),
                                      ),
                                      Text(
                                        '${_depRelationship[i]} • ${_depGender[i]} • DOB: ${_depDob[i].text}',
                                        style: const TextStyle(
                                            color: kTextMedium, fontSize: 12),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          )),
                )
              : const Text(
                  'No dependents on this plan. Tap Edit to add.',
                  style: TextStyle(color: kTextLight, fontSize: 13),
                ),
        ),

        // Plan Options
        _sectionCard(
          title: 'Plan Options',
          icon: Icons.health_and_safety,
          iconColor: joviMint,
          onEdit: () => _goToStep(OnboardingUpdateStep.editCoverage),
          child: Column(
            children: [
              _infoRow('Plan Tier', _planTier),
              _infoRow('Dental Plan', _hasDental ? 'Yes (+\$35/mo)' : 'No'),
              _infoRow('Vision Plan', _hasVision ? 'Yes (+\$15/mo)' : 'No'),
              _infoRow('Tobacco (You)', _hasTobacco ? 'Yes (+15%)' : 'No'),
              if (_hasSpouse)
                _infoRow('Tobacco (Spouse)',
                    _spouseHasTobacco ? 'Yes (+15%)' : 'No'),
              _infoRow('Your Responsibility',
                  '\$${_healthDeductible.toStringAsFixed(0)}'),
            ],
          ),
        ),

        // Pet Plan
        _sectionCard(
          title: 'Pet Plan ($_numPets pet${_numPets == 1 ? "" : "s"})',
          icon: Icons.pets,
          iconColor: joviCoral,
          onEdit: () => _goToStep(OnboardingUpdateStep.editPets),
          child: _numPets > 0
              ? Column(
                  children: List.generate(
                      _numPets,
                      (i) => Padding(
                            padding: EdgeInsets.only(
                                bottom: i < _numPets - 1 ? 12 : 0),
                            child: Row(
                              children: [
                                _buildPetSmallAvatar(i),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        _petName[i].text.isNotEmpty
                                            ? _petName[i].text
                                            : 'Pet ${i + 1}',
                                        style: const TextStyle(
                                            fontWeight: FontWeight.w600,
                                            fontSize: 13.5),
                                      ),
                                      Text(
                                        '${_petType[i]} • ${_petBreed[i].isNotEmpty ? _petBreed[i] : "No breed"} • ${_petAge[i].text.isNotEmpty ? _petAge[i].text : "Age N/A"}',
                                        style: const TextStyle(
                                            color: kTextMedium, fontSize: 12),
                                      ),
                                    ],
                                  ),
                                ),
                                Text(
                                  '\$${(_petQuotes.length > i ? _petQuotes[i]['premium'] : 60.0).toStringAsFixed(0)}/mo',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: joviCoral,
                                    fontSize: 13,
                                  ),
                                ),
                              ],
                            ),
                          )),
                )
              : const Text(
                  'No pet plan. Tap Edit to add a plan for your pets.',
                  style: TextStyle(color: kTextLight, fontSize: 13),
                ),
        ),

        // Quick quote preview (navy gradient)
        if (_quoteReady)
          Container(
            padding: const EdgeInsets.all(16),
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [joviNavy, joviNavyDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.25),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Estimated Monthly Total',
                      style: TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Health Plan + Pet Plan',
                      style: TextStyle(color: Colors.white54, fontSize: 11),
                    ),
                  ],
                ),
                Text(
                  '\$${_grandTotal.toStringAsFixed(2)}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),

        // Action buttons
        _buildNavButtons(
          nextLabel: 'Review & Update Quote',
          onNext: () {
            _computeQuote();
            _goToStep(OnboardingUpdateStep.quoteSummary);
          },
        ),
      ],
    );
  }

  // ─── Avatar Helpers ───────────────────────────────────
  Widget _buildAvatarRow({
    Uint8List? photoBytes,
    String photoUrl = '',
    required String name,
  }) {
    return Row(
      children: [
        CircleAvatar(
          radius: 28,
          backgroundColor: kSurfaceGrey,
          backgroundImage: photoBytes != null
              ? MemoryImage(photoBytes)
              : (photoUrl.isNotEmpty ? NetworkImage(photoUrl) : null)
                  as ImageProvider?,
          child: (photoBytes == null && photoUrl.isEmpty)
              ? const Icon(Icons.person, color: kTextLight, size: 28)
              : null,
        ),
        const SizedBox(width: 12),
        Text(
          name,
          style: const TextStyle(
              fontSize: 16, fontWeight: FontWeight.bold, color: kTextDark),
        ),
      ],
    );
  }

  Widget _buildSmallAvatar({Uint8List? photoBytes, String photoUrl = ''}) {
    return CircleAvatar(
      radius: 18,
      backgroundColor: kSurfaceGrey,
      backgroundImage: photoBytes != null
          ? MemoryImage(photoBytes)
          : (photoUrl.isNotEmpty ? NetworkImage(photoUrl) : null)
              as ImageProvider?,
      child: (photoBytes == null && photoUrl.isEmpty)
          ? const Icon(Icons.person, color: kTextLight, size: 18)
          : null,
    );
  }

  Widget _buildPetSmallAvatar(int petIndex) {
    final bytes =
        _petPhotoBytes.length > petIndex ? _petPhotoBytes[petIndex] : null;
    final url = _petPhotoUrls.length > petIndex ? _petPhotoUrls[petIndex] : '';
    return CircleAvatar(
      radius: 18,
      backgroundColor: kPetPurpleLight,
      backgroundImage: bytes != null
          ? MemoryImage(bytes)
          : (url.isNotEmpty ? NetworkImage(url) : null) as ImageProvider?,
      child: (bytes == null && url.isEmpty)
          ? const Icon(Icons.pets, color: joviCoral, size: 18)
          : null,
    );
  }

  // ═══════════════════════════════════════════════════════
  // PERSONAL INFO STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildPersonalStep(ResponsiveConfig config) {
    return Form(
      key: _personalFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Photo
          Center(
            child: _Pressable(
              onTap: _pickProfilePhoto,
              child: Stack(
                children: [
                  CircleAvatar(
                    radius: config.avatarRadius,
                    backgroundColor: kSurfaceGrey,
                    backgroundImage: _profilePhotoBytes != null
                        ? MemoryImage(_profilePhotoBytes!)
                        : (_profilePhotoUrl.isNotEmpty
                            ? NetworkImage(_profilePhotoUrl)
                            : null) as ImageProvider?,
                    child:
                        (_profilePhotoBytes == null && _profilePhotoUrl.isEmpty)
                            ? Icon(Icons.person,
                                size: config.avatarRadius, color: kTextLight)
                            : null,
                  ),
                  Positioned(
                    bottom: 0,
                    right: 0,
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: const BoxDecoration(
                        color: joviCoral,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.camera_alt,
                          size: 16, color: Colors.white),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Name row
          if (config.columnsPerRow >= 2)
            Row(
              children: [
                Expanded(
                    child: _buildFormField(
                  controller: _firstNameCtrl,
                  label: 'First Name',
                  validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
                )),
                SizedBox(width: config.fieldSpacing),
                Expanded(
                    child: _buildFormField(
                  controller: _lastNameCtrl,
                  label: 'Last Name',
                  validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
                )),
              ],
            )
          else ...[
            _buildFormField(
              controller: _firstNameCtrl,
              label: 'First Name',
              validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
            ),
            _buildFormField(
              controller: _lastNameCtrl,
              label: 'Last Name',
              validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
            ),
          ],

          _buildFormField(
            controller: _emailCtrl,
            label: 'Email',
            keyboardType: TextInputType.emailAddress,
            validator: (v) {
              if (v?.isEmpty ?? true) return 'Required';
              if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$').hasMatch(v!)) {
                return 'Invalid email';
              }
              return null;
            },
          ),

          _buildFormField(
            controller: _phoneCtrl,
            label: 'Phone',
            keyboardType: TextInputType.phone,
          ),

          // DOB & Gender
          if (config.columnsPerRow >= 2)
            Row(
              children: [
                Expanded(
                    child: _buildFormField(
                  controller: _dobCtrl,
                  label: 'Date of Birth',
                  hint: 'MM/DD/YYYY',
                  suffix: IconButton(
                    icon: const Icon(Icons.calendar_today,
                        size: 18, color: joviCoral),
                    onPressed: () => _pickDate(_dobCtrl),
                  ),
                )),
                SizedBox(width: config.fieldSpacing),
                Expanded(
                    child: _buildGenderDropdown(
                        _gender, (v) => setState(() => _gender = v!))),
              ],
            )
          else ...[
            _buildFormField(
              controller: _dobCtrl,
              label: 'Date of Birth',
              hint: 'MM/DD/YYYY',
              suffix: IconButton(
                icon: const Icon(Icons.calendar_today,
                    size: 18, color: joviCoral),
                onPressed: () => _pickDate(_dobCtrl),
              ),
            ),
            _buildGenderDropdown(_gender, (v) => setState(() => _gender = v!)),
          ],

          _buildFormField(
            controller: _ssnCtrl,
            label: 'SSN (Last 4)',
            keyboardType: TextInputType.number,
            formatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(4),
            ],
            obscure: true,
          ),

          _buildFormField(controller: _addressCtrl, label: 'Street Address'),

          if (config.columnsPerRow >= 3)
            Row(
              children: [
                Expanded(
                    flex: 3,
                    child:
                        _buildFormField(controller: _cityCtrl, label: 'City')),
                SizedBox(width: config.fieldSpacing),
                Expanded(
                    flex: 2,
                    child: _buildFormField(
                        controller: _stateCtrl, label: 'State')),
                SizedBox(width: config.fieldSpacing),
                Expanded(
                    flex: 2,
                    child: _buildFormField(
                      controller: _zipCtrl,
                      label: 'ZIP',
                      keyboardType: TextInputType.number,
                      formatters: [
                        FilteringTextInputFormatter.digitsOnly,
                        LengthLimitingTextInputFormatter(5),
                      ],
                    )),
              ],
            )
          else ...[
            _buildFormField(controller: _cityCtrl, label: 'City'),
            Row(
              children: [
                Expanded(
                    child: _buildFormField(
                        controller: _stateCtrl, label: 'State')),
                SizedBox(width: config.fieldSpacing),
                Expanded(
                    child: _buildFormField(
                  controller: _zipCtrl,
                  label: 'ZIP',
                  keyboardType: TextInputType.number,
                  formatters: [
                    FilteringTextInputFormatter.digitsOnly,
                    LengthLimitingTextInputFormatter(5),
                  ],
                )),
              ],
            ),
          ],

          _buildNavButtons(
            onBack: _goBack,
            onNext: () {
              if (_personalFormKey.currentState?.validate() ?? false) {
                _goNext();
              }
            },
          ),
        ],
      ),
    );
  }

  Widget _buildGenderDropdown(String value, ValueChanged<String?> onChanged) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: DropdownButtonFormField<String>(
        value: value,
        decoration: InputDecoration(
          labelText: 'Gender',
          labelStyle: const TextStyle(color: kTextMedium),
          floatingLabelStyle: const TextStyle(color: joviCoral),
          filled: true,
          fillColor: Colors.white.withOpacity(0.08),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: kBorderGrey),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: kBorderGrey),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: joviCoral, width: 2),
          ),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        ),
        items: const [
          DropdownMenuItem(value: 'Male', child: Text('Male')),
          DropdownMenuItem(value: 'Female', child: Text('Female')),
          DropdownMenuItem(value: 'Other', child: Text('Other')),
        ],
        onChanged: onChanged,
      ),
    );
  }

  // ═══════════════════════════════════════════════════════
  // SPOUSE STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildSpouseStep(ResponsiveConfig config) {
    return Form(
      key: _spouseFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Toggle
          SwitchListTile(
            title: const Text('Include Spouse',
                style: TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text(
              _hasSpouse
                  ? 'Spouse included in plan'
                  : 'Add a spouse to your plan',
              style: const TextStyle(color: kTextMedium, fontSize: 13),
            ),
            value: _hasSpouse,
            activeColor: joviCoral,
            contentPadding: EdgeInsets.zero,
            onChanged: (v) {
              setState(() => _hasSpouse = v);
              _computeQuote();
            },
          ),
          const SizedBox(height: 16),

          if (_hasSpouse) ...[
            // Photo
            Center(
              child: _Pressable(
                onTap: _pickSpousePhoto,
                child: Stack(
                  children: [
                    CircleAvatar(
                      radius: 36,
                      backgroundColor: kSurfaceGrey,
                      backgroundImage: _spousePhotoBytes != null
                          ? MemoryImage(_spousePhotoBytes!)
                          : (_spousePhotoUrl.isNotEmpty
                              ? NetworkImage(_spousePhotoUrl)
                              : null) as ImageProvider?,
                      child:
                          (_spousePhotoBytes == null && _spousePhotoUrl.isEmpty)
                              ? const Icon(Icons.person,
                                  size: 36, color: kTextLight)
                              : null,
                    ),
                    Positioned(
                      bottom: 0,
                      right: 0,
                      child: Container(
                        padding: const EdgeInsets.all(4),
                        decoration: const BoxDecoration(
                            color: joviCoral, shape: BoxShape.circle),
                        child: const Icon(Icons.camera_alt,
                            size: 14, color: Colors.white),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            if (config.columnsPerRow >= 2)
              Row(
                children: [
                  Expanded(
                      child: _buildFormField(
                    controller: _spouseFirstNameCtrl,
                    label: 'First Name',
                    validator: (v) =>
                        _hasSpouse && (v?.isEmpty ?? true) ? 'Required' : null,
                  )),
                  SizedBox(width: config.fieldSpacing),
                  Expanded(
                      child: _buildFormField(
                    controller: _spouseLastNameCtrl,
                    label: 'Last Name',
                    validator: (v) =>
                        _hasSpouse && (v?.isEmpty ?? true) ? 'Required' : null,
                  )),
                ],
              )
            else ...[
              _buildFormField(
                controller: _spouseFirstNameCtrl,
                label: 'First Name',
                validator: (v) =>
                    _hasSpouse && (v?.isEmpty ?? true) ? 'Required' : null,
              ),
              _buildFormField(
                controller: _spouseLastNameCtrl,
                label: 'Last Name',
                validator: (v) =>
                    _hasSpouse && (v?.isEmpty ?? true) ? 'Required' : null,
              ),
            ],

            if (config.columnsPerRow >= 2)
              Row(
                children: [
                  Expanded(
                      child: _buildFormField(
                    controller: _spouseDobCtrl,
                    label: 'Date of Birth',
                    hint: 'MM/DD/YYYY',
                    suffix: IconButton(
                      icon: const Icon(Icons.calendar_today,
                          size: 18, color: joviCoral),
                      onPressed: () => _pickDate(_spouseDobCtrl),
                    ),
                  )),
                  SizedBox(width: config.fieldSpacing),
                  Expanded(
                      child: _buildGenderDropdown(
                    _spouseGender,
                    (v) => setState(() => _spouseGender = v!),
                  )),
                ],
              )
            else ...[
              _buildFormField(
                controller: _spouseDobCtrl,
                label: 'Date of Birth',
                hint: 'MM/DD/YYYY',
                suffix: IconButton(
                  icon: const Icon(Icons.calendar_today,
                      size: 18, color: joviCoral),
                  onPressed: () => _pickDate(_spouseDobCtrl),
                ),
              ),
              _buildGenderDropdown(
                _spouseGender,
                (v) => setState(() => _spouseGender = v!),
              ),
            ],

            _buildFormField(
              controller: _spouseSsnCtrl,
              label: 'SSN (Last 4)',
              keyboardType: TextInputType.number,
              formatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(4),
              ],
              obscure: true,
            ),
          ],

          _buildNavButtons(
            onBack: _goBack,
            onNext: () {
              if (!_hasSpouse ||
                  (_spouseFormKey.currentState?.validate() ?? false)) {
                _computeQuote();
                _goNext();
              }
            },
          ),
        ],
      ),
    );
  }

  // ============================================================
  // Part 8 of 10: Dependents Step & Plan Options Step
  // ============================================================

  // ═══════════════════════════════════════════════════════
  // DEPENDENTS STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildDependentsStep(ResponsiveConfig config) {
    return Form(
      key: _dependentFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header + Add button
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Dependents ($_numDependents)',
                style: const TextStyle(
                    fontSize: 17,
                    fontWeight: FontWeight.bold,
                    color: kTextDark),
              ),
              TextButton.icon(
                onPressed: () {
                  _addDependentSlot();
                  setState(() => _numDependents++);
                },
                icon: const Icon(Icons.add_circle_outline, size: 20),
                label: const Text('Add Dependent'),
                style: TextButton.styleFrom(foregroundColor: joviCoral),
              ),
            ],
          ),
          const SizedBox(height: 12),

          if (_numDependents == 0)
            Container(
              padding: const EdgeInsets.all(32),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withOpacity(0.1)),
              ),
              child: const Center(
                child: Column(
                  children: [
                    Icon(Icons.family_restroom, size: 48, color: kTextLight),
                    SizedBox(height: 12),
                    Text(
                      'No dependents added yet',
                      style: TextStyle(color: kTextMedium, fontSize: 14),
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Tap "Add Dependent" to include children or other dependents.',
                      style: TextStyle(color: kTextLight, fontSize: 12),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),

          // Dependent cards
          ...List.generate(
              _numDependents, (i) => _buildDependentCard(i, config)),

          _buildNavButtons(
            onBack: _goBack,
            onNext: () {
              if (_dependentFormKey.currentState?.validate() ?? false) {
                _computeQuote();
                _goNext();
              }
            },
          ),
        ],
      ),
    );
  }

  Widget _buildDependentCard(int index, ResponsiveConfig config) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Card header
          Row(
            children: [
              _Pressable(
                onTap: () => _pickDependentPhoto(index),
                child: Stack(
                  children: [
                    CircleAvatar(
                      radius: 22,
                      backgroundColor: kSurfaceGrey,
                      backgroundImage: _depPhotoBytes[index] != null
                          ? MemoryImage(_depPhotoBytes[index]!)
                          : (_depPhotoUrls[index].isNotEmpty
                              ? NetworkImage(_depPhotoUrls[index])
                              : null) as ImageProvider?,
                      child: (_depPhotoBytes[index] == null &&
                              _depPhotoUrls[index].isEmpty)
                          ? const Icon(Icons.person,
                              size: 22, color: kTextLight)
                          : null,
                    ),
                    Positioned(
                      bottom: -2,
                      right: -2,
                      child: Container(
                        padding: const EdgeInsets.all(3),
                        decoration: const BoxDecoration(
                            color: joviCoral, shape: BoxShape.circle),
                        child: const Icon(Icons.camera_alt,
                            size: 10, color: Colors.white),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _depFirstName[index].text.isNotEmpty
                      ? '${_depFirstName[index].text} ${_depLastName[index].text}'
                      : 'Dependent ${index + 1}',
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 15),
                ),
              ),
              IconButton(
                onPressed: () async {
                  final confirm = await _showConfirmDialog(
                    'Remove Dependent',
                    'Remove ${_depFirstName[index].text.isNotEmpty ? _depFirstName[index].text : "this dependent"}?',
                  );
                  if (confirm) _removeDependent(index);
                },
                icon: const Icon(Icons.delete_outline,
                    color: kErrorRed, size: 20),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Fields
          if (config.columnsPerRow >= 2)
            Row(
              children: [
                Expanded(
                    child: _buildFormField(
                  controller: _depFirstName[index],
                  label: 'First Name',
                  validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
                )),
                SizedBox(width: config.fieldSpacing),
                Expanded(
                    child: _buildFormField(
                  controller: _depLastName[index],
                  label: 'Last Name',
                  validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
                )),
              ],
            )
          else ...[
            _buildFormField(
              controller: _depFirstName[index],
              label: 'First Name',
              validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
            ),
            _buildFormField(
              controller: _depLastName[index],
              label: 'Last Name',
              validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
            ),
          ],

          if (config.columnsPerRow >= 2)
            Row(
              children: [
                Expanded(
                    child: _buildFormField(
                  controller: _depDob[index],
                  label: 'Date of Birth',
                  hint: 'MM/DD/YYYY',
                  suffix: IconButton(
                    icon: const Icon(Icons.calendar_today,
                        size: 18, color: joviCoral),
                    onPressed: () => _pickDate(_depDob[index]),
                  ),
                )),
                SizedBox(width: config.fieldSpacing),
                Expanded(
                  child: _buildRelationshipDropdown(
                    _depRelationship[index],
                    (v) => setState(() => _depRelationship[index] = v!),
                  ),
                ),
              ],
            )
          else ...[
            _buildFormField(
              controller: _depDob[index],
              label: 'Date of Birth',
              hint: 'MM/DD/YYYY',
              suffix: IconButton(
                icon: const Icon(Icons.calendar_today,
                    size: 18, color: joviCoral),
                onPressed: () => _pickDate(_depDob[index]),
              ),
            ),
            _buildRelationshipDropdown(
              _depRelationship[index],
              (v) => setState(() => _depRelationship[index] = v!),
            ),
          ],

          _buildGenderDropdown(
            _depGender[index],
            (v) => setState(() => _depGender[index] = v!),
          ),

          _buildFormField(
            controller: _depSsn[index],
            label: 'SSN (Last 4)',
            keyboardType: TextInputType.number,
            formatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(4),
            ],
            obscure: true,
          ),
        ],
      ),
    );
  }

  Widget _buildRelationshipDropdown(
      String value, ValueChanged<String?> onChanged) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: DropdownButtonFormField<String>(
        value: value,
        decoration: InputDecoration(
          labelText: 'Relationship',
          labelStyle: const TextStyle(color: kTextMedium),
          floatingLabelStyle: const TextStyle(color: joviCoral),
          filled: true,
          fillColor: Colors.white.withOpacity(0.08),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: kBorderGrey),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: kBorderGrey),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: joviCoral, width: 2),
          ),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        ),
        items: const [
          DropdownMenuItem(value: 'Child', child: Text('Child')),
          DropdownMenuItem(value: 'Stepchild', child: Text('Stepchild')),
          DropdownMenuItem(value: 'Foster Child', child: Text('Foster Child')),
          DropdownMenuItem(
              value: 'Domestic Partner', child: Text('Domestic Partner')),
          DropdownMenuItem(value: 'Other', child: Text('Other')),
        ],
        onChanged: onChanged,
      ),
    );
  }

  // ═══════════════════════════════════════════════════════
  // PLAN OPTIONS STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildCoverageStep(ResponsiveConfig config) {
    return Form(
      key: _coverageFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Plan Options',
            style: TextStyle(
                fontSize: 17, fontWeight: FontWeight.bold, color: kTextDark),
          ),
          const SizedBox(height: 16),

          // Plan Tier
          _sectionCard(
            title: 'Plan Tier',
            icon: Icons.shield,
            iconColor: joviNavy,
            child: Column(
              children: [
                _buildTierOption('Individual', 'Just you', Icons.person),
                _buildTierOption('Couple', 'You and your spouse', Icons.people),
                _buildTierOption('Family', 'You, spouse, and dependents',
                    Icons.family_restroom),
              ],
            ),
          ),

          // Add-ons
          _sectionCard(
            title: 'Add-on Plans',
            icon: Icons.add_circle_outline,
            iconColor: joviMint,
            child: Column(
              children: [
                _buildCoverageToggle(
                  'Dental Plan',
                  '+\$35/month per person',
                  Icons.medical_services,
                  _hasDental,
                  (v) => setState(() {
                    _hasDental = v;
                    _computeQuote();
                  }),
                ),
                const Divider(height: 1),
                _buildCoverageToggle(
                  'Vision Plan',
                  '+\$15/month per person',
                  Icons.visibility,
                  _hasVision,
                  (v) => setState(() {
                    _hasVision = v;
                    _computeQuote();
                  }),
                ),
              ],
            ),
          ),

          // Tobacco
          _sectionCard(
            title: 'Tobacco Use',
            icon: Icons.smoking_rooms,
            iconColor: joviGold,
            child: Column(
              children: [
                _buildCoverageToggle(
                  'You use tobacco',
                  '+15% premium surcharge',
                  Icons.person,
                  _hasTobacco,
                  (v) => setState(() {
                    _hasTobacco = v;
                    _computeQuote();
                  }),
                ),
                if (_hasSpouse) ...[
                  const Divider(height: 1),
                  _buildCoverageToggle(
                    'Spouse uses tobacco',
                    '+15% premium surcharge',
                    Icons.people,
                    _spouseHasTobacco,
                    (v) => setState(() {
                      _spouseHasTobacco = v;
                      _computeQuote();
                    }),
                  ),
                ],
              ],
            ),
          ),

          // Your Responsibility
          _sectionCard(
            title: 'Your Responsibility',
            icon: Icons.attach_money,
            iconColor: joviCoral,
            child: Column(
              children: [
                Text(
                  '\$${_healthDeductible.toStringAsFixed(0)}',
                  style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: joviCoral),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Annual amount you pay before community sharing kicks in',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: kTextMedium, fontSize: 12),
                ),
                const SizedBox(height: 8),
                Slider(
                  value: _healthDeductible,
                  min: 500,
                  max: 5000,
                  divisions: 9,
                  activeColor: joviCoral,
                  inactiveColor: joviCoral.withOpacity(0.2),
                  label: '\$${_healthDeductible.toStringAsFixed(0)}',
                  onChanged: (v) => setState(() => _healthDeductible = v),
                ),
                const Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('\$500',
                        style: TextStyle(color: kTextLight, fontSize: 12)),
                    Text('\$5,000',
                        style: TextStyle(color: kTextLight, fontSize: 12)),
                  ],
                ),
              ],
            ),
          ),

          _buildNavButtons(
            onBack: _goBack,
            onNext: () {
              _computeQuote();
              _goNext();
            },
          ),
        ],
      ),
    );
  }

  Widget _buildTierOption(String tier, String desc, IconData icon) {
    final selected = _planTier == tier;
    return _Pressable(
      onTap: () {
        HapticFeedback.selectionClick();
        setState(() => _planTier = tier);
        _computeQuote();
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: selected
              ? joviCoral.withOpacity(0.12)
              : Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: selected ? joviCoral : kBorderGrey,
            width: selected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, color: selected ? joviCoral : kTextLight, size: 22),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    tier,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                      color: selected ? joviCoral : kTextDark,
                    ),
                  ),
                  Text(desc,
                      style: const TextStyle(color: kTextMedium, fontSize: 12)),
                ],
              ),
            ),
            if (selected)
              const Icon(Icons.check_circle, color: joviCoral, size: 22),
          ],
        ),
      ),
    );
  }

  Widget _buildCoverageToggle(
    String title,
    String subtitle,
    IconData icon,
    bool value,
    ValueChanged<bool> onChanged,
  ) {
    return SwitchListTile(
      title: Text(title,
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
      subtitle: Text(subtitle,
          style: const TextStyle(color: kTextMedium, fontSize: 12)),
      secondary: Icon(icon, color: value ? joviCoral : kTextLight),
      value: value,
      activeColor: joviCoral,
      contentPadding: const EdgeInsets.symmetric(horizontal: 4),
      onChanged: (v) => onChanged(v),
    );
  }

  // ============================================================
  // Part 9 of 10: Pet Plan Section, Quote Summary, Promo
  // ============================================================

  // ═══════════════════════════════════════════════════════
  // PET PLAN STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildPetInsuranceSection(ResponsiveConfig config) {
    return Form(
      key: _petFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: kPetPurpleLight,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.pets, color: joviCoral, size: 24),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Pet Plan',
                      style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: kTextDark),
                    ),
                    SizedBox(height: 2),
                    Text(
                      '90% reimbursement • \$500 out-of-pocket',
                      style: TextStyle(color: kTextMedium, fontSize: 12),
                    ),
                  ],
                ),
              ),
              TextButton(
                onPressed: _showPetCoverageDialog,
                style: TextButton.styleFrom(foregroundColor: joviCoral),
                child:
                    const Text('Plan Details', style: TextStyle(fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Pet count dropdown
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.08),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: kBorderGrey),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<int>(
                value: _numPets,
                isExpanded: true,
                icon: const Icon(Icons.keyboard_arrow_down, color: joviCoral),
                items: List.generate(
                    6,
                    (i) => DropdownMenuItem(
                          value: i,
                          child: Text(
                            i == 0 ? 'No pets' : '$i pet${i > 1 ? "s" : ""}',
                            style: const TextStyle(fontSize: 14),
                          ),
                        )),
                onChanged: (v) {
                  if (v == null) return;
                  final oldCount = _numPets;
                  if (v > oldCount) {
                    for (int i = oldCount; i < v; i++) {
                      _addPetSlot();
                    }
                  } else if (v < oldCount) {
                    for (int i = oldCount - 1; i >= v; i--) {
                      _removePet(i);
                    }
                  }
                  setState(() => _numPets = v);
                  _computePetQuotes();
                  _computeQuote();
                },
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Empty state
          if (_numPets == 0) _buildPetEmptyState(),

          // Pet cards
          ...List.generate(_numPets, (i) => _buildAnimatedPetCard(i, config)),

          // Total pet premium
          if (_numPets > 0)
            Container(
              padding: const EdgeInsets.all(14),
              margin: const EdgeInsets.only(top: 8, bottom: 8),
              decoration: BoxDecoration(
                color: kPetPurpleLight,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: joviCoral.withOpacity(0.3)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.pets, color: joviCoral, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Total Pet Plan',
                        style: TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 14,
                            color: joviCoral),
                      ),
                    ],
                  ),
                  Text(
                    '\$${_petTotalPremium.toStringAsFixed(2)}/mo',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: joviCoral,
                    ),
                  ),
                ],
              ),
            ),

          _buildNavButtons(
            onBack: _goBack,
            onNext: () {
              _computeQuote();
              _goNext();
            },
          ),
        ],
      ),
    );
  }

  // ─── Pet Empty State ──────────────────────────────────
  Widget _buildPetEmptyState() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 40, horizontal: 24),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Center(
        child: Column(
          children: [
            // Paw print illustration
            Container(
              width: 80,
              height: 80,
              decoration: const BoxDecoration(
                color: kPetPurpleLight,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.pets, size: 40, color: joviCoral),
            ),
            const SizedBox(height: 16),
            const Text(
              'Protect Your Furry Friends',
              style: TextStyle(
                  fontSize: 16, fontWeight: FontWeight.bold, color: kTextDark),
            ),
            const SizedBox(height: 8),
            const Text(
              'Add a pet plan for comprehensive coverage.\nStarting at \$60/month per pet.',
              textAlign: TextAlign.center,
              style: TextStyle(color: kTextMedium, fontSize: 13, height: 1.4),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: () {
                _addPetSlot();
                setState(() => _numPets = 1);
                _computePetQuotes();
                _computeQuote();
              },
              icon: const Icon(Icons.add, color: joviCoral),
              label: const Text('Add a Pet'),
              style: OutlinedButton.styleFrom(
                foregroundColor: joviCoral,
                side: const BorderSide(color: joviCoral),
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ─── Animated Pet Card Wrapper ────────────────────────
  Widget _buildAnimatedPetCard(int index, ResponsiveConfig config) {
    final anim = _petAnimations.length > index ? _petAnimations[index] : null;
    final animCtrl =
        _petAnimControllers.length > index ? _petAnimControllers[index] : null;

    if (anim == null || animCtrl == null) {
      return _petCardExpanded[index]
          ? _buildPetFullCard(index, config)
          : _buildPetSummaryCard(index, config);
    }

    return FadeTransition(
      opacity: anim,
      child: SizeTransition(
        sizeFactor: anim,
        axisAlignment: -1.0,
        child: _petCardExpanded[index]
            ? _buildPetFullCard(index, config)
            : _buildPetSummaryCard(index, config),
      ),
    );
  }

  // ─── Pet Summary Card (collapsed) ─────────────────────
  Widget _buildPetSummaryCard(int index, ResponsiveConfig config) {
    final name = _petName[index].text.isNotEmpty
        ? _petName[index].text
        : 'Pet ${index + 1}';
    final type = _petType[index];
    final breed = _petBreed[index].isNotEmpty ? _petBreed[index] : 'No breed';
    final age = _petAge[index].text.isNotEmpty ? _petAge[index].text : 'N/A';
    final premium =
        _petQuotes.length > index ? _petQuotes[index]['premium'] : 60.0;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: joviCoral.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          _buildPetAvatarDisplay(index, radius: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name,
                    style: const TextStyle(
                        fontWeight: FontWeight.bold, fontSize: 14)),
                const SizedBox(height: 2),
                Text(
                  '$type • $breed • Age: $age',
                  style: const TextStyle(color: kTextMedium, fontSize: 12),
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '\$${premium.toStringAsFixed(0)}/mo',
                style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: joviCoral,
                    fontSize: 14),
              ),
              const SizedBox(height: 4),
              _Pressable(
                onTap: () => setState(() => _petCardExpanded[index] = true),
                child: const Text(
                  'Edit',
                  style: TextStyle(
                      color: joviCoral,
                      fontSize: 12,
                      fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ─── Pet Full Card (expanded) ─────────────────────────
  Widget _buildPetFullCard(int index, ResponsiveConfig config) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: joviCoral.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.15),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Card header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: kPetPurpleLight,
              borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
            ),
            child: Row(
              children: [
                _buildPetAvatarPicker(index),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    _petName[index].text.isNotEmpty
                        ? _petName[index].text
                        : 'Pet ${index + 1}',
                    style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                        color: kTextDark),
                  ),
                ),
                // Collapse button
                IconButton(
                  onPressed: () {
                    // Only collapse if basic info is filled
                    if (_petName[index].text.isNotEmpty &&
                        _petBreed[index].isNotEmpty) {
                      setState(() => _petCardExpanded[index] = false);
                    }
                  },
                  icon:
                      const Icon(Icons.check_circle, color: joviMint, size: 24),
                  tooltip: 'Done editing',
                ),
                // Delete button
                IconButton(
                  onPressed: () async {
                    final confirm = await _showConfirmDialog(
                      'Remove Pet',
                      'Remove ${_petName[index].text.isNotEmpty ? _petName[index].text : "this pet"}?',
                    );
                    if (confirm) _removePet(index);
                  },
                  icon: const Icon(Icons.delete_outline,
                      color: kErrorRed, size: 20),
                ),
              ],
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Pet Name
                _buildFormField(
                  controller: _petName[index],
                  label: 'Pet Name',
                  hint: 'e.g. Buddy, Luna',
                  onChanged: (_) => _validatePetName(index),
                  validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
                ),
                if (_petNameWarnings[index] != null)
                  _buildWarningText(_petNameWarnings[index]!),

                // Type & Gender row
                if (config.columnsPerRow >= 2)
                  Row(
                    children: [
                      Expanded(child: _buildPetTypeDropdown(index)),
                      SizedBox(width: config.fieldSpacing),
                      Expanded(child: _buildPetGenderDropdown(index)),
                    ],
                  )
                else ...[
                  _buildPetTypeDropdown(index),
                  _buildPetGenderDropdown(index),
                ],

                // Breed (searchable)
                _buildBreedSelector(index),

                // Birthdate & Age row
                if (config.columnsPerRow >= 2)
                  Row(
                    children: [
                      Expanded(
                        child: _buildFormField(
                          controller: _petBirthdate[index],
                          label: 'Birthdate',
                          hint: 'MM/DD/YYYY',
                          suffix: IconButton(
                            icon: const Icon(Icons.calendar_today,
                                size: 18, color: joviCoral),
                            onPressed: () async {
                              await _pickDate(_petBirthdate[index],
                                  isPet: true);
                              _calculateAgeFromBirthdate(index);
                            },
                          ),
                          onChanged: (_) => _calculateAgeFromBirthdate(index),
                        ),
                      ),
                      SizedBox(width: config.fieldSpacing),
                      Expanded(
                        child: _buildFormField(
                          controller: _petAge[index],
                          label: 'Age',
                          hint: 'e.g. 3y, 8m, 2y 6m',
                          onChanged: (_) {
                            _validatePetAge(index);
                            _computePetQuotes();
                            _computeQuote();
                          },
                        ),
                      ),
                    ],
                  )
                else ...[
                  _buildFormField(
                    controller: _petBirthdate[index],
                    label: 'Birthdate',
                    hint: 'MM/DD/YYYY',
                    suffix: IconButton(
                      icon: const Icon(Icons.calendar_today,
                          size: 18, color: joviCoral),
                      onPressed: () async {
                        await _pickDate(_petBirthdate[index], isPet: true);
                        _calculateAgeFromBirthdate(index);
                      },
                    ),
                    onChanged: (_) => _calculateAgeFromBirthdate(index),
                  ),
                  _buildFormField(
                    controller: _petAge[index],
                    label: 'Age',
                    hint: 'e.g. 3y, 8m, 2y 6m',
                    onChanged: (_) {
                      _validatePetAge(index);
                      _computePetQuotes();
                      _computeQuote();
                    },
                  ),
                ],
                if (_petAgeWarnings[index] != null)
                  _buildWarningText(_petAgeWarnings[index]!),

                // Premium display
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 14),
                  decoration: BoxDecoration(
                    color: kPetPurpleLight,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Monthly Contribution',
                        style: TextStyle(
                            fontWeight: FontWeight.w500, fontSize: 13),
                      ),
                      Text(
                        '\$${(_petQuotes.length > index ? _petQuotes[index]['premium'] : 60.0).toStringAsFixed(2)}/mo',
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          color: joviCoral,
                          fontSize: 15,
                        ),
                      ),
                    ],
                  ),
                ),

                // Coverage accordion
                _buildPetCoverageAccordion(index),

                const SizedBox(height: 8),

                // Pre-existing conditions
                _buildPreExistingConditionSection(index),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ─── Pet Avatar Picker ────────────────────────────────
  Widget _buildPetAvatarPicker(int petIndex) {
    return _Pressable(
      onTap: () => _pickPetPhoto(petIndex),
      child: Stack(
        children: [
          _buildPetAvatarDisplay(petIndex, radius: 28),
          Positioned(
            bottom: -2,
            right: -2,
            child: Container(
              padding: const EdgeInsets.all(4),
              decoration:
                  const BoxDecoration(color: joviCoral, shape: BoxShape.circle),
              child:
                  const Icon(Icons.camera_alt, size: 12, color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPetAvatarDisplay(int petIndex, {double radius = 24}) {
    final bytes =
        _petPhotoBytes.length > petIndex ? _petPhotoBytes[petIndex] : null;
    final url = _petPhotoUrls.length > petIndex ? _petPhotoUrls[petIndex] : '';
    return CircleAvatar(
      radius: radius,
      backgroundColor: kPetPurpleLight,
      backgroundImage: bytes != null
          ? MemoryImage(bytes)
          : (url.isNotEmpty ? NetworkImage(url) : null) as ImageProvider?,
      child: (bytes == null && url.isEmpty)
          ? Icon(Icons.pets, color: joviCoral, size: radius)
          : null,
    );
  }

  // ─── Pet Type Dropdown ────────────────────────────────
  Widget _buildPetTypeDropdown(int index) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: DropdownButtonFormField<String>(
        value: _petType[index],
        decoration: InputDecoration(
          labelText: 'Type',
          labelStyle: const TextStyle(color: kTextMedium),
          floatingLabelStyle: const TextStyle(color: joviCoral),
          filled: true,
          fillColor: Colors.white.withOpacity(0.08),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: kBorderGrey),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: kBorderGrey),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: joviCoral, width: 2),
          ),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        ),
        items: const [
          DropdownMenuItem(value: 'Dog', child: Text('🐕 Dog')),
          DropdownMenuItem(value: 'Cat', child: Text('🐈 Cat')),
        ],
        onChanged: (v) {
          setState(() {
            _petType[index] = v!;
            _petBreed[index] = ''; // Reset breed on type change
          });
        },
      ),
    );
  }

  // ─── Pet Gender Dropdown ──────────────────────────────
  Widget _buildPetGenderDropdown(int index) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: DropdownButtonFormField<String>(
        value: _petGender[index],
        decoration: InputDecoration(
          labelText: 'Gender',
          labelStyle: const TextStyle(color: kTextMedium),
          floatingLabelStyle: const TextStyle(color: joviCoral),
          filled: true,
          fillColor: Colors.white.withOpacity(0.08),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: kBorderGrey),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: kBorderGrey),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: joviCoral, width: 2),
          ),
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        ),
        items: const [
          DropdownMenuItem(value: 'Male', child: Text('Male')),
          DropdownMenuItem(value: 'Female', child: Text('Female')),
        ],
        onChanged: (v) => setState(() => _petGender[index] = v!),
      ),
    );
  }

  // ─── Breed Selector (taps to open searchable dialog) ──
  Widget _buildBreedSelector(int index) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: _Pressable(
        onTap: () async {
          final breed = await _showSearchableBreedDropdown(_petType[index]);
          if (breed != null) {
            setState(() => _petBreed[index] = breed);
            _validatePetAge(index);
          }
        },
        child: InputDecorator(
          decoration: InputDecoration(
            labelText: 'Breed',
            labelStyle: const TextStyle(color: kTextMedium),
            filled: true,
            fillColor: Colors.white.withOpacity(0.08),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: kBorderGrey),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: kBorderGrey),
            ),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            suffixIcon: const Icon(Icons.search, color: joviCoral),
          ),
          child: Text(
            _petBreed[index].isNotEmpty
                ? _petBreed[index]
                : 'Tap to select breed',
            style: TextStyle(
              color: _petBreed[index].isNotEmpty ? kTextDark : kTextLight,
              fontSize: 14,
            ),
          ),
        ),
      ),
    );
  }

  // ─── Coverage Accordion (per pet) ─────────────────────
  Widget _buildPetCoverageAccordion(int index) {
    final expanded = _petCoverageExpanded.length > index
        ? _petCoverageExpanded[index]
        : false;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Column(
        children: [
          _Pressable(
            onTap: () =>
                setState(() => _petCoverageExpanded[index] = !expanded),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: kSurfaceGrey,
                borderRadius: expanded
                    ? const BorderRadius.vertical(top: Radius.circular(8))
                    : BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.health_and_safety,
                      size: 18, color: joviCoral),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      "What's Shared",
                      style: TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                          color: kTextDark),
                    ),
                  ),
                  Icon(
                    expanded
                        ? Icons.keyboard_arrow_up
                        : Icons.keyboard_arrow_down,
                    color: kTextMedium,
                    size: 22,
                  ),
                ],
              ),
            ),
          ),
          if (expanded)
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _coverageCheckItem('Accidents & Injuries'),
                  _coverageCheckItem('Illnesses & Chronic Conditions'),
                  _coverageCheckItem('Surgery & Hospitalization'),
                  _coverageCheckItem('Prescriptions'),
                  _coverageCheckItem('Diagnostic Tests (X-rays, MRI, etc.)'),
                  _coverageCheckItem('Emergency & Urgent Care'),
                  _coverageCheckItem('Specialist Referrals'),
                  _coverageCheckItem('Behavioral Therapy'),
                  const Divider(height: 16),
                  _coverageStat('Reimbursement', '90%'),
                  _coverageStat('Your Responsibility', '\$500'),
                  _coverageStat('Annual Limit', 'Unlimited'),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _coverageCheckItem(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          const Icon(Icons.check_circle, size: 16, color: joviMint),
          const SizedBox(width: 8),
          Expanded(
              child: Text(text,
                  style: const TextStyle(fontSize: 12.5, color: kTextDark))),
        ],
      ),
    );
  }

  // ─── Pre-existing Conditions (per pet) ────────────────
  Widget _buildPreExistingConditionSection(int index) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: kSurfaceGrey,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withOpacity(0.12)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: CheckboxListTile(
                  title: const Text(
                    'My pet has pre-existing conditions',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                  ),
                  subtitle: const Text(
                    'Pre-existing conditions are not shared but must be disclosed.',
                    style: TextStyle(fontSize: 11, color: kTextMedium),
                  ),
                  value: _petPreExistingAck[index],
                  activeColor: joviCoral,
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  onChanged: (v) =>
                      setState(() => _petPreExistingAck[index] = v ?? false),
                ),
              ),
            ],
          ),
          if (_petPreExistingAck[index]) ...[
            const SizedBox(height: 8),
            _buildFormField(
              controller: _petPreExistingControllers[index],
              label: 'Describe conditions',
              hint: 'e.g. Hip dysplasia, allergies…',
              maxLines: 2,
            ),
          ],
        ],
      ),
    );
  }

  // ─── Warning Text Helper ──────────────────────────────
  Widget _buildWarningText(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          const Icon(Icons.warning_amber_rounded, size: 16, color: joviGold),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                  color: Colors.white.withOpacity(0.85), fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════
  // QUOTE SUMMARY STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildQuoteSummaryStep(ResponsiveConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Your Updated Plan',
          style: TextStyle(
              fontSize: 18, fontWeight: FontWeight.bold, color: kTextDark),
        ),
        const SizedBox(height: 16),

        // ── Health Plan Section ──
        _sectionCard(
          title: 'Health Plan',
          icon: Icons.health_and_safety,
          iconColor: joviMint,
          child: Column(
            children: [
              // Primary member
              _quoteLine(
                '${_firstNameCtrl.text} ${_lastNameCtrl.text} (You)',
                _primaryPremium,
                details: [
                  'Base: \$250.00',
                  if (_hasTobacco) 'Tobacco surcharge: +15%',
                  if (_hasDental) 'Dental: +\$35.00',
                  if (_hasVision) 'Vision: +\$15.00',
                ],
              ),

              // Spouse
              if (_hasSpouse) ...[
                const Divider(height: 16),
                _quoteLine(
                  '${_spouseFirstNameCtrl.text} ${_spouseLastNameCtrl.text} (Spouse)',
                  _spousePremium,
                  details: [
                    'Base: \$250.00',
                    if (_spouseHasTobacco) 'Tobacco surcharge: +15%',
                    if (_hasDental) 'Dental: +\$35.00',
                    if (_hasVision) 'Vision: +\$15.00',
                  ],
                ),
              ],

              // Dependents
              ...List.generate(_numDependents, (i) {
                double depPrem = 250.0 * 0.6;
                if (_hasDental) depPrem += 25.0;
                if (_hasVision) depPrem += 10.0;
                return Column(
                  children: [
                    const Divider(height: 16),
                    _quoteLine(
                      '${_depFirstName[i].text} ${_depLastName[i].text} (${_depRelationship[i]})',
                      depPrem,
                      details: [
                        'Base: \$150.00 (dependent rate)',
                        if (_hasDental) 'Dental: +\$25.00',
                        if (_hasVision) 'Vision: +\$10.00',
                      ],
                    ),
                  ],
                );
              }),

              const Divider(height: 20),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Health Subtotal',
                      style:
                          TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                  Text(
                    '\$${_totalHealthPremium.toStringAsFixed(2)}/mo',
                    style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                        color: Colors.white),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'Your Responsibility: \$${_healthDeductible.toStringAsFixed(0)}/year',
                style: const TextStyle(color: kTextMedium, fontSize: 12),
              ),
            ],
          ),
        ),

        // ── Pet Plan Section ──
        if (_numPets > 0)
          _sectionCard(
            title: 'Pet Plan',
            icon: Icons.pets,
            iconColor: joviCoral,
            child: Column(
              children: [
                ...List.generate(_numPets, (i) {
                  final premium = _petQuotes[i]['premium'] as double;
                  return Column(
                    children: [
                      if (i > 0) const Divider(height: 16),
                      _quoteLine(
                        '${_petName[i].text.isNotEmpty ? _petName[i].text : "Pet ${i + 1}"} (${_petType[i]})',
                        premium,
                        details: [
                          '${_petBreed[i].isNotEmpty ? _petBreed[i] : "Unknown breed"} • Age: ${_petAge[i].text.isNotEmpty ? _petAge[i].text : "N/A"}',
                          '90% reimbursement • \$500 out-of-pocket',
                        ],
                        color: joviCoral,
                      ),
                    ],
                  );
                }),
                const Divider(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text('Pet Subtotal',
                        style: TextStyle(
                            fontWeight: FontWeight.bold, fontSize: 14)),
                    Text(
                      '\$${_petTotalPremium.toStringAsFixed(2)}/mo',
                      style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                          color: joviCoral),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Text(
                  'Out-of-Pocket: \$500/year per pet',
                  style: TextStyle(color: kTextMedium, fontSize: 12),
                ),
              ],
            ),
          ),

        // ── Promo Code Section ──
        _buildPromoCodeSection(),

        // ── Discounts ──
        if (_discountAmount > 0 || _hasReferralDiscount)
          _sectionCard(
            title: 'Discounts Applied',
            icon: Icons.local_offer,
            iconColor: joviMint,
            child: Column(
              children: [
                if (_discountAmount > 0)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Promo: $_promoCodeApplied (${_discountPercentage.toStringAsFixed(0)}% off)',
                        style:
                            const TextStyle(color: joviMintDark, fontSize: 13),
                      ),
                      Text(
                        '-\$${_discountAmount.toStringAsFixed(2)}',
                        style: const TextStyle(
                            color: joviMintDark, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                if (_hasReferralDiscount)
                  const Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('Referral Discount',
                          style: TextStyle(color: joviMintDark, fontSize: 13)),
                      Text('-\$25.00',
                          style: TextStyle(
                              color: joviMintDark,
                              fontWeight: FontWeight.bold)),
                    ],
                  ),
              ],
            ),
          ),

        // ── Grand Total (navy gradient, matches landing page) ──
        Container(
          padding: const EdgeInsets.all(20),
          margin: const EdgeInsets.only(bottom: 16),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [joviNavy, joviNavyDark],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.25),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: Column(
            children: [
              const Text(
                'Total Monthly Plan',
                style: TextStyle(color: Colors.white70, fontSize: 14),
              ),
              const SizedBox(height: 8),
              Text(
                '\$${_grandTotal.toStringAsFixed(2)}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 36,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Health: \$${_totalHealthPremium.toStringAsFixed(2)}${_numPets > 0 ? " + Pets: \$${_petTotalPremium.toStringAsFixed(2)}" : ""}${_discountAmount > 0 ? " − Discount: \$${_discountAmount.toStringAsFixed(2)}" : ""}',
                style: const TextStyle(color: Colors.white60, fontSize: 12),
              ),
            ],
          ),
        ),

        _buildNavButtons(
          backLabel: 'Edit Plan',
          nextLabel: 'Proceed to Payment',
          onBack: () => _goToStep(OnboardingUpdateStep.review),
          onNext: () => _goToStep(OnboardingUpdateStep.payment),
          nextColor: joviCoral,
        ),
      ],
    );
  }

  // ─── Quote Line Item ──────────────────────────────────
  Widget _quoteLine(String label, double amount,
      {List<String>? details, Color? color}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(label,
                  style: const TextStyle(
                      fontWeight: FontWeight.w600, fontSize: 13.5)),
            ),
            Text(
              '\$${amount.toStringAsFixed(2)}/mo',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: color ?? joviNavy,
                fontSize: 14,
              ),
            ),
          ],
        ),
        if (details != null)
          ...details.map((d) => Padding(
                padding: const EdgeInsets.only(top: 2, left: 4),
                child: Text(d,
                    style: const TextStyle(color: kTextMedium, fontSize: 11.5)),
              )),
      ],
    );
  }

  // ─── Promo Code Section ───────────────────────────────
  Widget _buildPromoCodeSection() {
    return _sectionCard(
      title: 'Promo & Referral Codes',
      icon: Icons.card_giftcard,
      iconColor: joviGold,
      child: Column(
        children: [
          // Promo code
          Row(
            children: [
              Expanded(
                child: _buildFormField(
                  controller: _promoCodeCtrl,
                  label: 'Promo Code',
                  hint: 'e.g. WELCOME10',
                  enabled: _promoCodeApplied.isEmpty,
                ),
              ),
              const SizedBox(width: 8),
              _promoCodeApplied.isEmpty
                  ? ElevatedButton(
                      onPressed: _applyPromoCode,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: joviCoral,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 14),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10)),
                      ),
                      child: const Text('Apply'),
                    )
                  : TextButton(
                      onPressed: _removePromoCode,
                      child: const Text('Remove',
                          style: TextStyle(color: kErrorRed)),
                    ),
            ],
          ),

          // Referral code
          if (!_hasReferralDiscount) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _buildFormField(
                    controller: _referralCodeCtrl,
                    label: 'Referral Code',
                    hint: 'Friend\'s referral code',
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _applyReferralCode,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: joviMint,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 14),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                  ),
                  child: const Text('Apply'),
                ),
              ],
            ),
          ] else
            Row(
              children: [
                const Icon(Icons.check_circle, color: joviMint, size: 18),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'Referral discount applied: -\$25/mo',
                    style: TextStyle(
                        color: joviMintDark,
                        fontSize: 13,
                        fontWeight: FontWeight.w500),
                  ),
                ),
                TextButton(
                  onPressed: () {
                    setState(() => _hasReferralDiscount = false);
                    _referralCodeCtrl.clear();
                    _computeQuote();
                  },
                  child: const Text('Remove',
                      style: TextStyle(color: kErrorRed, fontSize: 12)),
                ),
              ],
            ),
        ],
      ),
    );
  }

  // ============================================================
  // Part 10 of 10: Payment Step, Confirmation, Close
  // ============================================================

  // ═══════════════════════════════════════════════════════
  // PAYMENT STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildPaymentStep(ResponsiveConfig config) {
    return Form(
      key: _paymentFormKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Amount summary (navy gradient to match Total Monthly Plan card)
          Container(
            padding: const EdgeInsets.all(16),
            margin: const EdgeInsets.only(bottom: 20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [joviNavy, joviNavyDark],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.2),
                  blurRadius: 10,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Amount Due Today',
                      style: TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'First month\'s contribution',
                      style: TextStyle(color: Colors.white54, fontSize: 11),
                    ),
                  ],
                ),
                Text(
                  '\$${_grandTotal.toStringAsFixed(2)}',
                  style: const TextStyle(
                    fontSize: 26,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ],
            ),
          ),

          const Text(
            'Payment Information',
            style: TextStyle(
                fontSize: 16, fontWeight: FontWeight.bold, color: kTextDark),
          ),
          const SizedBox(height: 4),
          const Text(
            'Your payment is processed securely',
            style: TextStyle(color: kTextMedium, fontSize: 12),
          ),
          const SizedBox(height: 16),

          // Card name
          _buildFormField(
            controller: _cardNameCtrl,
            label: 'Name on Card',
            validator: (v) => (v?.isEmpty ?? true) ? 'Required' : null,
          ),

          // Card number
          _buildFormField(
            controller: _cardNumberCtrl,
            label: 'Card Number',
            hint: '•••• •••• •••• ••••',
            keyboardType: TextInputType.number,
            formatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(19),
              _CardNumberFormatter(),
            ],
            validator: (v) {
              final digits = v?.replaceAll(' ', '') ?? '';
              if (digits.length < 15 || !_luhnValid(digits)) {
                return 'Check the card number';
              }
              return null;
            },
            suffix: const Padding(
              padding: EdgeInsets.all(12),
              child: Icon(Icons.credit_card, color: kTextLight, size: 20),
            ),
          ),

          // Exp & CVC
          if (config.columnsPerRow >= 2)
            Row(
              children: [
                Expanded(
                  child: _buildFormField(
                    controller: _cardExpCtrl,
                    label: 'Expiration',
                    hint: 'MM/YY',
                    keyboardType: TextInputType.number,
                    formatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(4),
                      _ExpirationDateFormatter(),
                    ],
                    validator: (v) {
                      final text = v?.replaceAll('/', '') ?? '';
                      if (text.length < 4) return 'Invalid';
                      return null;
                    },
                  ),
                ),
                SizedBox(width: config.fieldSpacing),
                Expanded(
                  child: _buildFormField(
                    controller: _cardCvcCtrl,
                    label: 'CVC',
                    hint: '•••',
                    keyboardType: TextInputType.number,
                    formatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(4),
                    ],
                    obscure: true,
                    validator: (v) => (v?.length ?? 0) < 3 ? 'Invalid' : null,
                  ),
                ),
              ],
            )
          else ...[
            _buildFormField(
              controller: _cardExpCtrl,
              label: 'Expiration',
              hint: 'MM/YY',
              keyboardType: TextInputType.number,
              formatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(4),
                _ExpirationDateFormatter(),
              ],
              validator: (v) {
                final text = v?.replaceAll('/', '') ?? '';
                if (text.length < 4) return 'Invalid';
                return null;
              },
            ),
            _buildFormField(
              controller: _cardCvcCtrl,
              label: 'CVC',
              hint: '•••',
              keyboardType: TextInputType.number,
              formatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(4),
              ],
              obscure: true,
              validator: (v) => (v?.length ?? 0) < 3 ? 'Invalid' : null,
            ),
          ],

          // Billing ZIP
          _buildFormField(
            controller: _cardZipCtrl,
            label: 'Billing ZIP Code',
            keyboardType: TextInputType.number,
            formatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(5),
            ],
            validator: (v) => (v?.length ?? 0) < 5 ? 'Invalid ZIP' : null,
          ),

          // Secure badge (mint)
          Container(
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(
              color: joviMint.withOpacity(0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: joviMint.withOpacity(0.3)),
            ),
            child: const Row(
              children: [
                Icon(Icons.lock, size: 18, color: joviMintDark),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Your payment information is encrypted and secure. We never store your full card number.',
                    style: TextStyle(color: joviMintDark, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),

          _buildNavButtons(
            backLabel: 'Back to Quote',
            nextLabel: _isProcessingPayment
                ? 'Processing…'
                : 'Pay \$${_grandTotal.toStringAsFixed(2)}',
            onBack: _goBack,
            onNext: _processPayment,
            isNextLoading: _isProcessingPayment,
            nextColor: joviCoral,
          ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════
  // CONFIRMATION STEP
  // ═══════════════════════════════════════════════════════
  Widget _buildConfirmationStep(ResponsiveConfig config) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 40),

          // Success icon (mint with coral pulse ring)
          Container(
            width: 110,
            height: 110,
            decoration: BoxDecoration(
              color: joviMint.withOpacity(0.12),
              shape: BoxShape.circle,
              border: Border.all(
                color: joviMint.withOpacity(0.3),
                width: 3,
              ),
            ),
            child: const Icon(Icons.check_circle, size: 68, color: joviMint),
          ),
          const SizedBox(height: 24),

          const Text(
            'Plan Updated',
            style: TextStyle(
                fontSize: 26, fontWeight: FontWeight.bold, color: kTextDark),
          ),
          const SizedBox(height: 12),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Text(
              'Your Jovi Health plan has been updated successfully.\nYour new monthly contribution is \$${_grandTotal.toStringAsFixed(2)}.',
              textAlign: TextAlign.center,
              style: const TextStyle(
                  color: kTextMedium, fontSize: 14, height: 1.5),
            ),
          ),
          const SizedBox(height: 8),

          if (_numPets > 0) ...[
            Container(
              margin: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: kPetPurpleLight,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: joviCoral.withOpacity(0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.pets, color: joviCoral, size: 20),
                  const SizedBox(width: 8),
                  Text(
                    '$_numPets pet${_numPets > 1 ? "s" : ""} covered • \$${_petTotalPremium.toStringAsFixed(2)}/mo',
                    style: const TextStyle(
                      color: joviCoral,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 24),

          // Plan Summary card
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.07),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.12)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.15),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Column(
              children: [
                const Text(
                  'Plan Summary',
                  style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                      color: kTextDark),
                ),
                const SizedBox(height: 12),
                _confirmRow(
                    'Members', '${1 + (_hasSpouse ? 1 : 0) + _numDependents}'),
                _confirmRow('Health Plan',
                    '\$${_totalHealthPremium.toStringAsFixed(2)}/mo'),
                if (_numPets > 0)
                  _confirmRow('Pet Plan',
                      '\$${_petTotalPremium.toStringAsFixed(2)}/mo'),
                if (_discountAmount > 0)
                  _confirmRow(
                      'Discount', '−\$${_discountAmount.toStringAsFixed(2)}'),
                if (_hasReferralDiscount) _confirmRow('Referral', '−\$25.00'),
                const Divider(height: 16),
                _confirmRow(
                    'Total Monthly', '\$${_grandTotal.toStringAsFixed(2)}',
                    isBold: true),
              ],
            ),
          ),

          const SizedBox(height: 32),

          // Done button (coral)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  // Navigate back or close
                  Navigator.of(context).maybePop();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: joviCoral,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  elevation: 0,
                ),
                child: const Text(
                  'Done',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                ),
              ),
            ),
          ),

          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _confirmRow(String label, String value, {bool isBold = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              color: isBold ? kTextDark : kTextMedium,
              fontSize: 13,
              fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              color: isBold ? joviCoral : kTextDark,
              fontSize: isBold ? 15 : 13,
              fontWeight: isBold ? FontWeight.bold : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
} // ← End of _OnboardingUpdateWidgetState

// ═════════════════════════════════════════════════════════════
// INPUT FORMATTERS
// ═════════════════════════════════════════════════════════════
class _CardNumberFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(' ', '');
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
    return newValue;
  }
}

// ═════════════════════════════════════════════════════════════
// CUSTOM CONFETTI (Jovi-colored particles)
// ═════════════════════════════════════════════════════════════
class _ConfettiParticle {
  final double x; // 0..1 horizontal start position
  final double y; // initial vertical offset (negative = above screen)
  final double speed; // fall speed multiplier
  final double drift; // horizontal drift
  final double size;
  final Color color;
  final double rotation;
  final double rotSpeed;

  _ConfettiParticle({
    required this.x,
    required this.y,
    required this.speed,
    required this.drift,
    required this.size,
    required this.color,
    required this.rotation,
    required this.rotSpeed,
  });
}

class _ConfettiOverlay extends StatefulWidget {
  final AnimationController controller;
  final List<_ConfettiParticle> particles;

  const _ConfettiOverlay({required this.controller, required this.particles});

  @override
  State<_ConfettiOverlay> createState() => _ConfettiOverlayState();
}

class _ConfettiOverlayState extends State<_ConfettiOverlay> {
  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTick);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTick);
    super.dispose();
  }

  void _onTick() {
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _ConfettiPainter(
        particles: widget.particles,
        progress: widget.controller.value,
      ),
    );
  }
}

class _ConfettiPainter extends CustomPainter {
  final List<_ConfettiParticle> particles;
  final double progress; // 0..1

  _ConfettiPainter({required this.particles, required this.progress});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint();
    for (final p in particles) {
      final t = progress;
      final px = p.x * size.width + p.drift * size.width * t;
      final py = p.y * size.height + p.speed * size.height * t * 1.2;
      final opacity = (1.0 - t).clamp(0.0, 1.0);

      if (py > size.height || opacity <= 0) continue;

      paint.color = p.color.withOpacity(opacity);
      canvas.save();
      canvas.translate(px, py);
      canvas.rotate(p.rotation + p.rotSpeed * t);
      canvas.drawRect(
        Rect.fromCenter(
            center: Offset.zero, width: p.size, height: p.size * 0.6),
        paint,
      );
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(covariant _ConfettiPainter oldDelegate) =>
      oldDelegate.progress != progress;
}

// ═════════════════════════════════════════════════════════════
// END — JOVI HEALTH UPDATE MEMBERSHIP WIDGET
// ═════════════════════════════════════════════════════════════
