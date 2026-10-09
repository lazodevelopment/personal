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
// PART 1 OF 10 - Imports, Constants, Breed Lists, Enums, Config
// ============================================================

// Jovi Health Rebrand - April 2026
// Version 2.5 - Enhanced pet section: birthdate calculator, coverage accordion, pre-existing conditions, validation, animations, empty state, summary cards (FlutterFlow compatible)
//
// Version 2.6 - 2026-09-22 - Apple HIG refinement pass
//  Motion
//  - Step transitions are a 320 ms critically-damped fade + 6% slide that
//    follows direction (Continue enters from the right, Back from the left).
//    r2.5 slid the whole screen in from the right for both directions.
//  - Removed the infinite trophy spin that ran from initState for the entire
//    flow (a ticker every frame, and continuous rotation is a Reduce Motion
//    trigger). It is now a one-shot scale-in on the confirmation step.
//  - Confetti plays once and fades out. r2.5 looped it forever and rebuilt a
//    new random set of pieces on every frame, so nothing actually "fell".
//  - Pet cards arrive with easeOutCubic (no overshoot). Progress bar animates
//    between steps. Reduce Motion is honoured everywhere.
//  - Press feedback on pointer-down for buttons and photo pickers; haptics on
//    checkbox changes and step changes; keyboard dismissed on step change.
//  Bugs
//  - Typed text in the name/email/phone/date/address fields inherited the
//    light theme's dark text colour on the navy fill. All fields now white.
//  - "Complete Onboarding" advanced to the done screen before the save
//    finished, and a failed save still showed "All Set". It now awaits the
//    save and only advances on success.
//  - After saving, build() showed the "Welcome Back… already complete"
//    screen instead of the done step. New members now see the done step.
//  - Restoring saved progress could land on step 4 ("Payment Successful")
//    without a payment. paymentProcessed is now persisted and the restored
//    step is capped at the payment step until it is true.
//  - Breed picker allocated a new TextEditingController on every build.
//  - Removed the "Sample codes: WELCOME10!…" hint that shipped to every user.
//  Typography / colour
//  - Titles tightened (-0.6 tracking, 1.1 leading); emoji removed from
//    headings; off-brand Material colours (green/blue/purple/indigo/teal)
//    in the coverage accordion and confetti replaced with the Jovi palette.
//  Not changed (flagged): raw card number/CVC are still collected in-app
//  and posted to a Cloud Function; three Google Places keys are hard-coded;
//  promo/referral discounts are validated client-side.
import 'package:flutter/foundation.dart';
import 'package:image_picker/image_picker.dart';
import 'package:uuid/uuid.dart';
import 'dart:convert';
import 'dart:typed_data';
import 'dart:async';
import 'dart:math';
import 'dart:ui' as ui_dart;
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:cloud_functions/cloud_functions.dart';
import 'package:flutter_google_places/flutter_google_places.dart';
import 'package:google_maps_webservice/places.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intl/intl.dart';

const _androidApiKey = 'AIzaSyAoI6CWUg7OPak96E2GNooyF6wod_F4zEg';
const _iosApiKey = 'AIzaSyBDyMELc4u1FkVqC-2ch7-tLsWBIezgN0A';
const _webApiKey = 'AIzaSyDCMwzNdUGWSXucLubmTaBWeCOjpbeONw0';
const _storageBucket = 'gs://kurv-health.firebasestorage.app';

// Jovi Health Brand Colors
const Color joviCoral = Color(0xFFFF6B4A);
const Color joviCoralLight = Color(0xFFFF8F73);
const Color joviNavy = Color(0xFF1A2744);
const Color joviNavyDark = Color(0xFF0F1A2E);
const Color joviNavyLight = Color(0xFF243352);
const Color joviWarmWhite = Color(0xFFFFF8F5);
const Color joviMint = Color(0xFF00D4AA);
const Color joviMintDark = Color(0xFF00B894);
const Color joviGold = Color(0xFFFFD166);
const Color joviSoftStone = Color(0xFFF0EFEB);

const List<String> usStates = [
  'AL',
  'AK',
  'AZ',
  'AR',
  'CA',
  'CO',
  'CT',
  'DE',
  'FL',
  'GA',
  'HI',
  'ID',
  'IL',
  'IN',
  'IA',
  'KS',
  'KY',
  'LA',
  'ME',
  'MD',
  'MA',
  'MI',
  'MN',
  'MS',
  'MO',
  'MT',
  'NE',
  'NV',
  'NH',
  'NJ',
  'NM',
  'NY',
  'NC',
  'ND',
  'OH',
  'OK',
  'OR',
  'PA',
  'RI',
  'SC',
  'SD',
  'TN',
  'TX',
  'UT',
  'VT',
  'VA',
  'WA',
  'WV',
  'WI',
  'WY'
];

// Pet breeds list
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

// Breed average life expectancy (in years) for age validation warnings
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
// ============================================================
// PART 2 OF 10 - Widget Declaration & State Variables
// ============================================================

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration step = Duration(milliseconds: 320);
  static const Duration reveal = Duration(milliseconds: 320);
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

class QuotePaymentWidget extends StatefulWidget {
  final double width;
  final double height;

  const QuotePaymentWidget({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  QuotePaymentWidgetState createState() => QuotePaymentWidgetState();
}

class QuotePaymentWidgetState extends State<QuotePaymentWidget>
    with TickerProviderStateMixin, WidgetsBindingObserver {
  // Responsive Layout Variables
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

  // Track previous screen configuration to prevent unnecessary rebuilds
  double? _lastScreenWidth;
  bool? _lastHasHinge;

  final _formKey = GlobalKey<FormState>();
  int _step = 0;
  final _uuid = Uuid();

  // Onboarding completion state management
  bool _isCheckingOnboardingStatus = true;
  bool _onboardingCompleted = false;

  // Photo bytes
  Uint8List? _parentBytes;
  Uint8List? _spouseBytes;
  late String _parentPhoto;
  late String _spousePhoto;

  // Pet photo bytes and URLs
  final List<Uint8List?> _petPhotoBytes = [];
  final List<String> _petPhotoUrls = [];

  // Personal Info Controllers
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _birthdate = TextEditingController();

  // Spouse Controllers
  bool _spouse = false;
  final _spouseFirst = TextEditingController();
  final _spouseLast = TextEditingController();
  final _spouseBirth = TextEditingController();

  // Dependent Controllers
  int _numDeps = 0;
  final _depFirst = <TextEditingController>[];
  final _depLast = <TextEditingController>[];
  final _depBirth = <TextEditingController>[];

  // Pet Insurance Controllers
  int _numPets = 0;
  final _petName = <TextEditingController>[];
  final _petAge = <TextEditingController>[];
  final _petType = <String>[]; // 'Dog' or 'Cat'
  final _petGender = <String>[]; // 'Male' or 'Female'
  final _petBreed = <String>[];
  List<Map<String, dynamic>> _petQuotes = [];

  // v2.5: Pet birthdate controllers
  final _petBirthdate = <TextEditingController>[];

  // v2.5: Pre-existing condition acknowledgment per pet
  final List<bool> _petPreExistingAck = [];
  final List<String> _petPreExistingNotes = [];
  final List<TextEditingController> _petPreExistingControllers = [];

  // v2.5: Pet card expanded/collapsed state
  final List<bool> _petCardExpanded = [];

  // v2.5: Coverage accordion expanded state per pet
  final List<bool> _petCoverageExpanded = [];

  // v2.5: Pet validation warnings
  final List<String?> _petAgeWarnings = [];
  final List<String?> _petNameWarnings = [];

  // v2.5: Pet card animation controllers
  final List<AnimationController?> _petAnimControllers = [];
  final List<Animation<double>?> _petAnimations = [];

  // Coverage Options
  bool _tobacco = false;
  bool _dental = false;
  bool _vision = false;

  // Quote Data
  double _totalPremium = 0;
  double _petTotalPremium = 0;
  List<Map<String, dynamic>> _quotes = [];
  bool _showQuoteSummary = false;

  // Payment Controllers
  final _card = TextEditingController();
  // ACH (BILL): bank account instead of a card. Numbers go straight to the
  // billSetupBankAccount Cloud Function; only BILL's ids and last4 are stored.
  final _routing = TextEditingController();
  final _account = TextEditingController();
  final _acctName = TextEditingController();
  String _acctType = 'CHECKING';
  final _expM = TextEditingController();
  final _expY = TextEditingController();
  final _cvc = TextEditingController();
  final _billingAddress = TextEditingController();
  final _city = TextEditingController();
  final _state = TextEditingController();
  final _zip = TextEditingController();
  final _country = TextEditingController(text: 'US');

  // Onboarding Controllers
  late TextEditingController _fullName;
  late TextEditingController _dobOnboard;
  late TextEditingController _phoneOnboard;
  late TextEditingController _referral;
  String? _height;
  String? _gender;
  final _heights = [
    for (var ft = 4; ft <= 7; ft++)
      for (var i = 0; i < 12; i++) '$ft ft $i in'
  ];
  final _weight = TextEditingController();
  final _conds = TextEditingController();
  final _address = TextEditingController();
  final _pharmacy = TextEditingController();
  final _emName = TextEditingController();
  final _emPhone = TextEditingController();

  // State Variables
  bool _isLoading = false;
  bool _paymentProcessed = false;
  bool _isAuthenticated = false;
  String? _payarcCustomerId;

  // Progress Persistence & Auto-Save
  Timer? _autoSaveTimer;
  bool _isLoadingSavedData = false;

  // Error Recovery
  int _paymentRetryCount = 0;
  int _uploadRetryCount = 0;
  static const int _maxRetryAttempts = 3;

  // Promo Codes & Discounts
  final _promoCode = TextEditingController();
  final _referralCode = TextEditingController();
  bool _isValidatingPromo = false;
  double _discountAmount = 0.0;
  double _discountPercentage = 0.0;
  String _promoCodeApplied = '';
  bool _hasReferralDiscount = false;

  // Animation Controllers
  late AnimationController _celebrate;
  late AnimationController _slideController;
  late AnimationController _fadeController;
  late AnimationController _confettiController;
  late Animation<Offset> _slideAnimation;
  late Animation<double> _fadeAnimation;
  late Animation<double> _confettiAnimation;

  // Google Places
  late GoogleMapsPlaces _places;

  // v2.6
  bool _reduceMotion = false; // MediaQuery.disableAnimations (Reduce Motion)
  int _stepDirection = 1; // +1 Continue, -1 Back — drives slide direction
  bool _justCompleted = false; // show the done step, not "Welcome Back"
  late List<Confetti> _confettiPieces; // generated once, not per frame
  // ============================================================
  // PART 3 OF 10 - initState, Lifecycle, Auth, Progress Save/Load
  // ============================================================

  @override
  void initState() {
    super.initState();

    // Add lifecycle observer for app state monitoring
    WidgetsBinding.instance.addObserver(this);

    _parentPhoto = '';
    _spousePhoto = '';

    final key = kIsWeb
        ? _webApiKey
        : (defaultTargetPlatform == TargetPlatform.iOS
            ? _iosApiKey
            : _androidApiKey);
    _places = GoogleMapsPlaces(apiKey: key);

    _fullName = TextEditingController();
    _dobOnboard = TextEditingController();
    _phoneOnboard = TextEditingController();
    _referral = TextEditingController();

    // One-shot scale-in for the confirmation trophy (played when that step
    // appears). r2.5 ran this as an infinite 2 s spin from initState.
    _celebrate = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 520),
    );

    _slideController = AnimationController(
      vsync: this,
      duration: _Motion.step,
    );

    _fadeController = AnimationController(
      vsync: this,
      duration: _Motion.step,
    );

    _confettiController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2800),
    );

    _slideAnimation = _buildSlide(1);

    _fadeAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(
      parent: _fadeController,
      curve: _Motion.settle,
    ));

    _confettiAnimation = CurvedAnimation(
      parent: _confettiController,
      curve: Curves.linear,
    );

    _confettiPieces = Confetti.generate(seed: 7);

    _slideController.forward();
    _fadeController.forward();

    _checkOnboardingStatus();
    _initializeAuth();
    _loadProgressData();
    _startAutoSave();
    _autoPopulateEmail();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = MediaQuery.of(context).disableAnimations;
    if (_reduceMotion) {
      if (_slideController.value != 1.0) _slideController.value = 1.0;
      if (_fadeController.value != 1.0) _fadeController.value = 1.0;
    }
    analyzeScreenConfiguration();
  }

  /// A 6% slide from the side the user is moving toward. Continue enters
  /// from the right, Back from the left — the path is symmetric, so the
  /// screens feel like they live in a row rather than always arriving from
  /// the same edge.
  Animation<Offset> _buildSlide(int direction) {
    return Tween<Offset>(
      begin: Offset(0.06 * direction, 0.0),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _slideController,
      curve: _Motion.settle,
    ));
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _checkOnboardingStatus();
    }
  }

  Future<void> _checkOnboardingStatus() async {
    try {
      User? user = FirebaseAuth.instance.currentUser;
      if (user != null) {
        final isCompleted = await _isOnboardingCompleted();
        setState(() {
          _onboardingCompleted = isCompleted;
          _isCheckingOnboardingStatus = false;
        });
      } else {
        setState(() {
          _onboardingCompleted = false;
          _isCheckingOnboardingStatus = false;
        });
      }
    } catch (e) {
      print('Error checking onboarding status: $e');
      setState(() {
        _onboardingCompleted = false;
        _isCheckingOnboardingStatus = false;
      });
    }
  }

  Future<bool> _isOnboardingCompleted() async {
    try {
      User? user = FirebaseAuth.instance.currentUser;
      if (user == null) return false;
      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();
      if (!userDoc.exists) return false;
      final data = userDoc.data();
      final onboardingCompleted = data?['onboardingCompleted'] == true;
      if (onboardingCompleted) await _setOnboardingCompletedLocally();
      return onboardingCompleted;
    } catch (e) {
      print('Error checking onboarding completion: $e');
      return await _isOnboardingCompletedLocally();
    }
  }

  Future<void> _setOnboardingCompletedLocally() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('onboarding_completed', true);
    } catch (e) {
      print('Error setting local onboarding flag: $e');
    }
  }

  Future<bool> _isOnboardingCompletedLocally() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      return prefs.getBool('onboarding_completed') ?? false;
    } catch (e) {
      return false;
    }
  }

  Future<void> _startAutoSave() async {
    _autoSaveTimer?.cancel();
    _autoSaveTimer = Timer.periodic(Duration(seconds: 5), (timer) {
      _saveProgressData();
    });
  }

  Future<void> _saveProgressData() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final progressData = {
        'step': _step,
        'firstName': _firstName.text,
        'lastName': _lastName.text,
        'email': _email.text,
        'phone': _phone.text,
        'birthdate': _birthdate.text,
        'spouse': _spouse,
        'spouseFirst': _spouseFirst.text,
        'spouseLast': _spouseLast.text,
        'spouseBirth': _spouseBirth.text,
        'numDeps': _numDeps,
        'numPets': _numPets,
        'tobacco': _tobacco,
        'dental': _dental,
        'vision': _vision,
        'fullName': _fullName.text,
        'dobOnboard': _dobOnboard.text,
        'phoneOnboard': _phoneOnboard.text,
        'height': _height ?? '',
        'gender': _gender ?? '',
        'weight': _weight.text,
        'conds': _conds.text,
        'address': _address.text,
        'pharmacy': _pharmacy.text,
        'emName': _emName.text,
        'emPhone': _emPhone.text,
        'referral': _referral.text,
        'promoCode': _promoCode.text,
        'referralCode': _referralCode.text,
        'discountAmount': _discountAmount,
        'discountPercentage': _discountPercentage,
        'promoCodeApplied': _promoCodeApplied,
        'paymentProcessed': _paymentProcessed,
      };

      for (int i = 0; i < _numDeps && i < _depFirst.length; i++) {
        progressData['depFirst_$i'] = _depFirst[i].text;
        progressData['depLast_$i'] = _depLast[i].text;
        progressData['depBirth_$i'] = _depBirth[i].text;
      }

      for (int i = 0; i < _numPets && i < _petName.length; i++) {
        progressData['petName_$i'] = _petName[i].text;
        progressData['petAge_$i'] = _petAge[i].text;
        progressData['petType_$i'] = i < _petType.length ? _petType[i] : '';
        progressData['petGender_$i'] =
            i < _petGender.length ? _petGender[i] : '';
        progressData['petBreed_$i'] = i < _petBreed.length ? _petBreed[i] : '';
        progressData['petPhotoUrl_$i'] =
            i < _petPhotoUrls.length ? _petPhotoUrls[i] : '';
        progressData['petBirthdate_$i'] =
            i < _petBirthdate.length ? _petBirthdate[i].text : '';
        progressData['petPreExistingAck_$i'] =
            i < _petPreExistingAck.length ? _petPreExistingAck[i] : false;
        progressData['petPreExistingNotes_$i'] =
            i < _petPreExistingControllers.length
                ? _petPreExistingControllers[i].text
                : '';
      }

      await prefs.setString('onboarding_progress', jsonEncode(progressData));
    } catch (e) {
      print('Error saving progress: $e');
    }
  }

  Future<void> _loadProgressData() async {
    try {
      setState(() => _isLoadingSavedData = true);
      final prefs = await SharedPreferences.getInstance();
      final progressString = prefs.getString('onboarding_progress');

      if (progressString != null) {
        final progressData = jsonDecode(progressString) as Map<String, dynamic>;

        setState(() {
          _paymentProcessed = progressData['paymentProcessed'] ?? false;
          int restoredStep = progressData['step'] ?? 0;
          // Never restore past the payment step unless the payment actually
          // went through; otherwise a restored session lands on the
          // "Payment successful" screen without paying.
          if (restoredStep >= 3 && !_paymentProcessed) restoredStep = 2;
          _step = restoredStep;
          _firstName.text = progressData['firstName'] ?? '';
          _lastName.text = progressData['lastName'] ?? '';
          _email.text = progressData['email'] ?? '';
          _phone.text = progressData['phone'] ?? '';
          _birthdate.text = progressData['birthdate'] ?? '';
          _spouse = progressData['spouse'] ?? false;
          _spouseFirst.text = progressData['spouseFirst'] ?? '';
          _spouseLast.text = progressData['spouseLast'] ?? '';
          _spouseBirth.text = progressData['spouseBirth'] ?? '';
          _numDeps = progressData['numDeps'] ?? 0;
          _numPets = progressData['numPets'] ?? 0;
          _tobacco = progressData['tobacco'] ?? false;
          _dental = progressData['dental'] ?? false;
          _vision = progressData['vision'] ?? false;
          _fullName.text = progressData['fullName'] ?? '';
          _dobOnboard.text = progressData['dobOnboard'] ?? '';
          _phoneOnboard.text = progressData['phoneOnboard'] ?? '';
          _height =
              progressData['height'].isEmpty ? null : progressData['height'];
          _gender =
              progressData['gender'].isEmpty ? null : progressData['gender'];
          _weight.text = progressData['weight'] ?? '';
          _conds.text = progressData['conds'] ?? '';
          _address.text = progressData['address'] ?? '';
          _pharmacy.text = progressData['pharmacy'] ?? '';
          _emName.text = progressData['emName'] ?? '';
          _emPhone.text = progressData['emPhone'] ?? '';
          _referral.text = progressData['referral'] ?? '';
          _promoCode.text = progressData['promoCode'] ?? '';
          _referralCode.text = progressData['referralCode'] ?? '';
          _discountAmount = progressData['discountAmount'] ?? 0.0;
          _discountPercentage = progressData['discountPercentage'] ?? 0.0;
          _promoCodeApplied = progressData['promoCodeApplied'] ?? '';
        });

        for (int i = 0; i < _numDeps; i++) {
          if (i >= _depFirst.length) {
            _depFirst.add(TextEditingController());
            _depLast.add(TextEditingController());
            _depBirth.add(TextEditingController());
          }
          _depFirst[i].text = progressData['depFirst_$i'] ?? '';
          _depLast[i].text = progressData['depLast_$i'] ?? '';
          _depBirth[i].text = progressData['depBirth_$i'] ?? '';
        }

        for (int i = 0; i < _numPets; i++) {
          if (i >= _petName.length) {
            _petName.add(TextEditingController());
            _petAge.add(TextEditingController());
            _petType.add('Dog');
            _petGender.add('Male');
            _petBreed.add('');
          }
          while (_petPhotoBytes.length <= i) _petPhotoBytes.add(null);
          while (_petPhotoUrls.length <= i) _petPhotoUrls.add('');
          while (_petBirthdate.length <= i)
            _petBirthdate.add(TextEditingController());
          while (_petPreExistingAck.length <= i) _petPreExistingAck.add(false);
          while (_petPreExistingNotes.length <= i) _petPreExistingNotes.add('');
          while (_petPreExistingControllers.length <= i)
            _petPreExistingControllers.add(TextEditingController());
          while (_petCardExpanded.length <= i) _petCardExpanded.add(true);
          while (_petCoverageExpanded.length <= i)
            _petCoverageExpanded.add(false);
          while (_petAgeWarnings.length <= i) _petAgeWarnings.add(null);
          while (_petNameWarnings.length <= i) _petNameWarnings.add(null);
          while (_petAnimControllers.length <= i) {
            final ac = AnimationController(
                vsync: this, duration: Duration(milliseconds: 400));
            _petAnimControllers.add(ac);
            _petAnimations
                .add(CurvedAnimation(parent: ac, curve: _Motion.settle));
            if (_reduceMotion) {
              ac.value = 1.0;
            } else {
              ac.forward();
            }
          }
          _petName[i].text = progressData['petName_$i'] ?? '';
          _petAge[i].text = progressData['petAge_$i'] ?? '';
          if (i < _petType.length)
            _petType[i] = progressData['petType_$i'] ?? 'Dog';
          if (i < _petGender.length)
            _petGender[i] = progressData['petGender_$i'] ?? 'Male';
          if (i < _petBreed.length)
            _petBreed[i] = progressData['petBreed_$i'] ?? '';
          if (i < _petPhotoUrls.length)
            _petPhotoUrls[i] = progressData['petPhotoUrl_$i'] ?? '';
          if (i < _petBirthdate.length)
            _petBirthdate[i].text = progressData['petBirthdate_$i'] ?? '';
          if (i < _petPreExistingAck.length)
            _petPreExistingAck[i] =
                progressData['petPreExistingAck_$i'] ?? false;
          if (i < _petPreExistingControllers.length)
            _petPreExistingControllers[i].text =
                progressData['petPreExistingNotes_$i'] ?? '';
          if (_petName[i].text.isNotEmpty &&
              _petAge[i].text.isNotEmpty &&
              (i < _petBreed.length && _petBreed[i].isNotEmpty)) {
            _petCardExpanded[i] = false;
          }
        }

        _computeQuote();
        _showSnackBar('Picked up where you left off', isSuccess: true);
      }
    } catch (e) {
      print('Error loading progress: $e');
    } finally {
      setState(() => _isLoadingSavedData = false);
    }
  }

  Future<void> _clearProgressData() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('onboarding_progress');
      _autoSaveTimer?.cancel();
    } catch (e) {
      print('Error clearing progress: $e');
    }
  }

  Future<void> _initializeAuth() async {
    try {
      User? user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        final userCredential = await FirebaseAuth.instance.signInAnonymously();
        user = userCredential.user;
      }
      if (user != null) setState(() => _isAuthenticated = true);
    } catch (e) {
      print('Authentication initialization error: $e');
    }
  }

  Future<bool> _checkNeedsRenewal() async {
    try {
      User? user = FirebaseAuth.instance.currentUser;
      if (user == null) return false;
      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();
      if (!userDoc.exists) return false;
      final data = userDoc.data();
      if (data == null || data['renew'] == null) return false;
      final renewTimestamp = data['renew'] as Timestamp;
      final renewDate = renewTimestamp.toDate();
      return renewDate.difference(DateTime.now()).inDays <= 30;
    } catch (e) {
      return false;
    }
  }

  Future<int?> _getDaysUntilRenewal() async {
    try {
      User? user = FirebaseAuth.instance.currentUser;
      if (user == null) return null;
      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();
      if (!userDoc.exists) return null;
      final data = userDoc.data();
      if (data == null || data['renew'] == null) return null;
      final renewTimestamp = data['renew'] as Timestamp;
      return renewTimestamp.toDate().difference(DateTime.now()).inDays;
    } catch (e) {
      return null;
    }
  }

  Future<void> _autoPopulateEmail() async {
    try {
      if (_email.text.isNotEmpty) return;
      User? user = FirebaseAuth.instance.currentUser;
      if (user != null && user.email != null && user.email!.isNotEmpty) {
        setState(() {
          _email.text = user!.email!;
        });
        await _saveProgressData();
      } else {
        try {
          final prefs = await SharedPreferences.getInstance();
          final savedEmail = prefs.getString('signup_email');
          if (savedEmail != null && savedEmail.isNotEmpty) {
            setState(() {
              _email.text = savedEmail;
            });
            await _saveProgressData();
          }
        } catch (e) {
          print('Error checking saved signup email: $e');
        }
      }
    } catch (e) {
      print('Error auto-populating email: $e');
    }
  }

  static Future<void> saveSignupEmail(String email) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('signup_email', email);
    } catch (e) {
      print('Error saving signup email: $e');
    }
  }

  Future<void> _clearSavedEmail() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('signup_email');
    } catch (e) {
      print('Error clearing saved email: $e');
    }
  }
  // ============================================================
  // PART 4 OF 10 - Responsive Layout, Dispose, Error Recovery,
  //                Promo Codes, Pet Premium Calc, Pet Photo Upload
  // ============================================================

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

    if (_lastScreenWidth == screenWidth && _lastHasHinge == hasHinge) return;

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
    if (currentScreenType == ScreenType.expanded || layoutSettings.hasHinge)
      return child;
    if (currentScreenType == ScreenType.large &&
        layoutSettings.contentMax < double.infinity) {
      return Center(
          child: ConstrainedBox(
              constraints: BoxConstraints(maxWidth: layoutSettings.contentMax),
              child: child));
    }
    return child;
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    final controllers = [
      _firstName,
      _lastName,
      _email,
      _phone,
      _birthdate,
      _spouseFirst,
      _spouseLast,
      _spouseBirth,
      _card,
      _expM,
      _expY,
      _cvc,
      _billingAddress,
      _city,
      _state,
      _zip,
      _country,
      _fullName,
      _dobOnboard,
      _phoneOnboard,
      _referral,
      _weight,
      _conds,
      _address,
      _pharmacy,
      _emName,
      _emPhone,
      _promoCode,
      _referralCode,
      ..._depFirst,
      ..._depLast,
      ..._depBirth,
      ..._petName,
      ..._petAge,
      ..._petBirthdate,
      ..._petPreExistingControllers,
    ];
    for (var controller in controllers) controller.dispose();
    for (var ac in _petAnimControllers) ac?.dispose();
    _celebrate.dispose();
    _slideController.dispose();
    _fadeController.dispose();
    _confettiController.dispose();
    _autoSaveTimer?.cancel();
    super.dispose();
  }

  Future<T> _retryOperation<T>(
      Future<T> Function() operation, String operationName,
      {int maxRetries = 3}) async {
    for (int attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (e) {
        if (attempt == maxRetries) rethrow;
        await Future.delayed(Duration(seconds: attempt * 2));
        _showSnackBar('Retry attempt $attempt of $maxRetries...',
            isLoading: true);
      }
    }
    throw Exception('All retry attempts failed');
  }

  Future<bool> _processPaymentWithRetry() async {
    try {
      return await _retryOperation(
          () => _processMembershipPayment(), 'Payment processing',
          maxRetries: _maxRetryAttempts);
    } catch (e) {
      _showSnackBar(
          'Payment failed after ${_maxRetryAttempts} attempts. Please check your connection and try again.',
          isError: true);
      return false;
    }
  }

  Future<void> _uploadPhotoWithRetry({required bool forSpouse}) async {
    try {
      await _retryOperation(
          () => _pickAndSetPhoto(forSpouse: forSpouse), 'Photo upload',
          maxRetries: _maxRetryAttempts);
    } catch (e) {
      _showSnackBar(
          'Photo upload failed after ${_maxRetryAttempts} attempts. Please try again.',
          isError: true);
    }
  }

  Future<void> _validatePromoCode() async {
    if (_promoCode.text.trim().isEmpty) return;
    setState(() => _isValidatingPromo = true);
    try {
      await Future.delayed(Duration(seconds: 1));
      final code = _promoCode.text.trim().toUpperCase();
      double discount = 0.0;
      double percentage = 0.0;
      switch (code) {
        case 'WELCOME10!':
          percentage = 10.0;
          discount = _totalPremium * 0.10;
          break;
        case 'SAVE25!':
          discount = 25.0;
          break;
        case 'FIRSTMONTH!':
          discount = _totalPremium;
          break;
        case 'FAMILY20!':
          if (_spouse || _numDeps > 0) {
            percentage = 20.0;
            discount = _totalPremium * 0.20;
          }
          break;
        default:
          throw Exception('Invalid promo code');
      }
      if (discount > 0) {
        setState(() {
          _discountAmount = discount;
          _discountPercentage = percentage;
          _promoCodeApplied = code;
        });
        _computeQuote();
        _showSnackBar('Promo code applied successfully!', isSuccess: true);
      } else {
        throw Exception('Promo code not applicable');
      }
    } catch (e) {
      _showSnackBar('Invalid or expired promo code', isError: true);
      setState(() {
        _discountAmount = 0.0;
        _discountPercentage = 0.0;
        _promoCodeApplied = '';
      });
      _computeQuote();
    } finally {
      setState(() => _isValidatingPromo = false);
    }
  }

  void _applyReferralDiscount() {
    if (_referralCode.text.trim().isNotEmpty && !_hasReferralDiscount) {
      setState(() {
        _hasReferralDiscount = true;
        if (_discountPercentage == 0.0) {
          _discountPercentage = 10.0;
          _discountAmount = _totalPremium * 0.10;
        }
      });
      _computeQuote();
      _showSnackBar('Referral discount applied!', isSuccess: true);
    }
  }

  void _removePromoCode() {
    setState(() {
      _promoCode.clear();
      _discountAmount = 0.0;
      _discountPercentage = 0.0;
      _promoCodeApplied = '';
      _hasReferralDiscount = false;
    });
    _computeQuote();
  }

  double _calculatePetPremium(int ageInMonths) {
    if (ageInMonths >= 8 && ageInMonths <= 11) return 60.0;
    int ageInYears = (ageInMonths / 12).floor();
    if (ageInYears >= 1 && ageInYears <= 20)
      return 60.0 + ((ageInYears - 1) * 7.0);
    return 60.0;
  }

  int _parseAgeToMonths(String ageText) {
    try {
      ageText = ageText.toLowerCase().trim();
      int totalMonths = 0;
      if (ageText.contains('year')) {
        final yearMatch = RegExp(r'(\d+)\s*year').firstMatch(ageText);
        if (yearMatch != null)
          totalMonths += int.parse(yearMatch.group(1)!) * 12;
      }
      if (ageText.contains('month')) {
        final monthMatch = RegExp(r'(\d+)\s*month').firstMatch(ageText);
        if (monthMatch != null) totalMonths += int.parse(monthMatch.group(1)!);
      }
      if (totalMonths == 0)
        totalMonths =
            int.tryParse(ageText.replaceAll(RegExp(r'[^\d]'), '')) ?? 0;
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
      _saveProgressData();
    } catch (e) {
      print('Error computing pet age from birthdate: $e');
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
              'The average lifespan for ${breed}s is ~$expectedMax years. Please double-check this age.';
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

  void _validatePetName(int petIndex) {
    while (_petNameWarnings.length <= petIndex) _petNameWarnings.add(null);
    if (petIndex < _petName.length && _petName[petIndex].text.trim().isEmpty) {
      setState(() {
        _petNameWarnings[petIndex] =
            "Don't forget to name your pet for the plan!";
      });
    } else {
      setState(() {
        _petNameWarnings[petIndex] = null;
      });
    }
  }

  void _ensurePetListsForIndex(int i) {
    while (_petName.length <= i) _petName.add(TextEditingController());
    while (_petAge.length <= i) _petAge.add(TextEditingController());
    while (_petBirthdate.length <= i)
      _petBirthdate.add(TextEditingController());
    while (_petType.length <= i) _petType.add('Dog');
    while (_petGender.length <= i) _petGender.add('Male');
    while (_petBreed.length <= i) _petBreed.add('');
    while (_petPhotoBytes.length <= i) _petPhotoBytes.add(null);
    while (_petPhotoUrls.length <= i) _petPhotoUrls.add('');
    while (_petPreExistingAck.length <= i) _petPreExistingAck.add(false);
    while (_petPreExistingNotes.length <= i) _petPreExistingNotes.add('');
    while (_petPreExistingControllers.length <= i)
      _petPreExistingControllers.add(TextEditingController());
    while (_petCardExpanded.length <= i) _petCardExpanded.add(true);
    while (_petCoverageExpanded.length <= i) _petCoverageExpanded.add(false);
    while (_petAgeWarnings.length <= i) _petAgeWarnings.add(null);
    while (_petNameWarnings.length <= i) _petNameWarnings.add(null);
    while (_petAnimControllers.length <= i) {
      final ac = AnimationController(
          vsync: this, duration: Duration(milliseconds: 400));
      _petAnimControllers.add(ac);
      _petAnimations
          .add(CurvedAnimation(parent: ac, curve: _Motion.settle));
      if (_reduceMotion) {
              ac.value = 1.0;
            } else {
              ac.forward();
            }
    }
  }

  bool _isPetCardComplete(int i) {
    if (i >= _petName.length) return false;
    return _petName[i].text.trim().isNotEmpty &&
        _petAge[i].text.trim().isNotEmpty &&
        (i < _petBreed.length && _petBreed[i].isNotEmpty);
  }

  Future<void> _pickPetBirthdate(int petIndex) async {
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
      while (_petBirthdate.length <= petIndex)
        _petBirthdate.add(TextEditingController());
      setState(() {
        _petBirthdate[petIndex].text =
            "${picked.month.toString().padLeft(2, '0')}/${picked.day.toString().padLeft(2, '0')}/${picked.year}";
      });
      _updatePetAgeFromBirthdate(petIndex);
    }
  }

  String _formatPhoneNumber(String phoneNumber) {
    String digits = phoneNumber.replaceAll(RegExp(r'[^\d]'), '');
    if (digits.length > 10) digits = digits.substring(0, 10);
    if (digits.length >= 6)
      return '(${digits.substring(0, 3)}) ${digits.substring(3, 6)}-${digits.substring(6)}';
    else if (digits.length >= 3)
      return '(${digits.substring(0, 3)}) ${digits.substring(3)}';
    else if (digits.length > 0) return '(${digits}';
    return digits;
  }

  void _onPhoneChanged(String value, TextEditingController controller) {
    final formatted = _formatPhoneNumber(value);
    if (formatted != value) {
      controller.value = TextEditingValue(
          text: formatted,
          selection: TextSelection.collapsed(offset: formatted.length));
    }
    _saveProgressData();
  }

  Future<void> _pickAndSetPetPhoto(int petIndex) async {
    if (!_isAuthenticated) await _initializeAuth();
    final picker = await ImagePicker().pickImage(
        source: ImageSource.gallery,
        maxWidth: 512,
        maxHeight: 512,
        imageQuality: 80);
    if (picker == null) return;
    setState(() => _isLoading = true);
    final bytes = await picker.readAsBytes();
    final ext = picker.path.split('.').last;
    while (_petPhotoBytes.length <= petIndex) _petPhotoBytes.add(null);
    while (_petPhotoUrls.length <= petIndex) _petPhotoUrls.add('');
    setState(() {
      _petPhotoBytes[petIndex] = bytes;
    });
    final user = FirebaseAuth.instance.currentUser;
    final uid = user?.uid ?? 'anonymous';
    final path = 'uploads/$uid/pets/${_uuid.v4()}.$ext';
    _showSnackBar('Uploading pet photo...', isLoading: true);
    try {
      final storage = FirebaseStorage.instanceFor(bucket: _storageBucket);
      final ref = storage.ref().child(path);
      await ref.putData(bytes);
      final url = await ref.getDownloadURL();
      setState(() {
        _petPhotoUrls[petIndex] = url;
      });
      _saveProgressData();
      _showSnackBar('Pet photo uploaded successfully!', isSuccess: true);
    } catch (e) {
      _showSnackBar('Failed to upload pet photo.', isError: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _uploadPetPhotoWithRetry(int petIndex) async {
    try {
      await _retryOperation(
          () => _pickAndSetPetPhoto(petIndex), 'Pet photo upload',
          maxRetries: _maxRetryAttempts);
    } catch (e) {
      _showSnackBar(
          'Pet photo upload failed after ${_maxRetryAttempts} attempts.',
          isError: true);
    }
  }
  // ============================================================
  // PART 5 OF 10 - Dialogs, Snackbar, Pickers, Payment, Photos
  // ============================================================

  Future<void> _showPetCoverageDialog() async {
    await showDialog(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Column(children: [
            Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: joviCoral.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(50)),
              child: Icon(Icons.pets, size: 40, color: joviCoral),
            ),
            SizedBox(height: 16),
            Text('Pet Sharing Details',
                style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: joviNavy)),
          ]),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildCoverageSection(
                    '✓ Coverage Type', 'Accident + Illness', Colors.green),
                _buildCoverageSection(
                    '✓ Reimbursement', '90% sharing', Colors.green),
                _buildCoverageSection('✓ Annual Deductible',
                    '\$500 (separate from human plan)', Colors.green),
                SizedBox(height: 16),
                Text('What\'s Shared:',
                    style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: joviNavy)),
                SizedBox(height: 8),
                _buildCoverageItem('Vet exam fees'),
                _buildCoverageItem(
                    'Diagnostics (blood tests, x-rays, MRIs, CT scans)'),
                _buildCoverageItem(
                    'Surgery at licensed vets or emergency hospitals'),
                _buildCoverageItem('Prescription medications & special diets'),
                _buildCoverageItem(
                    'Specialized treatments (acupuncture, microchipping)'),
                _buildCoverageItem(
                    'Accident sharing (toxic ingestions, cuts, broken bones)'),
                _buildCoverageItem(
                    'Illness sharing (breed-specific, allergies, hip dysplasia)'),
                _buildCoverageItem('Dental illnesses & trauma'),
                _buildCoverageItem('Cancer treatment'),
                _buildCoverageItem(
                    'Chronic conditions (diabetes, arthritis, allergies)'),
                _buildCoverageItem('Orthopedic conditions'),
                SizedBox(height: 16),
                Text('What\'s NOT Shared:',
                    style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: joviCoralLight)),
                SizedBox(height: 8),
                _buildNotCoveredItem('Waiting periods'),
                _buildNotCoveredItem(
                    'Pre-existing conditions (cured conditions eligible after 180 days)'),
                _buildNotCoveredItem('Cosmetic procedures'),
                _buildNotCoveredItem('Breeding costs'),
                _buildNotCoveredItem(
                    'Preventive care (can be added separately)'),
                SizedBox(height: 16),
                Container(
                  padding: EdgeInsets.all(12),
                  decoration: BoxDecoration(
                      color: joviWarmWhite,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: joviCoral.withOpacity(0.2))),
                  child: Row(children: [
                    Icon(Icons.info, color: joviCoral, size: 20),
                    SizedBox(width: 8),
                    Expanded(
                        child: Text('Valid at any vet in the US or Canada',
                            style: TextStyle(color: joviCoral, fontSize: 12))),
                  ]),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text('Close',
                  style:
                      TextStyle(color: joviCoral, fontWeight: FontWeight.w600)),
            ),
          ],
        );
      },
    );
  }

  Widget _buildCoverageSection(String title, String value, Color color) {
    return Padding(
      padding: EdgeInsets.only(bottom: 8),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(Icons.check_circle, color: color, size: 20),
        SizedBox(width: 8),
        Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title,
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
          Text(value, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
        ])),
      ]),
    );
  }

  Widget _buildCoverageItem(String text) {
    return Padding(
      padding: EdgeInsets.only(left: 8, bottom: 4),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('• ', style: TextStyle(color: Colors.green[700], fontSize: 16)),
        Expanded(
            child: Text(text,
                style: TextStyle(fontSize: 13, color: Colors.grey[700]))),
      ]),
    );
  }

  Widget _buildNotCoveredItem(String text) {
    return Padding(
      padding: EdgeInsets.only(left: 8, bottom: 4),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('• ', style: TextStyle(color: joviCoralLight, fontSize: 16)),
        Expanded(
            child: Text(text,
                style: TextStyle(fontSize: 13, color: Colors.grey[700]))),
      ]),
    );
  }

  /// Toast in the app's own voice: navy surface, tinted icon, white text.
  void _showSnackBar(String message,
      {bool isError = false, bool isSuccess = false, bool isLoading = false}) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    final accent = isError
        ? const Color(0xFFFF8A80)
        : (isSuccess ? joviMint : joviCoral);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(SnackBar(
      content: Row(children: [
        if (isLoading)
          SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2, color: accent)),
        if (isSuccess)
          Icon(Icons.check_circle_rounded, color: accent, size: 20),
        if (isError) Icon(Icons.error_rounded, color: accent, size: 20),
        const SizedBox(width: 10),
        Expanded(
            child: Text(message,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.2))),
      ]),
      duration: isError
          ? const Duration(milliseconds: 3500)
          : (isLoading
              ? const Duration(seconds: 4)
              : const Duration(milliseconds: 1800)),
      backgroundColor: joviNavyLight,
      elevation: 0,
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
      shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: accent.withOpacity(0.35))),
    ));
  }

  bool _isStateAllowed(String state) {
    return state == 'CO' || state == 'AZ' || state == 'TX';
  }

  Future<void> _showComingSoonDialog(String stateName) async {
    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Column(children: [
            Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: joviCoral.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(50)),
              child: Icon(Icons.location_on, size: 40, color: joviCoral),
            ),
            SizedBox(height: 16),
            Text('Coming Soon!',
                style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: joviNavy)),
          ]),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('We\'re expanding to $stateName soon!',
                textAlign: TextAlign.center,
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.grey[800])),
            SizedBox(height: 12),
            Text(
                'Jovi Health is currently available in Colorado, Arizona, and Texas. We\'re working hard to bring our services to your area.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: Colors.grey[600])),
            SizedBox(height: 20),
            Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                  color: joviWarmWhite,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: joviCoral.withOpacity(0.2))),
              child: Row(children: [
                Icon(Icons.email, color: joviCoral, size: 20),
                SizedBox(width: 8),
                Expanded(
                    child: Text(
                        'Join our waitlist to be notified when we launch in your state!',
                        style: TextStyle(color: joviCoral, fontSize: 12))),
              ]),
            ),
          ]),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                setState(() {
                  _state.text = '';
                });
              },
              child: Text('OK',
                  style:
                      TextStyle(color: joviCoral, fontWeight: FontWeight.w600)),
            ),
          ],
        );
      },
    );
  }

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
                surface: Colors.white)),
        child: child!,
      ),
    );
    if (date != null) {
      controller.text =
          '${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}-${date.year}';
      if (_step <= 2) _computeQuote();
    }
  }

  Future<void> _pickPlace(TextEditingController controller,
      {bool isBillingAddress = false}) async {
    try {
      final prediction = await PlacesAutocomplete.show(
        context: context,
        apiKey: _places.apiKey!,
        mode: Mode.overlay,
        types: [],
        strictbounds: false,
        components: [Component(Component.country, 'us')],
        hint: 'Search for address...',
        radius: 10000,
        language: 'en',
      );
      if (prediction != null) {
        final details = await _places.getDetailsByPlaceId(prediction.placeId!);
        final result = details.result;
        if (isBillingAddress && result.addressComponents != null) {
          String streetNumber = '', streetName = '', stateCode = '';
          for (var component in result.addressComponents!) {
            final types = component.types;
            if (types.contains('street_number'))
              streetNumber = component.longName;
            else if (types.contains('route'))
              streetName = component.longName;
            else if (types.contains('locality'))
              WidgetsBinding.instance.addPostFrameCallback((_) {
                _city.text = component.longName;
              });
            else if (types.contains('administrative_area_level_1'))
              stateCode = component.shortName;
            else if (types.contains('postal_code'))
              WidgetsBinding.instance.addPostFrameCallback((_) {
                _zip.text = component.longName;
              });
            else if (types.contains('country'))
              WidgetsBinding.instance.addPostFrameCallback((_) {
                _country.text = component.shortName;
              });
          }
          if (stateCode.isNotEmpty && !_isStateAllowed(stateCode)) {
            _showComingSoonDialog(stateCode);
            WidgetsBinding.instance.addPostFrameCallback((_) {
              _billingAddress.text = '';
              _city.text = '';
              _state.text = '';
              _zip.text = '';
            });
            return;
          }
          if (streetNumber.isNotEmpty || streetName.isNotEmpty) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              _billingAddress.text = '$streetNumber $streetName'.trim();
            });
          }
          WidgetsBinding.instance.addPostFrameCallback((_) {
            _state.text = stateCode;
          });
        } else {
          String address = result.formattedAddress ?? prediction.description!;
          if (address.endsWith(', USA'))
            address = address.substring(0, address.length - 5);
          WidgetsBinding.instance.addPostFrameCallback((_) {
            controller.text = address;
          });
        }
        if (!isBillingAddress || _isStateAllowed(_state.text)) {
          _showSnackBar('Address selected successfully!', isSuccess: true);
        }
      }
    } catch (e) {
      _showSnackBar('Address lookup failed. Please type manually.',
          isError: true);
    }
  }

  int _calcAge(String birthdate) {
    final parts = birthdate.split('-');
    final birth =
        DateTime(int.parse(parts[2]), int.parse(parts[0]), int.parse(parts[1]));
    final now = DateTime.now();
    var age = now.year - birth.year;
    if (now.month < birth.month ||
        (now.month == birth.month && now.day < birth.day)) age--;
    return age;
  }

  Future<void> _sendWelcomeEmail() async {
    try {
      final functions = FirebaseFunctions.instance;
      final callable = functions.httpsCallable('sendWelcomeEmail');
      int memberCount = 1;
      if (_spouse) memberCount++;
      memberCount += _numDeps;
      String deductible = '1500';
      if (_quotes.isNotEmpty)
        deductible = _quotes.first['deductible'].toString();
      await callable.call({
        'firstName': _firstName.text.trim(),
        'lastName': _lastName.text.trim(),
        'email': _email.text.trim(),
        'planType': (_spouse || _numDeps > 0) ? 'Family' : 'Individual',
        'totalPremium': _totalPremium.toString(),
        'deductible': deductible,
        'memberCount': memberCount.toString(),
        'dentalCoverage': _dental,
        'visionCoverage': _vision,
        'petCount': _numPets.toString(),
        'petPremium': _petTotalPremium.toString(),
      });
    } catch (e) {
      print('Error sending welcome email: $e');
    }
  }

  Future<bool> _processMembershipPayment() async {
    try {
      final user = FirebaseAuth.instance.currentUser;
      if (user == null) throw Exception('User not authenticated');
      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();
      final bool isRenewal = userDoc.exists && userDoc.data()?['renew'] != null;
      final functions = FirebaseFunctions.instance;
      final callable = functions.httpsCallable('billSetupBankAccount');
      final result = await callable.call({
        'routingNumber': _routing.text.trim(),
        'accountNumber': _account.text.trim(),
        'accountType': _acctType,
        'nameOnAccount': _acctName.text.trim(),
        'activate': true,
      });
      final data = result.data is Map ? Map<String, dynamic>.from(result.data) : <String, dynamic>{};
      if (data['success'] == true || data['ok'] == true) {
        if (isRenewal) {
          final currentRenewTimestamp = userDoc.data()?['renew'] as Timestamp?;
          if (currentRenewTimestamp != null) {
            final currentRenewDate = currentRenewTimestamp.toDate();
            final newRenewDate = DateTime(currentRenewDate.year + 1,
                currentRenewDate.month, currentRenewDate.day);
            await FirebaseFirestore.instance
                .collection('users')
                .doc(user.uid)
                .update({
              'renew': Timestamp.fromDate(newRenewDate),
              'lastRenewalDate': FieldValue.serverTimestamp(),
              'renewalCount': FieldValue.increment(1),
              'lastPaymentDate': FieldValue.serverTimestamp(),
            });
          }
        }
        return true;
      } else {
        _showSnackBar(
            result.data['error'] ?? 'Payment failed. Please try again.',
            isError: true);
        return false;
      }
    } catch (e) {
      _showSnackBar('Payment processing error: ${e.toString()}', isError: true);
      return false;
    }
  }

  bool _validateCardNumber(String cardNumber) {
    cardNumber = cardNumber.replaceAll(' ', '');
    if (cardNumber.length < 13 || cardNumber.length > 19) return false;
    int sum = 0;
    bool alternate = false;
    for (int i = cardNumber.length - 1; i >= 0; i--) {
      int digit = int.tryParse(cardNumber[i]) ?? -1;
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

  Future<void> _processPayment() async {
    if (!_formKey.currentState!.validate()) return;
    if (!RegExp(r'^\d{9}$').hasMatch(_routing.text.trim())) {
      _showSnackBar('Routing number should be 9 digits.', isError: true);
      return;
    }
    if (!RegExp(r'^\d{4,17}$').hasMatch(_account.text.trim())) {
      _showSnackBar('Please check the account number.', isError: true);
      return;
    }
    if (_acctName.text.trim().isEmpty) {
      _showSnackBar('Enter the name on the account.', isError: true);
      return;
    }
    setState(() => _isLoading = true);
    _showSnackBar('Authenticating...', isLoading: true);
    try {
      User? user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        _showSnackBar('Setting up secure connection...', isLoading: true);
        final userCredential = await FirebaseAuth.instance.signInAnonymously();
        user = userCredential.user;
        if (user == null) throw Exception('Failed to authenticate.');
        await Future.delayed(Duration(seconds: 1));
        user = FirebaseAuth.instance.currentUser;
        if (user == null) throw Exception('Authentication verification failed');
      }
      _showSnackBar('Processing payment...', isLoading: true);
      final success = await _processPaymentWithRetry();
      if (success) {
        setState(() {
          _paymentProcessed = true;
          _isLoading = false;
        });
        HapticFeedback.heavyImpact();
        _showSnackBar('Bank account added. Your membership is active.', isSuccess: true);
        await Future.delayed(const Duration(milliseconds: 350));
        if (!mounted) return;
        _nextStep();
        // One-shot celebration, skipped under Reduce Motion.
        if (!_reduceMotion) _confettiController.forward(from: 0);
      } else {
        setState(() => _isLoading = false);
      }
    } catch (e) {
      setState(() => _isLoading = false);
      String errorMessage = e.toString().contains('unauthenticated')
          ? 'Authentication failed. Please refresh and try again.'
          : e.toString().contains('network')
              ? 'Network error. Please check your connection.'
              : 'Payment failed: ${e.toString()}';
      _showSnackBar(errorMessage, isError: true);
    }
  }

  Future<void> _pickAndSetPhoto({required bool forSpouse}) async {
    if (!_isAuthenticated) await _initializeAuth();
    final picker = await ImagePicker().pickImage(
        source: ImageSource.gallery,
        maxWidth: 512,
        maxHeight: 512,
        imageQuality: 80);
    if (picker == null) return;
    setState(() => _isLoading = true);
    final bytes = await picker.readAsBytes();
    final ext = picker.path.split('.').last;
    setState(() {
      if (forSpouse)
        _spouseBytes = bytes;
      else
        _parentBytes = bytes;
    });
    final user = FirebaseAuth.instance.currentUser;
    final uid = user?.uid ?? 'anonymous';
    final path = 'uploads/$uid/${_uuid.v4()}.$ext';
    _showSnackBar('Uploading photo...', isLoading: true);
    try {
      final storage = FirebaseStorage.instanceFor(bucket: _storageBucket);
      final ref = storage.ref().child(path);
      await ref.putData(bytes);
      final url = await ref.getDownloadURL();
      setState(() {
        if (forSpouse)
          _spousePhoto = url;
        else
          _parentPhoto = url;
      });
      _showSnackBar('Photo uploaded successfully!', isSuccess: true);
    } catch (e) {
      _showSnackBar('Failed to upload photo.', isError: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  bool _isWideScreen(BuildContext context) {
    return layoutSettings.wideMode;
  }

  double _getContentWidth(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    if (screenWidth > 1200)
      return 800;
    else if (screenWidth > 800)
      return 600;
    else if (screenWidth > 600)
      return screenWidth * 0.85;
    else
      return screenWidth;
  }

  // ============================================================
  // PART 6 OF 10 - Quote Computation, Save, Navigation
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
          'date': _depBirth[i].text,
          'primary': false
        },
    ];
    for (var i = 0; i < membersData.length; i++) {
      final member = membersData[i];
      final dateStr = member['date'] as String;
      if (dateStr.isEmpty) continue;
      final age = _calcAge(dateStr);
      double basePremium = age <= 29
          ? 150
          : age <= 39
              ? 200
              : age <= 49
                  ? 250
                  : age <= 59
                      ? 300
                      : 350;
      double premium = basePremium;
      if (member['primary'] == true && _tobacco) premium *= 1.15;
      if (_dental) premium += 35;
      if (_vision) premium += 15;
      total += premium;
      final deductible = age <= 26
          ? 1500
          : age <= 45
              ? 2000
              : age <= 60
                  ? 2500
                  : 3000;
      final photo =
          (i == 0) ? _parentPhoto : ((i == 1 && _spouse) ? _spousePhoto : '');
      list.add({
        'memberId': _uuid.v4(),
        'name': member['label'],
        'age': age,
        'basePremium': basePremium,
        'contribution': premium,
        'deductible': deductible,
        'photo_url': photo,
        'hasTobacco': member['primary'] == true && _tobacco,
        'hasDental': _dental,
        'hasVision': _vision,
      });
    }
    setState(() {
      _quotes = list;
      _totalPremium = total;
      _showQuoteSummary = list.isNotEmpty;
    });
    _computePetQuote();
    _applyDiscountsToQuote();
  }

  void _computePetQuote() {
    final petList = <Map<String, dynamic>>[];
    double petTotal = 0;
    for (var i = 0; i < _numPets; i++) {
      if (i >= _petAge.length || _petAge[i].text.isEmpty) continue;
      final ageInMonths = _parseAgeToMonths(_petAge[i].text);
      if (ageInMonths < 2 || ageInMonths > 240) continue;
      final premium = _calculatePetPremium(ageInMonths);
      petTotal += premium;
      final petPhotoUrl = i < _petPhotoUrls.length ? _petPhotoUrls[i] : '';
      petList.add({
        'petId': _uuid.v4(),
        'name': i < _petName.length ? _petName[i].text : 'Pet ${i + 1}',
        'type': i < _petType.length ? _petType[i] : 'Dog',
        'breed': i < _petBreed.length ? _petBreed[i] : '',
        'gender': i < _petGender.length ? _petGender[i] : 'Male',
        'ageInMonths': ageInMonths,
        'contribution': premium,
        'deductible': 500,
        'reimbursement': 90,
        'photo_url': petPhotoUrl,
      });
    }
    setState(() {
      _petQuotes = petList;
      _petTotalPremium = petTotal;
    });
  }

  void _applyDiscountsToQuote() {
    if (_discountAmount > 0) {
      setState(() {
        _totalPremium =
            (_totalPremium - _discountAmount).clamp(0.0, double.infinity);
      });
    }
  }

  Future<bool> _save() async {
    setState(() => _isLoading = true);
    try {
      User? user = FirebaseAuth.instance.currentUser;
      if (user == null) {
        await _initializeAuth();
        user = FirebaseAuth.instance.currentUser;
        if (user == null) throw Exception('Authentication required');
      }
      final plan = (_spouse || _numDeps > 0) ? 'Family' : 'Individual';
      final deps = List<String>.generate(
          _numDeps,
          (i) => jsonEncode({
                'first': _depFirst[i].text.trim(),
                'last': _depLast[i].text.trim(),
                'birth': _depBirth[i].text.trim(),
                'memberId': _uuid.v4(),
                'photo_url': '',
              }));
      final membersJson = _quotes.map(jsonEncode).toList();
      final pets = List<String>.generate(
          _numPets,
          (i) => jsonEncode({
                'name': _petName[i].text.trim(),
                'type': _petType[i],
                'breed': _petBreed[i],
                'gender': _petGender[i],
                'ageInMonths': _parseAgeToMonths(_petAge[i].text),
                'birthdate': i < _petBirthdate.length
                    ? _petBirthdate[i].text.trim()
                    : '',
                'petId':
                    _petQuotes.length > i ? _petQuotes[i]['petId'] : _uuid.v4(),
                'premium': _petQuotes.length > i ? _petQuotes[i]['premium'] : 0,
                'deductible': 500,
                'reimbursement': 90,
                'photo_url': i < _petPhotoUrls.length ? _petPhotoUrls[i] : '',
                'hasPreExistingConditions': i < _petPreExistingAck.length
                    ? _petPreExistingAck[i]
                    : false,
                'preExistingNotes': i < _petPreExistingControllers.length
                    ? _petPreExistingControllers[i].text.trim()
                    : '',
              }));
      final now = DateTime.now();
      final renewalDate = DateTime(
          now.year + 1, now.month, now.day, now.hour, now.minute, now.second);
      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .get();
      final bool isRenewal = userDoc.exists && userDoc.data()?['renew'] != null;
      final doc = {
        'first': _firstName.text.trim(),
        'last': _lastName.text.trim(),
        'email': _email.text.trim(),
        'phone': _phoneOnboard.text.trim(),
        'birth': _birthdate.text.trim(),
        'photo_url': _parentPhoto,
        'spouse': _spouse,
        if (_spouse) ...{
          'sFirst': _spouseFirst.text.trim(),
          'sLast': _spouseLast.text.trim(),
          'sBirth': _spouseBirth.text.trim(),
          'sPhoto_url': _spousePhoto,
        },
        'numDeps': _numDeps,
        'deps': deps,
        'tobacco': _tobacco,
        'dental': _dental,
        'vision': _vision,
        'members': membersJson,
        'totalPremium': _totalPremium,
        'planType': plan,
        'onboard_fullName': _fullName.text.trim(),
        'onboard_birth': _dobOnboard.text.trim(),
        'onboard_phone': _phoneOnboard.text.trim(),
        'onboard_height': _height ?? '',
        'onboard_weight': _weight.text.trim(),
        'onboard_gender': _gender ?? '',
        'onboard_conditions': _conds.text.trim(),
        'onboard_address': _address.text.trim(),
        'onboard_pharmacy': _pharmacy.text.trim(),
        'onboard_emName': _emName.text.trim(),
        'onboard_emPhone': _emPhone.text.trim(),
        'referral': _referral.text.trim(),
        'paymentProcessed': _paymentProcessed,
        'payarcCustomerId': _payarcCustomerId,
        'renew': Timestamp.fromDate(renewalDate),
        'lastPaymentDate': FieldValue.serverTimestamp(),
        'membershipStartDate': isRenewal ? null : FieldValue.serverTimestamp(),
        'isActive': true,
        'hasPetInsurance': _numPets > 0,
        'numPets': _numPets,
        'pets': pets,
        'petTotalPremium': _petTotalPremium,
        'onboardingCompleted': true,
        'onboardingCompletedAt': FieldValue.serverTimestamp(),
        'ts': FieldValue.serverTimestamp(),
      };
      if (isRenewal) doc.removeWhere((key, value) => value == null);
      await FirebaseFirestore.instance
          .collection('users')
          .doc(user.uid)
          .set(doc, SetOptions(merge: true));
      await _sendWelcomeEmail();
      await _setOnboardingCompletedLocally();
      await _clearProgressData();
      await _clearSavedEmail();
      _showSnackBar('Profile saved successfully!', isSuccess: true);
      setState(() {
        _onboardingCompleted = true;
        _justCompleted = true;
      });
      return true;
    } catch (e) {
      _showSnackBar('Failed to save profile: ${e.toString()}', isError: true);
      return false;
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _nextStep() => _changeStep(1);

  void _prevStep() => _changeStep(-1);

  void _changeStep(int delta) {
    // Dismiss the keyboard so the new step is not half-covered by it.
    FocusManager.instance.primaryFocus?.unfocus();
    HapticFeedback.selectionClick();
    _stepDirection = delta >= 0 ? 1 : -1;
    setState(() {
      _step += delta;
      _slideAnimation = _buildSlide(_stepDirection);
    });
    if (_reduceMotion) {
      _slideController.value = 1.0;
      _fadeController.value = 1.0;
      return;
    }
    _slideController.forward(from: 0);
    _fadeController.forward(from: 0);
  }
  // ============================================================
  // PART 7 OF 10 - build(), Header, Step Router, Step Buttons, Steps 1-3
  // ============================================================

  @override
  Widget build(BuildContext context) {
    // Show loading screen while checking onboarding status
    if (_isCheckingOnboardingStatus || _isLoadingSavedData) {
      return Scaffold(
        backgroundColor: joviNavy,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Image.network(
                'https://firebasestorage.googleapis.com/v0/b/kurv-health.firebasestorage.app/o/jovi-logo-white-header%403x.png?alt=media&token=2f75145b-e99b-4379-86e7-227ffc1ebf93',
                height: 80,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stackTrace) {
                  return Text(
                    'jovi',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                    ),
                  );
                },
              ),
              SizedBox(height: 24),
              CircularProgressIndicator(color: joviCoral),
              SizedBox(height: 16),
              Text(
                _isLoadingSavedData
                    ? 'Restoring your progress...'
                    : 'Loading...',
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.white70,
                ),
              ),
            ],
          ),
        ),
      );
    }

    // Returning member who already finished. A member who just finished in
    // this session sees the done step instead (r2.5 greeted new members
    // with "Welcome Back… already complete").
    if (_onboardingCompleted && !_justCompleted) {
      return Scaffold(
        backgroundColor: joviNavy,
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.check_circle, size: 80, color: joviCoral),
              SizedBox(height: 24),
              Text(
                'Welcome back',
                style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.6,
                    color: Colors.white),
              ),
              SizedBox(height: 16),
              Text(
                'Your onboarding is already complete.',
                style: TextStyle(fontSize: 18, color: Colors.white70),
              ),
              SizedBox(height: 32),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: _buildPrimaryButton('Go to Dashboard',
                    onPressed: () => context.go('/home')),
              ),
            ],
          ),
        ),
      );
    }

    return wrapWithConstraints(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final contentWidth = _getContentWidth(context);
          return Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [joviNavyDark, joviNavy, joviNavyLight],
              ),
            ),
            child: Stack(
              children: [
                // Ambient coral blob (top-right, sign-in style)
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
                          joviCoral.withOpacity(0.09),
                          Colors.transparent,
                        ]),
                      ),
                    ),
                  ),
                ),
                // Ambient mint blob (bottom-left, subtler)
                Positioned(
                  bottom: 140,
                  left: -40,
                  child: IgnorePointer(
                    child: Container(
                      width: 160,
                      height: 160,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(colors: [
                          joviMint.withOpacity(0.06),
                          Colors.transparent,
                        ]),
                      ),
                    ),
                  ),
                ),
                Center(
                  child: Container(
                    width: contentWidth,
                    constraints: BoxConstraints(
                        maxWidth: 800, minHeight: constraints.maxHeight),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        children: [
                          _buildHeader(),
                          Expanded(
                            child: SlideTransition(
                              position: _slideAnimation,
                              child: FadeTransition(
                                opacity: _fadeAnimation,
                                child: Column(
                                  children: [
                                    Expanded(
                                      child: SingleChildScrollView(
                                        padding: EdgeInsets.symmetric(
                                          horizontal: layoutSettings.paddingH,
                                          vertical: layoutSettings.paddingV,
                                        ),
                                        child: _buildCurrentStep(),
                                      ),
                                    ),
                                    Container(
                                      padding: EdgeInsets.only(
                                        left: layoutSettings.paddingH,
                                        right: layoutSettings.paddingH,
                                        bottom: MediaQuery.of(context)
                                                .padding
                                                .bottom +
                                            20,
                                        top: 16,
                                      ),
                                      decoration: BoxDecoration(
                                        color: joviNavyDark.withOpacity(0.85),
                                        border: Border(
                                          top: BorderSide(
                                              color: Colors.white
                                                  .withOpacity(0.08),
                                              width: 1),
                                        ),
                                      ),
                                      child: _buildStepButtons(),
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
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildHeader() {
    final statusBarHeight = MediaQuery.of(context).padding.top;
    return Container(
      padding: EdgeInsets.fromLTRB(layoutSettings.paddingH,
          statusBarHeight + 16, layoutSettings.paddingH, 20),
      decoration: BoxDecoration(
        color: joviNavyDark.withOpacity(0.85),
        border: Border(
          bottom: BorderSide(color: Colors.white.withOpacity(0.08), width: 1),
        ),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 10,
              offset: Offset(0, 2))
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Center(
                  child: Image.network(
                    'https://storage.googleapis.com/flutterflow-io-6f20.appspot.com/projects/kurv-health-3vcfmp/assets/gveqn2eoe4nf/jovi_header_logo_master.png',
                    height: layoutSettings.wideMode ? 50 : 40,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stackTrace) {
                      return Text(
                        'jovi',
                        style: TextStyle(
                          fontSize: layoutSettings.wideMode ? 28 : 24,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      );
                    },
                  ),
                ),
              ),
              if (_step < 5)
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: joviCoral.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                        color: joviCoral.withOpacity(0.35), width: 1),
                  ),
                  child: Text(
                    'Step ${_step + 1} of 6',
                    style: TextStyle(
                      color: joviCoralLight,
                      fontWeight: FontWeight.w600,
                      fontSize: layoutSettings.actionTextSize + 1,
                    ),
                  ),
                ),
            ],
          ),
          SizedBox(height: 16),
          Semantics(
            label: 'Step ${_step + 1} of 6',
            child: TweenAnimationBuilder<double>(
              tween: Tween<double>(end: (_step + 1) / 6),
              duration: _reduceMotion ? Duration.zero : _Motion.step,
              curve: _Motion.settle,
              builder: (context, value, _) => ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: LinearProgressIndicator(
                  value: value,
                  backgroundColor: Colors.white.withOpacity(0.08),
                  color: joviCoral,
                  minHeight: 6,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCurrentStep() {
    switch (_step) {
      case 0:
        return _stepOne();
      case 1:
        return _stepTwo();
      case 2:
        return _stepThree();
      case 3:
        return _stepConfirm();
      case 4:
        return _stepOnboard();
      case 5:
        return _stepDone();
      default:
        return Container();
    }
  }

  Widget _buildStepButtons() {
    switch (_step) {
      case 0:
        return _buildPrimaryButton('Continue', onPressed: () {
          if (_parentPhoto.isEmpty && _parentBytes == null) {
            _showSnackBar('Please select your profile photo.', isError: true);
            return;
          }
          if (!_formKey.currentState!.validate()) return;
          _computeQuote();
          _nextStep();
          _fullName.text = '${_firstName.text} ${_lastName.text}';
          _dobOnboard.text = _birthdate.text;
          _phoneOnboard.text = _phone.text;
        });
      case 1:
        return layoutSettings.useTwoColumnLayout
            ? Row(children: [
                Expanded(
                    child: _buildSecondaryButton('Back', onPressed: _prevStep)),
                SizedBox(width: 16),
                Expanded(
                    flex: 2,
                    child: _buildPrimaryButton('Continue', onPressed: () {
                      if (_spouse &&
                          _spousePhoto.isEmpty &&
                          _spouseBytes == null) {
                        _showSnackBar('Please select spouse photo.',
                            isError: true);
                        return;
                      }
                      if (!_formKey.currentState!.validate()) return;
                      _nextStep();
                    })),
              ])
            : Column(children: [
                _buildPrimaryButton('Continue', onPressed: () {
                  if (_spouse && _spousePhoto.isEmpty && _spouseBytes == null) {
                    _showSnackBar('Please select spouse photo.', isError: true);
                    return;
                  }
                  if (!_formKey.currentState!.validate()) return;
                  _nextStep();
                }),
                SizedBox(height: 12),
                _buildSecondaryButton('Back', onPressed: _prevStep),
              ]);
      case 2:
        return layoutSettings.useTwoColumnLayout
            ? Row(children: [
                Expanded(
                    child: _buildSecondaryButton('Back',
                        onPressed: _isLoading ? null : _prevStep)),
                SizedBox(width: 16),
                Expanded(
                    flex: 2,
                    child: _buildPrimaryButton(
                      _isLoading ? 'Processing...' : 'Complete Purchase',
                      onPressed: _isLoading ? null : _processPayment,
                      showLoader: _isLoading,
                    )),
              ])
            : Column(children: [
                _buildPrimaryButton(
                  _isLoading ? 'Processing...' : 'Complete Purchase',
                  onPressed: _isLoading ? null : _processPayment,
                  showLoader: _isLoading,
                ),
                SizedBox(height: 12),
                _buildSecondaryButton('Back',
                    onPressed: _isLoading ? null : _prevStep),
              ]);
      case 3:
        return _buildPrimaryButton('Continue to Complete Profile',
            onPressed: _nextStep);
      case 4:
        return _buildPrimaryButton(
          _isLoading ? 'Completing...' : 'Complete Onboarding',
          onPressed: _isLoading
              ? null
              : () async {
                  if (!_formKey.currentState!.validate()) return;
                  // Advance only once the profile is actually saved.
                  final ok = await _save();
                  if (ok && mounted) _nextStep();
                },
          showLoader: _isLoading,
        );
      case 5:
        // go() rather than push(): Back must not return into a finished
        // onboarding flow.
        return _buildPrimaryButton('Go to Dashboard',
            onPressed: () => context.go('/home'));
      default:
        return Container();
    }
  }

  Widget _stepOne() {
    return Column(children: [
      _buildStepHeader(Icons.person_add, 'Create Your Membership',
          'Tell us about yourself to get started'),
      SizedBox(height: 24),
      _buildAvatarPicker(
          bytes: _parentBytes,
          url: _parentPhoto,
          onTap: () => _pickAndSetPhoto(forSpouse: false)),
      SizedBox(height: 20),
      if (layoutSettings.useTwoColumnLayout)
        Row(children: [
          Expanded(
              child: _buildTextField(_firstName, 'First Name', Icons.person)),
          SizedBox(width: 12),
          Expanded(
              child: _buildTextField(
                  _lastName, 'Last Name', Icons.person_outline)),
        ])
      else
        Column(children: [
          _buildTextField(_firstName, 'First Name', Icons.person),
          SizedBox(height: 16),
          _buildTextField(_lastName, 'Last Name', Icons.person_outline),
        ]),
      SizedBox(height: 16),
      _buildEmailField(_email, 'Email Address'),
      SizedBox(height: 16),
      _buildPhoneField(_phone, 'Phone Number'),
      SizedBox(height: 16),
      _buildDateField(_birthdate, 'Date of Birth'),
      if (_birthdate.text.isNotEmpty) ...[
        SizedBox(height: 12),
        _buildAgeIndicator(_calcAge(_birthdate.text))
      ],
      SizedBox(height: 100),
    ]);
  }

  Widget _stepTwo() {
    while (_depFirst.length < _numDeps) {
      _depFirst.add(TextEditingController());
      _depLast.add(TextEditingController());
      _depBirth.add(TextEditingController());
    }
    while (_petName.length < _numPets) {
      _petName.add(TextEditingController());
      _petAge.add(TextEditingController());
      _petType.add('Dog');
      _petGender.add('Male');
      _petBreed.add('');
    }
    for (int idx = 0; idx < _numPets; idx++) _ensurePetListsForIndex(idx);
    return Column(children: [
      _buildStepHeader(Icons.family_restroom, 'Family Plan',
          'Add family members, pets, and sharing options'),
      SizedBox(height: 24),
      _buildSpouseSection(),
      SizedBox(height: 20),
      _buildDependentsSection(),
      SizedBox(height: 20),
      _buildPetInsuranceSection(),
      SizedBox(height: 20),
      _buildCoverageOptions(),
      SizedBox(height: 20),
      _buildPromoCodeSection(),
      if (_showQuoteSummary) ...[SizedBox(height: 24), _buildQuoteSummary()],
      SizedBox(height: 100),
    ]);
  }

  Widget _stepThree() {
    return Column(children: [
      _buildStepHeader(Icons.payment, 'Payment Information',
          'Secure automatic monthly plan'),
      SizedBox(height: 24),
      _buildQuoteSummary(),
      SizedBox(height: 24),
      _buildSecurityBadge(),
      SizedBox(height: 20),
      _buildPaymentForm(),
      SizedBox(height: 20),
      _buildPaymentInfo(),
      if (!_isAuthenticated) ...[
        SizedBox(height: 16),
        Container(
          padding: EdgeInsets.all(12),
          decoration: BoxDecoration(
              color: joviGold.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: joviGold.withOpacity(0.4), width: 1)),
          child: Row(children: [
            Icon(Icons.info_outline, color: joviGold, size: 20),
            SizedBox(width: 8),
            Expanded(
                child: Text('Setting up secure connection...',
                    style: TextStyle(color: joviGold, fontSize: 14))),
          ]),
        ),
      ],
      SizedBox(height: 100),
    ]);
  }

  Widget _stepConfirm() {
    // Trophy scale-in plays once when this step first shows (also covers a
    // restored session that lands here directly).
    if (_celebrate.value == 0.0 && !_celebrate.isAnimating) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        if (_reduceMotion) {
          _celebrate.value = 1.0;
        } else {
          _celebrate.forward();
        }
      });
    }
    return Stack(clipBehavior: Clip.none, children: [
      _buildConfirmationContent(),
      if (_paymentProcessed && !_reduceMotion)
        Positioned.fill(
          child: IgnorePointer(
            child: AnimatedBuilder(
              animation: _confettiAnimation,
              builder: (context, child) {
                return CustomPaint(
                    painter: ConfettiPainter(
                        _confettiPieces, _confettiAnimation.value));
              },
            ),
          ),
        ),
    ]);
  }

  Widget _stepOnboard() {
    return Column(children: [
      _buildStepHeader(Icons.assignment_ind, 'Member Onboarding',
          'Complete your health profile'),
      SizedBox(height: 24),
      _buildOnboardingPersonalInfo(),
      SizedBox(height: 20),
      _buildOnboardingPhysicalInfo(),
      SizedBox(height: 20),
      _buildOnboardingHealthInfo(),
      SizedBox(height: 20),
      _buildOnboardingEmergencyContact(),
      SizedBox(height: 20),
      _buildOnboardingLocationInfo(),
      SizedBox(height: 20),
      _buildOnboardingReferral(),
      SizedBox(height: 100),
    ]);
  }

  Widget _stepDone() {
    return _buildCompletionScreen();
  }
  // ============================================================
  // PART 8 OF 10 - Helper Widgets, Sections
  // ============================================================

  Widget _buildStepHeader(IconData icon, String title, String subtitle) {
    return Container(
      padding: EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [joviCoral, joviCoralLight],
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
              color: joviCoral.withOpacity(0.35),
              blurRadius: 24,
              offset: Offset(0, 10)),
          BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 20,
              offset: Offset(0, 4)),
        ],
      ),
      child: Column(children: [
        Container(
          padding: EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.18),
            borderRadius: BorderRadius.circular(50),
            border: Border.all(color: Colors.white.withOpacity(0.3), width: 1),
          ),
          child: Icon(icon, size: 32, color: Colors.white),
        ),
        SizedBox(height: 16),
        Text(title,
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: layoutSettings.wideMode ? 32 : 28,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.6,
                height: 1.1,
                color: Colors.white)),
        SizedBox(height: 8),
        Text(subtitle,
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: layoutSettings.wideMode ? 18 : 16,
                color: Colors.white.withOpacity(0.85))),
      ]),
    );
  }

  Widget _buildAvatarPicker(
      {required Uint8List? bytes,
      required String url,
      required VoidCallback onTap,
      String title = 'Profile Photo'}) {
    return Column(children: [
      Text(title,
          style: TextStyle(
              fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white)),
      SizedBox(height: 12),
      _Pressable(
        reduceMotion: _reduceMotion,
        pressedScale: 0.94,
        semanticsLabel: title,
        semanticsHint: 'Choose a photo',
        onTap: onTap,
        child: Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: joviCoral, width: 3),
            boxShadow: [
              BoxShadow(
                  color: joviCoral.withOpacity(0.4),
                  blurRadius: 20,
                  offset: Offset(0, 6))
            ],
          ),
          child: ClipOval(
            child: bytes != null
                ? Image.memory(bytes, fit: BoxFit.cover)
                : url.isNotEmpty
                    ? Image.network(url, fit: BoxFit.cover)
                    : Container(
                        color: joviCoral.withOpacity(0.18),
                        child:
                            Icon(Icons.camera_alt, color: joviCoral, size: 32)),
          ),
        ),
      ),
      SizedBox(height: 8),
      Text('Tap to change',
          style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 12)),
    ]);
  }

  Widget _buildPetAvatarPicker(
      {required int petIndex, String title = 'Pet Photo'}) {
    final Uint8List? bytes =
        petIndex < _petPhotoBytes.length ? _petPhotoBytes[petIndex] : null;
    final String url =
        petIndex < _petPhotoUrls.length ? _petPhotoUrls[petIndex] : '';
    return Column(children: [
      Text(title,
          style: TextStyle(
              fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white)),
      SizedBox(height: 8),
      _Pressable(
        reduceMotion: _reduceMotion,
        pressedScale: 0.94,
        semanticsLabel: title,
        semanticsHint: 'Choose a photo',
        onTap: () => _pickAndSetPetPhoto(petIndex),
        child: Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: joviCoral, width: 3),
            boxShadow: [
              BoxShadow(
                  color: joviCoral.withOpacity(0.4),
                  blurRadius: 20,
                  offset: Offset(0, 6))
            ],
          ),
          child: ClipOval(
            child: bytes != null
                ? Image.memory(bytes, fit: BoxFit.cover)
                : url.isNotEmpty
                    ? Image.network(url, fit: BoxFit.cover)
                    : Container(
                        color: joviCoral.withOpacity(0.18),
                        child: Icon(Icons.pets, color: joviCoral, size: 28)),
          ),
        ),
      ),
      SizedBox(height: 6),
      Text('Tap to add photo',
          style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 11)),
    ]);
  }

  Widget _buildTextField(
      TextEditingController controller, String label, IconData icon,
      [TextInputType keyboardType = TextInputType.text]) {
    return TextFormField(
      controller: controller,
      keyboardType: keyboardType,
      textInputAction: TextInputAction.next,
      // r2.5 left the text colour to the (light) theme: dark text on the
      // navy fill.
      style: const TextStyle(color: Colors.white, fontSize: 16),
      cursorColor: joviCoral,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, color: joviCoral),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: joviCoral, width: 2)),
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
        filled: true,
        fillColor: Colors.white.withOpacity(0.06),
      ),
      onChanged: (value) => _saveProgressData(),
      validator: (v) => v!.isEmpty ? 'This field is required' : null,
    );
  }

  Widget _buildEmailField(TextEditingController controller, String label) {
    return TextFormField(
      controller: controller,
      keyboardType: TextInputType.emailAddress,
      textInputAction: TextInputAction.next,
      autofillHints: const [AutofillHints.email],
      autocorrect: false,
      style: const TextStyle(color: Colors.white, fontSize: 16),
      cursorColor: joviCoral,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(Icons.email, color: joviCoral),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: joviCoral, width: 2)),
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
        filled: true,
        fillColor: Colors.white.withOpacity(0.06),
      ),
      onChanged: (value) => _saveProgressData(),
      validator: (v) {
        if (v == null || v.isEmpty) return 'Email is required';
        return RegExp(r'^[^@]+@[^@]+\.[^@]+$').hasMatch(v)
            ? null
            : 'Please enter a valid email';
      },
    );
  }

  Widget _buildPhoneField(TextEditingController controller, String label) {
    return TextFormField(
      controller: controller,
      keyboardType: TextInputType.phone,
      textInputAction: TextInputAction.next,
      autofillHints: const [AutofillHints.telephoneNumber],
      style: const TextStyle(color: Colors.white, fontSize: 16),
      cursorColor: joviCoral,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(Icons.phone, color: joviCoral),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: joviCoral, width: 2)),
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
        filled: true,
        fillColor: Colors.white.withOpacity(0.06),
      ),
      onChanged: (value) => _onPhoneChanged(value, controller),
      validator: (v) {
        if (v == null || v.isEmpty) return 'Phone number is required';
        return v.replaceAll(RegExp(r'[^\d]'), '').length >= 10
            ? null
            : 'Please enter a valid phone number';
      },
    );
  }

  Widget _buildDateField(TextEditingController controller, String label) {
    return TextFormField(
      controller: controller,
      readOnly: true,
      style: const TextStyle(color: Colors.white, fontSize: 16),
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(Icons.calendar_today, color: joviCoral),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: joviCoral, width: 2)),
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
        filled: true,
        fillColor: Colors.white.withOpacity(0.06),
      ),
      onTap: () => _pickDate(context, controller),
      validator: (v) => v!.isEmpty ? 'Date is required' : null,
    );
  }

  Widget _buildAddressPicker(
      TextEditingController controller, String label, IconData icon) {
    return TextFormField(
      controller: controller,
      style: const TextStyle(color: Colors.white, fontSize: 16),
      cursorColor: joviCoral,
      decoration: InputDecoration(
        labelText: label,
        hintText: 'Tap to search...',
        prefixIcon: Icon(icon, color: joviCoral),
        suffixIcon: IconButton(
            icon: Icon(Icons.search, color: joviCoral),
            onPressed: () => _pickPlace(controller)),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: joviCoral, width: 2)),
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
        filled: true,
        fillColor: Colors.white.withOpacity(0.06),
      ),
      onTap: () => _pickPlace(controller),
      validator: (v) => v!.isEmpty ? 'Address is required' : null,
    );
  }

  Widget _buildDropdown<T>(
      {required T? value,
      required String label,
      required List<DropdownMenuItem<T>> items,
      required void Function(T?) onChanged,
      String? Function(T?)? validator}) {
    return DropdownButtonFormField<T>(
      value: value,
      dropdownColor: joviNavyLight,
      iconEnabledColor: Colors.white.withOpacity(0.7),
      style: TextStyle(color: Colors.white, fontSize: 16),
      decoration: InputDecoration(
        labelText: label,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: joviCoral, width: 2)),
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
        filled: true,
        fillColor: Colors.white.withOpacity(0.06),
      ),
      items: items,
      onChanged: onChanged,
      validator: validator,
    );
  }

  Widget _buildSearchableBreedDropdown(
      {required String? value,
      required String label,
      required List<String> breeds,
      required void Function(String?) onChanged,
      String? Function(String?)? validator}) {
    return TextFormField(
      // Keyed on the value so the field refreshes when a breed is picked,
      // without allocating a new controller on every build.
      key: ValueKey('breed_${value ?? ''}'),
      initialValue: value ?? '',
      style: TextStyle(color: Colors.white, fontSize: 16),
      decoration: InputDecoration(
        labelText: label,
        hintText: 'Tap to search breeds...',
        prefixIcon: Icon(Icons.pets, color: joviCoral),
        suffixIcon: Icon(Icons.search, color: joviCoral),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.white.withOpacity(0.15))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: joviCoral, width: 2)),
        labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
        hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
        filled: true,
        fillColor: Colors.white.withOpacity(0.06),
      ),
      readOnly: true,
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
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    TextField(
                      decoration: InputDecoration(
                          labelText: 'Search breeds',
                          prefixIcon: Icon(Icons.search),
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12))),
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
                            onTap: () {
                              Navigator.of(context).pop(filteredBreeds[index]);
                            });
                      },
                    )),
                  ]),
                ),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: Text('Cancel'))
                ],
              );
            });
          },
        );
        if (selected != null) onChanged(selected);
      },
      validator: validator,
    );
  }

  Widget _buildCheckbox(String title, bool value,
      {String? subtitle,
      IconData? icon,
      required void Function(bool?) onChanged}) {
    return AnimatedContainer(
      duration: _reduceMotion ? Duration.zero : const Duration(milliseconds: 200),
      curve: _Motion.settle,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
            color: value ? joviCoral : Colors.white.withOpacity(0.15),
            width: value ? 2 : 1),
        color: value
            ? joviCoral.withOpacity(0.12)
            : Colors.white.withOpacity(0.04),
      ),
      child: CheckboxListTile(
        title: Row(children: [
          if (icon != null) ...[
            Icon(icon,
                color: value ? joviCoral : Colors.white.withOpacity(0.6),
                size: 20),
            SizedBox(width: 8)
          ],
          Expanded(
              child: Text(title,
                  style: TextStyle(
                      fontWeight: FontWeight.w600, color: Colors.white))),
        ]),
        subtitle: subtitle != null
            ? Text(subtitle,
                style: TextStyle(
                    color: Colors.white.withOpacity(0.65), fontSize: 12))
            : null,
        value: value,
        activeColor: joviCoral,
        checkColor: Colors.white,
        onChanged: (v) {
          HapticFeedback.selectionClick();
          onChanged(v);
        },
        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
    );
  }

  Widget _buildPrimaryButton(String text,
      {required VoidCallback? onPressed, bool showLoader = false}) {
    final enabled = onPressed != null;
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.975,
      child: Container(
        height: 56,
        width: double.infinity,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          boxShadow: enabled
              ? [
                  BoxShadow(
                      color: joviCoral.withOpacity(0.35),
                      blurRadius: 18,
                      offset: const Offset(0, 8)),
                ]
              : null,
        ),
        child: ElevatedButton(
          onPressed: enabled
              ? () {
                  HapticFeedback.lightImpact();
                  onPressed();
                }
              : null,
          style: ElevatedButton.styleFrom(
            backgroundColor: joviCoral,
            foregroundColor: Colors.white,
            disabledBackgroundColor: joviCoral.withOpacity(0.35),
            disabledForegroundColor: Colors.white.withOpacity(0.7),
            elevation: 0,
            shadowColor: Colors.transparent,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16)),
          ),
          child: showLoader
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white))
              : Text(text,
                  style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                      letterSpacing: -0.3)),
        ),
      ),
    );
  }

  Widget _buildSecondaryButton(String text,
      {required VoidCallback? onPressed}) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.975,
      child: SizedBox(
        height: 56,
        width: double.infinity,
        child: ElevatedButton(
          onPressed: onPressed == null
              ? null
              : () {
                  HapticFeedback.lightImpact();
                  onPressed();
                },
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.white.withOpacity(0.08),
            foregroundColor: Colors.white.withOpacity(0.85),
            disabledBackgroundColor: Colors.white.withOpacity(0.04),
            disabledForegroundColor: Colors.white.withOpacity(0.35),
            elevation: 0,
            shadowColor: Colors.transparent,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(
                    color: Colors.white.withOpacity(0.18), width: 1)),
          ),
          child: Text(text,
              style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.3)),
        ),
      ),
    );
  }

  Widget _buildAgeIndicator(int age) {
    return Container(
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
          color: joviCoral.withOpacity(0.1),
          borderRadius: BorderRadius.circular(12)),
      child: Row(children: [
        Icon(Icons.cake, color: joviCoral),
        SizedBox(width: 8),
        Text('Age: $age years',
            style: TextStyle(fontWeight: FontWeight.w600, color: Colors.white))
      ]),
    );
  }

  Widget _buildSpouseSection() {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
      child: Column(children: [
        _buildCheckbox('Include Spouse', _spouse,
            icon: Icons.favorite,
            onChanged: (v) => setState(() {
                  _spouse = v!;
                  _computeQuote();
                })),
        if (_spouse) ...[
          SizedBox(height: 20),
          _buildAvatarPicker(
              bytes: _spouseBytes,
              url: _spousePhoto,
              onTap: () => _pickAndSetPhoto(forSpouse: true),
              title: 'Spouse Photo'),
          SizedBox(height: 16),
          if (layoutSettings.useTwoColumnLayout)
            Row(children: [
              Expanded(
                  child: _buildTextField(
                      _spouseFirst, 'Spouse First Name', Icons.person)),
              SizedBox(width: 12),
              Expanded(
                  child: _buildTextField(
                      _spouseLast, 'Spouse Last Name', Icons.person_outline)),
            ])
          else
            Column(children: [
              _buildTextField(_spouseFirst, 'Spouse First Name', Icons.person),
              SizedBox(height: 16),
              _buildTextField(
                  _spouseLast, 'Spouse Last Name', Icons.person_outline),
            ]),
          SizedBox(height: 16),
          _buildDateField(_spouseBirth, 'Spouse Date of Birth'),
        ],
      ]),
    );
  }

  Widget _buildDependentsSection() {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.child_care, color: joviCoral),
          SizedBox(width: 8),
          Text('Dependents',
              style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Colors.white))
        ]),
        SizedBox(height: 16),
        _buildDropdown(
            value: _numDeps,
            label: 'Number of Dependents',
            items: List.generate(
                6,
                (i) => DropdownMenuItem(
                    value: i,
                    child: Text('$i ${i == 1 ? "Dependent" : "Dependents"}'))),
            onChanged: (v) => setState(() {
                  _numDeps = v!;
                  _computeQuote();
                })),
        for (var i = 0; i < _numDeps; i++) ...[
          SizedBox(height: 20),
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.04),
              borderRadius: BorderRadius.circular(12),
              border:
                  Border.all(color: Colors.white.withOpacity(0.08), width: 1),
            ),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Dependent ${i + 1}',
                  style: TextStyle(
                      fontWeight: FontWeight.w600, color: Colors.white)),
              SizedBox(height: 12),
              if (layoutSettings.useTwoColumnLayout)
                Row(children: [
                  Expanded(
                      child: _buildTextField(
                          _depFirst[i], 'First Name', Icons.child_friendly)),
                  SizedBox(width: 12),
                  Expanded(
                      child: _buildTextField(
                          _depLast[i], 'Last Name', Icons.child_friendly)),
                ])
              else
                Column(children: [
                  _buildTextField(
                      _depFirst[i], 'First Name', Icons.child_friendly),
                  SizedBox(height: 12),
                  _buildTextField(
                      _depLast[i], 'Last Name', Icons.child_friendly),
                ]),
              SizedBox(height: 12),
              _buildDateField(_depBirth[i], 'Date of Birth'),
            ]),
          ),
        ],
      ]),
    );
  }

  Widget _buildCoverageOptions() {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.health_and_safety, color: joviCoral),
          SizedBox(width: 8),
          Text('Plan Options',
              style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Colors.white))
        ]),
        SizedBox(height: 16),
        _buildCheckbox('Tobacco/Marijuana Use', _tobacco,
            subtitle: 'Check if you or your spouse use tobacco or marijuana',
            icon: Icons.smoking_rooms,
            onChanged: (v) => setState(() {
                  _tobacco = v!;
                  _computeQuote();
                })),
        SizedBox(height: 12),
        _buildCheckbox('Dental Sharing', _dental,
            subtitle: '+\$35/month per person',
            icon: Icons.emoji_emotions,
            onChanged: (v) => setState(() {
                  _dental = v!;
                  _computeQuote();
                })),
        SizedBox(height: 12),
        _buildCheckbox('Vision Sharing', _vision,
            subtitle: '+\$15/month per person',
            icon: Icons.visibility,
            onChanged: (v) => setState(() {
                  _vision = v!;
                  _computeQuote();
                })),
      ]),
    );
  }
  // ============================================================
  // PART 9 OF 10 - Pet Insurance Section, Quote Summary, Payment Form, Promo Codes
  // ============================================================

  Widget _buildPetInsuranceSection() {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.pets, color: joviCoral),
          SizedBox(width: 8),
          Expanded(
              child: Text('Pet Sharing',
                  style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: Colors.white))),
          TextButton.icon(
              onPressed: _showPetCoverageDialog,
              icon: Icon(Icons.info_outline, size: 18),
              label: Text('Details'),
              style: TextButton.styleFrom(foregroundColor: joviCoral)),
        ]),
        SizedBox(height: 8),
        Container(
          padding: EdgeInsets.all(12),
          decoration: BoxDecoration(
              color: joviMint.withOpacity(0.15),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: joviMint.withOpacity(0.4), width: 1)),
          child: Row(children: [
            Icon(Icons.check_circle, color: joviMint, size: 20),
            SizedBox(width: 8),
            Expanded(
                child: Text(
                    'Accident + Illness • 90% Reimbursement • \$500 Deductible',
                    style: TextStyle(
                        color: joviMint,
                        fontSize: 12,
                        fontWeight: FontWeight.w600))),
          ]),
        ),
        SizedBox(height: 16),
        _buildDropdown(
            value: _numPets,
            label: 'Number of Pets',
            items: List.generate(
                5,
                (i) => DropdownMenuItem(
                    value: i, child: Text('$i ${i == 1 ? "Pet" : "Pets"}'))),
            onChanged: (v) {
              final oldCount = _numPets;
              setState(() {
                _numPets = v!;
                for (int idx = 0; idx < _numPets; idx++)
                  _ensurePetListsForIndex(idx);
                _computeQuote();
              });
              for (int idx = oldCount; idx < _numPets; idx++) {
                if (idx < _petAnimControllers.length) {
                  _petAnimControllers[idx]?.reset();
                  _petAnimControllers[idx]?.forward();
                }
              }
            }),
        if (_numPets == 0) _buildPetEmptyState(),
        for (var i = 0; i < _numPets; i++) ...[
          SizedBox(height: 20),
          _buildAnimatedPetCard(i)
        ],
        if (_petTotalPremium > 0) ...[
          SizedBox(height: 16),
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [
                joviCoral.withOpacity(0.1),
                joviGold.withOpacity(0.1)
              ]),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: joviCoral),
            ),
            child: Row(children: [
              Icon(Icons.pets, color: joviCoral, size: 24),
              SizedBox(width: 12),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    Text('Total Pet Sharing',
                        style: TextStyle(
                            fontSize: 14,
                            color: Colors.white.withOpacity(0.75))),
                    Text('\$${_petTotalPremium.toStringAsFixed(2)}/month',
                        style: TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.bold,
                            color: Colors.white)),
                  ])),
            ]),
          ),
        ],
      ]),
    );
  }

  Widget _buildPetEmptyState() {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 32),
      child: Center(
          child: Column(children: [
        Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
              color: joviCoral.withOpacity(0.08), shape: BoxShape.circle),
          child: Stack(alignment: Alignment.center, children: [
            Icon(Icons.pets, size: 48, color: joviCoral.withOpacity(0.4)),
            Positioned(
                bottom: 18,
                right: 18,
                child: Icon(Icons.pets,
                    size: 22, color: joviCoral.withOpacity(0.25))),
            Positioned(
                top: 18,
                left: 20,
                child: Icon(Icons.pets,
                    size: 18, color: joviCoral.withOpacity(0.2))),
          ]),
        ),
        SizedBox(height: 16),
        Text('Add your first furry family member',
            style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Colors.white)),
        SizedBox(height: 6),
        Text(
            'Select the number of pets above to get started\nwith affordable accident & illness coverage.',
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: 13,
                color: Colors.white.withOpacity(0.5),
                height: 1.4)),
      ])),
    );
  }

  Widget _buildAnimatedPetCard(int i) {
    _ensurePetListsForIndex(i);
    final anim = i < _petAnimations.length ? _petAnimations[i] : null;
    Widget card;
    final isComplete = _isPetCardComplete(i);
    final isExpanded = i < _petCardExpanded.length ? _petCardExpanded[i] : true;
    if (isComplete && !isExpanded)
      card = _buildPetSummaryCard(i);
    else
      card = _buildPetFullCard(i);
    if (anim != null)
      return FadeTransition(
          opacity:
              anim is Animation<double> ? anim : AlwaysStoppedAnimation(1.0),
          child: SizeTransition(
              sizeFactor: anim is Animation<double>
                  ? anim
                  : AlwaysStoppedAnimation(1.0),
              axisAlignment: -1.0,
              child: card));
    return card;
  }

  Widget _buildPetSummaryCard(int i) {
    final name = i < _petName.length ? _petName[i].text : 'Pet ${i + 1}';
    final type = i < _petType.length ? _petType[i] : 'Dog';
    final breed = i < _petBreed.length ? _petBreed[i] : '';
    final ageLabel = _getPetAgeLabel(i);
    final ageText = i < _petAge.length ? _petAge[i].text : '';
    final months = _parseAgeToMonths(ageText);
    final premium = _calculatePetPremium(months);
    final Uint8List? bytes =
        i < _petPhotoBytes.length ? _petPhotoBytes[i] : null;
    final String url = i < _petPhotoUrls.length ? _petPhotoUrls[i] : '';
    return Container(
      padding: EdgeInsets.all(14),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.08),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: joviCoral.withOpacity(0.35), width: 1),
          boxShadow: [
            BoxShadow(
                color: joviCoral.withOpacity(0.12),
                blurRadius: 10,
                offset: Offset(0, 3))
          ]),
      child: Row(children: [
        Container(
            width: 54,
            height: 54,
            decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: joviCoral, width: 2)),
            child: ClipOval(
                child: bytes != null
                    ? Image.memory(bytes, fit: BoxFit.cover)
                    : url.isNotEmpty
                        ? Image.network(url, fit: BoxFit.cover)
                        : Container(
                            color: joviCoral.withOpacity(0.18),
                            child:
                                Icon(Icons.pets, color: joviCoral, size: 22)))),
        SizedBox(width: 12),
        Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Flexible(
                child: Text(name.isNotEmpty ? name : 'Pet ${i + 1}',
                    style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                        color: Colors.white),
                    overflow: TextOverflow.ellipsis)),
            if (ageLabel.isNotEmpty) ...[
              SizedBox(width: 8),
              Container(
                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                      color: joviCoral.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color: joviCoral.withOpacity(0.35), width: 1)),
                  child: Text(ageLabel,
                      style: TextStyle(
                          fontSize: 11,
                          color: joviCoralLight,
                          fontWeight: FontWeight.w600)))
            ],
          ]),
          SizedBox(height: 3),
          Text(
              '$type${breed.isNotEmpty ? ' • $breed' : ''}${ageText.isNotEmpty ? ' • $ageText' : ''}',
              style:
                  TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.6)),
              overflow: TextOverflow.ellipsis),
        ])),
        SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('\$${premium.toStringAsFixed(2)}',
              style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                  color: Colors.white)),
          Text('/month',
              style: TextStyle(
                  fontSize: 10, color: Colors.white.withOpacity(0.5))),
        ]),
        SizedBox(width: 6),
        InkWell(
            onTap: () => setState(() => _petCardExpanded[i] = true),
            borderRadius: BorderRadius.circular(20),
            child: Container(
                padding: EdgeInsets.all(6),
                decoration: BoxDecoration(
                    color: joviCoral.withOpacity(0.2),
                    shape: BoxShape.circle,
                    border: Border.all(
                        color: joviCoral.withOpacity(0.35), width: 1)),
                child: Icon(Icons.edit, size: 16, color: joviCoralLight))),
      ]),
    );
  }

  Widget _buildPetFullCard(int i) {
    return Container(
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: joviCoral.withOpacity(0.25))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.pets, color: joviCoral, size: 20),
          SizedBox(width: 8),
          Expanded(
              child: Text('Pet ${i + 1}',
                  style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                      fontSize: 16))),
          if (_isPetCardComplete(i))
            TextButton.icon(
                onPressed: () => setState(() => _petCardExpanded[i] = false),
                icon: Icon(Icons.check_circle, size: 16),
                label: Text('Done', style: TextStyle(fontSize: 12)),
                style: TextButton.styleFrom(
                    foregroundColor: joviMint,
                    padding: EdgeInsets.symmetric(horizontal: 8))),
        ]),
        SizedBox(height: 12),
        Center(
            child: _buildPetAvatarPicker(
                petIndex: i,
                title: i < _petName.length && _petName[i].text.isNotEmpty
                    ? '${_petName[i].text}\'s Photo'
                    : 'Pet ${i + 1} Photo')),
        SizedBox(height: 16),
        _buildTextField(_petName[i], 'Pet Name', Icons.badge),
        if (i < _petNameWarnings.length && _petNameWarnings[i] != null)
          Padding(
              padding: EdgeInsets.only(top: 4, left: 12),
              child: Row(children: [
                Icon(Icons.info_outline, size: 14, color: joviGold),
                SizedBox(width: 4),
                Flexible(
                    child: Text(_petNameWarnings[i]!,
                        style: TextStyle(fontSize: 11, color: joviGold)))
              ])),
        SizedBox(height: 12),
        if (layoutSettings.useTwoColumnLayout)
          Row(children: [
            Expanded(
                child: _buildDropdown<String>(
                    value: i < _petType.length ? _petType[i] : 'Dog',
                    label: 'Type',
                    items: ['Dog', 'Cat']
                        .map((type) =>
                            DropdownMenuItem(value: type, child: Text(type)))
                        .toList(),
                    onChanged: (v) {
                      setState(() {
                        while (_petType.length <= i) _petType.add('Dog');
                        _petType[i] = v!;
                        while (_petBreed.length <= i) _petBreed.add('');
                        _petBreed[i] = '';
                      });
                      _validatePetAge(i);
                      _saveProgressData();
                    },
                    validator: (v) => v == null ? 'Required' : null)),
            SizedBox(width: 12),
            Expanded(
                child: _buildDropdown<String>(
                    value: i < _petGender.length ? _petGender[i] : 'Male',
                    label: 'Gender',
                    items: ['Male', 'Female']
                        .map((gender) => DropdownMenuItem(
                            value: gender, child: Text(gender)))
                        .toList(),
                    onChanged: (v) {
                      setState(() {
                        while (_petGender.length <= i) _petGender.add('Male');
                        _petGender[i] = v!;
                      });
                      _saveProgressData();
                    },
                    validator: (v) => v == null ? 'Required' : null)),
          ])
        else
          Column(children: [
            _buildDropdown<String>(
                value: i < _petType.length ? _petType[i] : 'Dog',
                label: 'Type',
                items: ['Dog', 'Cat']
                    .map((type) =>
                        DropdownMenuItem(value: type, child: Text(type)))
                    .toList(),
                onChanged: (v) {
                  setState(() {
                    while (_petType.length <= i) _petType.add('Dog');
                    _petType[i] = v!;
                    while (_petBreed.length <= i) _petBreed.add('');
                    _petBreed[i] = '';
                  });
                  _validatePetAge(i);
                  _saveProgressData();
                },
                validator: (v) => v == null ? 'Required' : null),
            SizedBox(height: 12),
            _buildDropdown<String>(
                value: i < _petGender.length ? _petGender[i] : 'Male',
                label: 'Gender',
                items: ['Male', 'Female']
                    .map((gender) =>
                        DropdownMenuItem(value: gender, child: Text(gender)))
                    .toList(),
                onChanged: (v) {
                  setState(() {
                    while (_petGender.length <= i) _petGender.add('Male');
                    _petGender[i] = v!;
                  });
                  _saveProgressData();
                },
                validator: (v) => v == null ? 'Required' : null),
          ]),
        SizedBox(height: 12),
        _buildSearchableBreedDropdown(
            value: i < _petBreed.length ? _petBreed[i] : null,
            label: 'Breed',
            breeds: i < _petType.length && _petType[i] == 'Cat'
                ? catBreeds
                : dogBreeds,
            onChanged: (v) {
              setState(() {
                while (_petBreed.length <= i) _petBreed.add('');
                _petBreed[i] = v ?? '';
              });
              _validatePetAge(i);
              _saveProgressData();
            },
            validator: (v) => (v == null || v.isEmpty) ? 'Required' : null),
        SizedBox(height: 16),
        Container(
          padding: EdgeInsets.all(12),
          decoration: BoxDecoration(
              color: joviCoral.withOpacity(0.04),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: joviCoral.withOpacity(0.15))),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Pet Birthdate',
                style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Colors.white)),
            SizedBox(height: 8),
            Row(children: [
              Expanded(
                  child: TextFormField(
                      controller: i < _petBirthdate.length
                          ? _petBirthdate[i]
                          : TextEditingController(),
                      readOnly: true,
                      style: TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                          hintText: 'MM/DD/YYYY',
                          prefixIcon: Icon(Icons.calendar_today,
                              color: joviCoral, size: 20),
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10)),
                          enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: BorderSide(
                                  color: Colors.white.withOpacity(0.15))),
                          focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide:
                                  BorderSide(color: joviCoral, width: 2)),
                          filled: true,
                          fillColor: Colors.white.withOpacity(0.06),
                          labelStyle:
                              TextStyle(color: Colors.white.withOpacity(0.7)),
                          hintStyle:
                              TextStyle(color: Colors.white.withOpacity(0.4)),
                          contentPadding: EdgeInsets.symmetric(
                              vertical: 12, horizontal: 12)),
                      onTap: () => _pickPetBirthdate(i))),
              SizedBox(width: 8),
              ElevatedButton.icon(
                  onPressed: () => _pickPetBirthdate(i),
                  icon: Icon(Icons.cake, size: 18),
                  label: Text('Pick Date'),
                  style: ElevatedButton.styleFrom(
                      backgroundColor: joviCoral,
                      foregroundColor: Colors.white,
                      padding:
                          EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10)))),
            ]),
            SizedBox(height: 8),
            if (i < _petAge.length && _petAge[i].text.isNotEmpty)
              Container(
                  padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                      color: joviMint.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                          color: joviMint.withOpacity(0.4), width: 1)),
                  child: Row(children: [
                    Icon(Icons.auto_awesome, size: 16, color: joviMint),
                    SizedBox(width: 6),
                    Expanded(
                        child: RichText(
                            text: TextSpan(
                                style: TextStyle(
                                    fontSize: 13,
                                    color: Colors.white.withOpacity(0.85)),
                                children: [
                          TextSpan(
                              text: 'Age: ',
                              style: TextStyle(fontWeight: FontWeight.w600)),
                          TextSpan(text: '${_petAge[i].text}'),
                          if (_getPetAgeLabel(i).isNotEmpty) ...[
                            TextSpan(text: '  '),
                            TextSpan(
                                text: _getPetAgeLabel(i),
                                style: TextStyle(
                                    fontWeight: FontWeight.w600,
                                    color: joviCoral))
                          ]
                        ])))
                  ]))
            else
              Text('Or enter age manually below if birthdate is unknown',
                  style: TextStyle(
                      fontSize: 11,
                      color: Colors.white.withOpacity(0.5),
                      fontStyle: FontStyle.italic)),
          ]),
        ),
        SizedBox(height: 12),
        TextFormField(
            controller: _petAge[i],
            style: TextStyle(color: Colors.white),
            decoration: InputDecoration(
                labelText: 'Age (e.g., "2 months", "3 years 5 months")',
                labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
                prefixIcon: Icon(Icons.cake, color: joviCoral),
                border:
                    OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.15))),
                focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: joviCoral, width: 2)),
                filled: true,
                fillColor: Colors.white.withOpacity(0.06)),
            onChanged: (value) {
              _validatePetAge(i);
              _validatePetName(i);
              _computeQuote();
              _saveProgressData();
            },
            validator: (v) => v!.isEmpty ? 'This field is required' : null),
        SizedBox(height: 4),
        Text('Minimum age: 8 weeks (2 months) • Maximum age: 20 years',
            style: TextStyle(
                fontSize: 11,
                color: Colors.white.withOpacity(0.65),
                fontStyle: FontStyle.italic)),
        if (i < _petAgeWarnings.length && _petAgeWarnings[i] != null)
          Padding(
              padding: EdgeInsets.only(top: 6),
              child: Container(
                  padding: EdgeInsets.all(8),
                  decoration: BoxDecoration(
                      color: joviGold.withOpacity(0.14),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                          color: joviGold.withOpacity(0.4), width: 1)),
                  child: Row(children: [
                    Icon(Icons.warning_amber, size: 18, color: joviGold),
                    SizedBox(width: 6),
                    Flexible(
                        child: Text(_petAgeWarnings[i]!,
                            style: TextStyle(fontSize: 12, color: joviGold)))
                  ]))),
        if (_petAge[i].text.isNotEmpty) ...[
          SizedBox(height: 12),
          Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                  color: joviCoral.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8)),
              child: Row(children: [
                Icon(Icons.monetization_on, color: joviCoral, size: 20),
                SizedBox(width: 8),
                Expanded(
                    child: Text(
                        'Monthly Contribution: \$${_calculatePetPremium(_parseAgeToMonths(_petAge[i].text)).toStringAsFixed(2)}',
                        style: TextStyle(
                            fontWeight: FontWeight.w600, color: Colors.white)))
              ])),
        ],
        SizedBox(height: 16),
        _buildPetCoverageAccordion(i),
        SizedBox(height: 16),
        _buildPreExistingConditionSection(i),
      ]),
    );
  }

  Widget _buildPetCoverageAccordion(int i) {
    while (_petCoverageExpanded.length <= i) _petCoverageExpanded.add(false);
    final isExpanded = _petCoverageExpanded[i];
    final type = i < _petType.length ? _petType[i] : 'Dog';
    return Container(
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
      child: Column(children: [
        InkWell(
            onTap: () {
              HapticFeedback.lightImpact();
              setState(
                  () => _petCoverageExpanded[i] = !_petCoverageExpanded[i]);
            },
            borderRadius: BorderRadius.circular(10),
            child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                child: Row(children: [
                  Icon(Icons.shield_outlined, size: 20, color: joviCoral),
                  SizedBox(width: 8),
                  Expanded(
                      child: Text(
                          "What's Shared for ${i < _petName.length && _petName[i].text.isNotEmpty ? _petName[i].text : 'this pet'}",
                          style: TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 14,
                              color: Colors.white))),
                  AnimatedRotation(
                      turns: isExpanded ? 0.5 : 0,
                      duration: _reduceMotion
                          ? Duration.zero
                          : const Duration(milliseconds: 220),
                      curve: _Motion.settle,
                      child: Icon(Icons.keyboard_arrow_down, color: joviCoral)),
                ]))),
        AnimatedCrossFade(
          firstChild: SizedBox.shrink(),
          secondChild: Padding(
              padding: EdgeInsets.only(left: 14, right: 14, bottom: 14),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Divider(height: 1, color: Colors.white.withOpacity(0.1)),
                    SizedBox(height: 12),
                    _buildAccordionCategory(
                        '🩺 Accidents',
                        [
                          'Broken bones & fractures',
                          'Toxic ingestion & poisoning',
                          'Cuts, lacerations & bite wounds',
                          'Emergency vet visits',
                          'Swallowed foreign objects'
                        ],
                        joviMint),
                    SizedBox(height: 10),
                    _buildAccordionCategory(
                        '💊 Illnesses',
                        [
                          'Cancer diagnosis & treatment',
                          'Diabetes management',
                          'Allergies & skin conditions',
                          'Digestive disorders',
                          type == 'Dog'
                              ? 'Hip dysplasia & joint conditions'
                              : 'Urinary tract conditions',
                          'Chronic conditions (arthritis, etc.)'
                        ],
                        const Color(0xFF7CB8FF)),
                    SizedBox(height: 10),
                    _buildAccordionCategory(
                        '🏥 Vet Services',
                        [
                          'Exam fees',
                          'Diagnostics (bloodwork, X-rays, MRI, CT)',
                          'Surgery & hospitalization',
                          'Prescription medications',
                          'Specialist referrals'
                        ],
                        const Color(0xFFA78BFA)),
                    SizedBox(height: 10),
                    _buildAccordionCategory(
                        '🦷 Dental',
                        [
                          'Dental illness treatment',
                          'Trauma-related dental work'
                        ],
                        joviGold),
                    SizedBox(height: 10),
                    _buildAccordionCategory(
                        '💉 Prescriptions',
                        [
                          'Prescription medications',
                          'Prescription therapeutic diets',
                          'Compounding pharmacy'
                        ],
                        joviCoralLight),
                    SizedBox(height: 14),
                    Container(
                        padding: EdgeInsets.all(10),
                        decoration: BoxDecoration(
                            color: joviCoral.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                                color: joviCoral.withOpacity(0.35), width: 1)),
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Not Shared:',
                                  style: TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 12,
                                      color: joviCoralLight)),
                              SizedBox(height: 4),
                              Text(
                                  'Pre-existing conditions (curable conditions eligible after 180 days) • Cosmetic procedures • Breeding costs • Preventive/wellness care (available as add-on)',
                                  style: TextStyle(
                                      fontSize: 11, color: joviCoralLight)),
                            ])),
                    SizedBox(height: 10),
                    Container(
                        padding: EdgeInsets.all(10),
                        decoration: BoxDecoration(
                            color: joviGold.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                                color: joviGold.withOpacity(0.4), width: 1)),
                        child: Row(children: [
                          Icon(Icons.timer, size: 16, color: joviGold),
                          SizedBox(width: 6),
                          Expanded(
                              child: Text(
                                  'Waiting periods: 14 days for accidents • 30 days for illnesses • 6 months for orthopedic (dogs)',
                                  style:
                                      TextStyle(fontSize: 11, color: joviGold)))
                        ])),
                  ])),
          crossFadeState:
              isExpanded ? CrossFadeState.showSecond : CrossFadeState.showFirst,
          duration: _reduceMotion
              ? Duration.zero
              : const Duration(milliseconds: 260),
          sizeCurve: _Motion.settle,
        ),
      ]),
    );
  }

  Widget _buildAccordionCategory(
      String title, List<String> items, Color color) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(title,
          style: TextStyle(
              fontWeight: FontWeight.w700, fontSize: 13, color: color)),
      SizedBox(height: 4),
      ...items.map((item) => Padding(
          padding: EdgeInsets.only(left: 6, bottom: 2),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.check, size: 14, color: color.withOpacity(0.85)),
            SizedBox(width: 4),
            Flexible(
                child: Text(item,
                    style: TextStyle(
                        fontSize: 12, color: Colors.white.withOpacity(0.75))))
          ]))),
    ]);
  }

  Widget _buildPreExistingConditionSection(int i) {
    _ensurePetListsForIndex(i);
    final isAcked =
        i < _petPreExistingAck.length ? _petPreExistingAck[i] : false;
    return Container(
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
          color: joviGold.withOpacity(0.12),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: joviGold.withOpacity(0.35), width: 1)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.medical_information, size: 18, color: joviGold),
          SizedBox(width: 6),
          Expanded(
              child: Text('Pre-Existing Conditions',
                  style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                      color: joviGold)))
        ]),
        SizedBox(height: 8),
        Text(
            'Does ${i < _petName.length && _petName[i].text.isNotEmpty ? _petName[i].text : 'this pet'} have any pre-existing conditions, prior diagnoses, or ongoing treatments?',
            style:
                TextStyle(fontSize: 12, color: Colors.white.withOpacity(0.75))),
        SizedBox(height: 8),
        Row(children: [
          SizedBox(
              width: 24,
              height: 24,
              child: Checkbox(
                  value: isAcked,
                  activeColor: joviCoral,
                  onChanged: (v) {
                    setState(() {
                      while (_petPreExistingAck.length <= i)
                        _petPreExistingAck.add(false);
                      _petPreExistingAck[i] = v ?? false;
                    });
                    _saveProgressData();
                  })),
          SizedBox(width: 8),
          Expanded(
              child: Text('Yes, my pet has pre-existing conditions',
                  style: TextStyle(
                      fontSize: 12, color: Colors.white.withOpacity(0.85))))
        ]),
        if (isAcked) ...[
          SizedBox(height: 10),
          TextFormField(
              controller: i < _petPreExistingControllers.length
                  ? _petPreExistingControllers[i]
                  : TextEditingController(),
              maxLines: 3,
              style: TextStyle(color: Colors.white),
              decoration: InputDecoration(
                  hintText:
                      'Please describe any conditions, diagnoses, or treatments...',
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8)),
                  enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide(color: joviGold.withOpacity(0.3))),
                  focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide(color: joviCoral, width: 2)),
                  filled: true,
                  fillColor: Colors.white.withOpacity(0.08),
                  hintStyle: TextStyle(
                      color: Colors.white.withOpacity(0.4), fontSize: 12),
                  contentPadding: EdgeInsets.all(10)),
              onChanged: (v) => _saveProgressData()),
          SizedBox(height: 8),
          Container(
              padding: EdgeInsets.all(8),
              decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                      color: Colors.white.withOpacity(0.12), width: 1)),
              child: Row(children: [
                Icon(Icons.info_outline, size: 14, color: joviCoralLight),
                SizedBox(width: 6),
                Flexible(
                    child: Text(
                        'Pre-existing conditions are generally not eligible for sharing. However, curable conditions that remain symptom-free for 180 days may become eligible.',
                        style: TextStyle(
                            fontSize: 11,
                            color: Colors.white.withOpacity(0.8))))
              ])),
        ] else ...[
          SizedBox(height: 6),
          Text('If none, no action needed — your pet is all set!',
              style: TextStyle(
                  fontSize: 11,
                  color: Colors.white.withOpacity(0.5),
                  fontStyle: FontStyle.italic)),
        ],
      ]),
    );
  }

  Widget _buildQuoteSummary() {
    final grandTotal = _totalPremium + _petTotalPremium;
    return Container(
      padding: EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: LinearGradient(
            colors: [joviCoral, joviCoralLight, joviNavy],
            stops: [0.0, 0.5, 1.0],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
              color: joviCoral.withOpacity(0.35),
              blurRadius: 24,
              offset: Offset(0, 10))
        ],
      ),
      child: Column(children: [
        Row(children: [
          Icon(Icons.receipt_long, color: Colors.white, size: 28),
          SizedBox(width: 12),
          Text('Your Plan Summary',
              style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.white))
        ]),
        SizedBox(height: 20),
        if (_quotes.isNotEmpty)
          Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12)),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Icon(Icons.people, color: Colors.white70, size: 18),
                      SizedBox(width: 8),
                      Text('Health Sharing',
                          style: TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w600))
                    ]),
                    SizedBox(height: 12),
                    for (var q in _quotes) ...[
                      _buildQuoteLineItem(
                          '${q['name']} (Age ${q['age']})',
                          q['basePremium'] is double
                              ? q['basePremium']
                              : (q['basePremium'] as num).toDouble(),
                          icon: Icons.person),
                      if (q['hasTobacco'] == true)
                        _buildQuoteSubItem('Tobacco surcharge (15%)',
                            (q['basePremium'] as num).toDouble() * 0.15),
                      if (q['hasDental'] == true)
                        _buildQuoteSubItem('Dental sharing', 35.0),
                      if (q['hasVision'] == true)
                        _buildQuoteSubItem('Vision sharing', 15.0),
                      SizedBox(height: 4),
                    ],
                    Divider(
                        color: Colors.white.withOpacity(0.3), thickness: 0.5),
                    SizedBox(height: 4),
                    Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Health sharing subtotal',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600)),
                          Text('\$${_totalPremium.toStringAsFixed(2)}/mo',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold))
                        ]),
                  ])),
        if (_petQuotes.isNotEmpty) ...[
          SizedBox(height: 12),
          Container(
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(12)),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Icon(Icons.pets, color: Colors.white70, size: 18),
                      SizedBox(width: 8),
                      Text('Pet Sharing',
                          style: TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w600))
                    ]),
                    SizedBox(height: 12),
                    for (var pq in _petQuotes) ...[
                      _buildQuoteLineItem(
                          '${pq['name'].toString().isNotEmpty ? pq['name'] : 'Pet'} (${pq['type']}${pq['breed'].toString().isNotEmpty ? ' - ${pq['breed']}' : ''})',
                          (pq['premium'] as num).toDouble(),
                          icon: Icons.pets),
                      _buildQuoteSubItem(
                          '90% reimbursement • \$500 out-of-pocket', null),
                      SizedBox(height: 4),
                    ],
                    Divider(
                        color: Colors.white.withOpacity(0.3), thickness: 0.5),
                    SizedBox(height: 4),
                    Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Pet sharing subtotal',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600)),
                          Text('\$${_petTotalPremium.toStringAsFixed(2)}/mo',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold))
                        ]),
                  ]))
        ],
        if (_discountAmount > 0) ...[
          SizedBox(height: 12),
          Container(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                  color: joviMint.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(10),
                  border:
                      Border.all(color: joviMint.withOpacity(0.4), width: 1)),
              child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(children: [
                      Icon(Icons.local_offer, color: joviMint, size: 18),
                      SizedBox(width: 8),
                      Text(
                          'Discount${_promoCodeApplied.isNotEmpty ? ' ($_promoCodeApplied)' : ''}',
                          style: TextStyle(
                              color: joviMint,
                              fontSize: 14,
                              fontWeight: FontWeight.w600))
                    ]),
                    Text('-\$${_discountAmount.toStringAsFixed(2)}',
                        style: TextStyle(
                            color: joviMint,
                            fontSize: 16,
                            fontWeight: FontWeight.w600))
                  ]))
        ],
        SizedBox(height: 16),
        Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white.withOpacity(0.3))),
            child: Column(children: [
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text('Total Monthly Plan',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w600)),
                Text('\$${grandTotal.toStringAsFixed(2)}',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.bold))
              ]),
              SizedBox(height: 8),
              Divider(color: Colors.white.withOpacity(0.3)),
              SizedBox(height: 8),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text('Your Responsibility (Health)',
                    style: TextStyle(color: Colors.white70, fontSize: 14)),
                Text(
                    '\$${_quotes.isNotEmpty ? _quotes.first['deductible'] : 0}',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600))
              ]),
              if (_petQuotes.isNotEmpty) ...[
                SizedBox(height: 4),
                Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                          'Out-of-Pocket (Pet)${_numPets > 1 ? ' (each)' : ''}',
                          style:
                              TextStyle(color: Colors.white70, fontSize: 14)),
                      Text('\$500',
                          style: TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w600))
                    ])
              ],
              SizedBox(height: 4),
              Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                Text('Plan Type',
                    style: TextStyle(color: Colors.white70, fontSize: 14)),
                Text((_spouse || _numDeps > 0) ? 'Family' : 'Individual',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600))
              ]),
            ])),
      ]),
    );
  }

  Widget _buildQuoteLineItem(String label, double amount, {IconData? icon}) {
    return Padding(
        padding: EdgeInsets.only(bottom: 2),
        child:
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Flexible(
              flex: 3,
              child: Row(children: [
                if (icon != null) ...[
                  Icon(icon, color: Colors.white60, size: 14),
                  SizedBox(width: 6)
                ],
                Flexible(
                    child: Text(label,
                        style: TextStyle(color: Colors.white, fontSize: 14),
                        overflow: TextOverflow.ellipsis))
              ])),
          Flexible(
              flex: 1,
              child: Text('\$${amount.toStringAsFixed(2)}',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.w600),
                  textAlign: TextAlign.right))
        ]));
  }

  Widget _buildQuoteSubItem(String label, double? amount) {
    return Padding(
        padding: EdgeInsets.only(left: 20, bottom: 2),
        child:
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          Flexible(
              flex: 3,
              child: Text('  + $label',
                  style: TextStyle(
                      color: Colors.white60,
                      fontSize: 12,
                      fontStyle: FontStyle.italic),
                  overflow: TextOverflow.ellipsis)),
          if (amount != null)
            Flexible(
                flex: 1,
                child: Text('+\$${amount.toStringAsFixed(2)}',
                    style: TextStyle(color: Colors.white60, fontSize: 12),
                    textAlign: TextAlign.right))
        ]));
  }

  Widget _buildSecurityBadge() {
    return Container(
        padding: EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: joviMint.withOpacity(0.15),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: joviMint.withOpacity(0.4), width: 1)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.lock, color: joviMint, size: 16),
          SizedBox(width: 8),
          Text('Secure Payment Processing',
              style: TextStyle(color: joviMint, fontWeight: FontWeight.w600))
        ]));
  }

  Widget _buildPaymentForm() {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
      child: Column(children: [
        Row(children: [
          Icon(Icons.account_balance, color: joviCoral, size: 20),
          SizedBox(width: 8),
          Expanded(
              child: Text('Pay by bank account (ACH)',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w600))),
        ]),
        SizedBox(height: 6),
        Text(
            'Your monthly membership is debited from this account. Verification can take up to two business days.',
            style: TextStyle(
                color: Colors.white.withOpacity(0.6), fontSize: 12.5)),
        SizedBox(height: 16),
        _buildTextField(_acctName, 'Name on Account', Icons.person_outline),
        SizedBox(height: 16),
        TextFormField(
            controller: _routing,
            keyboardType: TextInputType.number,
            style: TextStyle(color: Colors.white),
            decoration: InputDecoration(
                labelText: 'Routing Number',
                hintText: '9 digits',
                labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
                prefixIcon: Icon(Icons.account_balance, color: joviCoral),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.15))),
                enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.15))),
                focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: joviCoral, width: 2)),
                filled: true,
                fillColor: Colors.white.withOpacity(0.06)),
            validator: (v) => RegExp(r'^\d{9}$').hasMatch(v ?? '')
                ? null
                : 'Routing number is 9 digits'),
        SizedBox(height: 16),
        TextFormField(
            controller: _account,
            keyboardType: TextInputType.number,
            obscureText: true,
            style: TextStyle(color: Colors.white),
            decoration: InputDecoration(
                labelText: 'Account Number',
                hintText: '4 to 17 digits',
                labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
                prefixIcon: Icon(Icons.numbers, color: joviCoral),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.15))),
                enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.15))),
                focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: joviCoral, width: 2)),
                filled: true,
                fillColor: Colors.white.withOpacity(0.06)),
            validator: (v) => RegExp(r'^\d{4,17}$').hasMatch(v ?? '')
                ? null
                : 'Enter your account number'),
        SizedBox(height: 12),
        Row(children: [
          for (final type in const ['CHECKING', 'SAVINGS'])
            Padding(
              padding: const EdgeInsets.only(right: 10),
              child: ChoiceChip(
                label: Text(type == 'CHECKING' ? 'Checking' : 'Savings'),
                selected: _acctType == type,
                selectedColor: joviCoral,
                backgroundColor: Colors.white.withOpacity(0.08),
                labelStyle: TextStyle(
                    color: _acctType == type
                        ? Colors.white
                        : Colors.white.withOpacity(0.7),
                    fontWeight: FontWeight.w600),
                onSelected: (_) => setState(() => _acctType = type),
              ),
            ),
        ]),
        SizedBox(height: 16),
        Text('Billing Information',
            style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Colors.white)),
        SizedBox(height: 12),
        TextFormField(
            controller: _billingAddress,
            style: TextStyle(color: Colors.white),
            decoration: InputDecoration(
                labelText: 'Billing Address',
                hintText: 'Tap to search...',
                labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
                prefixIcon: Icon(Icons.home, color: joviCoral),
                suffixIcon: IconButton(
                    icon: Icon(Icons.search, color: joviCoral),
                    onPressed: () =>
                        _pickPlace(_billingAddress, isBillingAddress: true)),
                border:
                    OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.15))),
                focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: joviCoral, width: 2)),
                filled: true,
                fillColor: Colors.white.withOpacity(0.06)),
            onTap: () => _pickPlace(_billingAddress, isBillingAddress: true),
            validator: (v) =>
                v!.isEmpty ? 'Billing address is required' : null),
        SizedBox(height: 16),
        if (layoutSettings.useTwoColumnLayout)
          Row(children: [
            Expanded(
                child: _buildTextField(_city, 'City', Icons.location_city)),
            SizedBox(width: 12),
            Expanded(
                child: _buildDropdown<String>(
                    value: _state.text.isNotEmpty ? _state.text : null,
                    label: 'State (CO, AZ & TX only)',
                    items: usStates
                        .map((String state) => DropdownMenuItem<String>(
                            value: state,
                            child: Row(children: [
                              Text(state),
                              if (state == 'CO' ||
                                  state == 'AZ' ||
                                  state == 'TX') ...[
                                SizedBox(width: 8),
                                Icon(Icons.check_circle,
                                    size: 16, color: joviMint)
                              ]
                            ])))
                        .toList(),
                    onChanged: (String? newValue) {
                      if (newValue != null) {
                        if (_isStateAllowed(newValue))
                          setState(() {
                            _state.text = newValue;
                          });
                        else
                          _showComingSoonDialog(newValue);
                      }
                    },
                    validator: (value) {
                      if (value == null || value.isEmpty)
                        return 'Please select a state';
                      if (!_isStateAllowed(value))
                        return 'Service not available in this state';
                      return null;
                    }))
          ])
        else
          Column(children: [
            _buildTextField(_city, 'City', Icons.location_city),
            SizedBox(height: 16),
            _buildDropdown<String>(
                value: _state.text.isNotEmpty ? _state.text : null,
                label: 'State (CO, AZ & TX only)',
                items: usStates
                    .map((String state) => DropdownMenuItem<String>(
                        value: state,
                        child: Row(children: [
                          Text(state),
                          if (state == 'CO' ||
                              state == 'AZ' ||
                              state == 'TX') ...[
                            SizedBox(width: 8),
                            Icon(Icons.check_circle, size: 16, color: joviMint)
                          ]
                        ])))
                    .toList(),
                onChanged: (String? newValue) {
                  if (newValue != null) {
                    if (_isStateAllowed(newValue))
                      setState(() {
                        _state.text = newValue;
                      });
                    else
                      _showComingSoonDialog(newValue);
                  }
                },
                validator: (value) {
                  if (value == null || value.isEmpty)
                    return 'Please select a state';
                  if (!_isStateAllowed(value))
                    return 'Service not available in this state';
                  return null;
                })
          ]),
        SizedBox(height: 16),
        if (layoutSettings.useTwoColumnLayout)
          Row(children: [
            Expanded(
                child: _buildTextField(_zip, 'ZIP Code',
                    Icons.local_post_office, TextInputType.number)),
            SizedBox(width: 12),
            Expanded(child: _buildTextField(_country, 'Country', Icons.flag))
          ])
        else
          Column(children: [
            _buildTextField(_zip, 'ZIP Code', Icons.local_post_office,
                TextInputType.number),
            SizedBox(height: 16),
            _buildTextField(_country, 'Country', Icons.flag)
          ]),
      ]),
    );
  }

  Widget _buildPaymentInfo() {
    final grandTotal = _totalPremium + _petTotalPremium;
    return Container(
        padding: EdgeInsets.all(12),
        decoration: BoxDecoration(
            color: joviCoral.withOpacity(0.1),
            borderRadius: BorderRadius.circular(8)),
        child: Row(children: [
          Icon(Icons.info_outline, color: joviCoral, size: 20),
          SizedBox(width: 8),
          Expanded(
              child: Text(
                  'Your plan contribution of \$${grandTotal.toStringAsFixed(2)} will be billed monthly',
                  style: TextStyle(color: Colors.white, fontSize: 14)))
        ]));
  }

  Widget _buildPromoCodeSection() {
    return Container(
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.07),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.local_offer, color: joviCoral),
          SizedBox(width: 8),
          Text('Discounts & Promotions',
              style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: Colors.white))
        ]),
        SizedBox(height: 16),
        if (_promoCodeApplied.isNotEmpty) ...[
          Container(
              padding: EdgeInsets.all(12),
              decoration: BoxDecoration(
                  color: joviMint.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border:
                      Border.all(color: joviMint.withOpacity(0.4), width: 1)),
              child: Row(children: [
                Icon(Icons.check_circle, color: joviMint, size: 20),
                SizedBox(width: 8),
                Expanded(
                    child: Text('Promo code "$_promoCodeApplied" applied!',
                        style: TextStyle(
                            color: joviMint, fontWeight: FontWeight.w600))),
                TextButton(
                    onPressed: _removePromoCode,
                    child: Text('Remove',
                        style: TextStyle(
                            color: joviCoralLight,
                            fontWeight: FontWeight.w600)))
              ])),
          SizedBox(height: 16),
        ] else ...[
          Row(children: [
            Expanded(
                child: TextFormField(
                    controller: _promoCode,
                    style: TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                        labelText: 'Promo Code',
                        hintText: 'Enter promo code',
                        labelStyle:
                            TextStyle(color: Colors.white.withOpacity(0.7)),
                        hintStyle:
                            TextStyle(color: Colors.white.withOpacity(0.4)),
                        prefixIcon:
                            Icon(Icons.confirmation_number, color: joviCoral),
                        border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(
                                color: Colors.white.withOpacity(0.15))),
                        enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(
                                color: Colors.white.withOpacity(0.15))),
                        focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide(color: joviCoral, width: 2)),
                        filled: true,
                        fillColor: Colors.white.withOpacity(0.06)),
                    onChanged: (value) => _saveProgressData())),
            SizedBox(width: 12),
            ElevatedButton(
                onPressed: _isValidatingPromo ? null : _validatePromoCode,
                style: ElevatedButton.styleFrom(
                    backgroundColor: joviCoral,
                    padding: EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12))),
                child: _isValidatingPromo
                    ? SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2))
                    : Text('Apply', style: TextStyle(color: Colors.white))),
          ]),
          SizedBox(height: 16),
        ],
        TextFormField(
            controller: _referralCode,
            style: TextStyle(color: Colors.white),
            decoration: InputDecoration(
                labelText: 'Referral Code (Optional)',
                hintText: 'Who referred you?',
                labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
                hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
                prefixIcon: Icon(Icons.people, color: joviCoral),
                border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.15))),
                enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide:
                        BorderSide(color: Colors.white.withOpacity(0.15))),
                focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide(color: joviCoral, width: 2)),
                filled: true,
                fillColor: Colors.white.withOpacity(0.06)),
            onChanged: (value) {
              _saveProgressData();
              _applyReferralDiscount();
            }),
      ]),
    );
  }

  // ============================================================
  // PART 10 OF 10 - Confirmation, Onboarding Sections, Completion, Confetti
  // ============================================================

  Widget _buildConfirmationContent() {
    return Container(
      padding: EdgeInsets.all(32),
      decoration: BoxDecoration(
        gradient: LinearGradient(
            colors: [joviCoral, joviCoralLight],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
              color: joviCoral.withOpacity(0.45),
              blurRadius: 40,
              spreadRadius: 2,
              offset: Offset(0, 16)),
          BoxShadow(
              color: joviCoral.withOpacity(0.2),
              blurRadius: 60,
              spreadRadius: -8,
              offset: Offset(0, 28)),
        ],
      ),
      child: Column(children: [
        ScaleTransition(
            scale: Tween<double>(begin: 0.6, end: 1.0).animate(
                CurvedAnimation(parent: _celebrate, curve: _Motion.settle)),
            child: Container(
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.22),
                    borderRadius: BorderRadius.circular(50),
                    border: Border.all(
                        color: Colors.white.withOpacity(0.35), width: 1)),
                child: Icon(Icons.emoji_events,
                    size: 60, color: joviGold))),
        SizedBox(height: 24),
        Text('Payment successful',
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: layoutSettings.wideMode ? 32 : 28,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.6,
                height: 1.1,
                color: Colors.white)),
        SizedBox(height: 12),
        Text('Welcome to Jovi Health!',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, color: Colors.white70)),
        SizedBox(height: 8),
        Text('Your membership is confirmed',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16, color: Colors.white60)),
        SizedBox(height: 32),
        Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.15),
                borderRadius: BorderRadius.circular(12)),
            child: Column(children: [
              Row(children: [
                Icon(Icons.check_circle, color: Colors.white, size: 24),
                SizedBox(width: 12),
                Expanded(
                    child: Text('Payment Processed Successfully',
                        style: TextStyle(color: Colors.white, fontSize: 16)))
              ]),
              SizedBox(height: 8),
              Row(children: [
                Icon(Icons.check_circle, color: Colors.white, size: 24),
                SizedBox(width: 12),
                Expanded(
                    child: Text('Sharing Activated Immediately',
                        style: TextStyle(color: Colors.white, fontSize: 16)))
              ]),
              SizedBox(height: 8),
              Row(children: [
                Icon(Icons.check_circle, color: Colors.white, size: 24),
                SizedBox(width: 12),
                Expanded(
                    child: Text('Welcome Email Sent',
                        style: TextStyle(color: Colors.white, fontSize: 16)))
              ]),
              if (_numPets > 0) ...[
                SizedBox(height: 8),
                Row(children: [
                  Icon(Icons.pets, color: Colors.white, size: 24),
                  SizedBox(width: 12),
                  Expanded(
                      child: Text('Pet Sharing Active',
                          style: TextStyle(color: Colors.white, fontSize: 16)))
                ])
              ],
            ])),
      ]),
    );
  }

  Widget _buildOnboardingPersonalInfo() {
    return Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(16),
            border:
                Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.person, color: joviCoral),
            SizedBox(width: 8),
            Text('Personal Information',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.white))
          ]),
          SizedBox(height: 16),
          _buildTextField(_fullName, 'Full Legal Name', Icons.badge),
          SizedBox(height: 16),
          _buildDateField(_dobOnboard, 'Date of Birth'),
          SizedBox(height: 16),
          _buildPhoneField(_phoneOnboard, 'Phone Number')
        ]));
  }

  Widget _buildOnboardingPhysicalInfo() {
    return Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(16),
            border:
                Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.fitness_center, color: joviCoral),
            SizedBox(width: 8),
            Text('Physical Information',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.white))
          ]),
          SizedBox(height: 16),
          if (layoutSettings.useTwoColumnLayout)
            Row(children: [
              Expanded(
                  child: _buildDropdown(
                      value: _height,
                      label: 'Height',
                      items: _heights
                          .map(
                              (h) => DropdownMenuItem(value: h, child: Text(h)))
                          .toList(),
                      onChanged: (v) => setState(() => _height = v),
                      validator: (v) => v == null ? 'Required' : null)),
              SizedBox(width: 12),
              Expanded(
                  child: _buildTextField(_weight, 'Weight (lbs)',
                      Icons.monitor_weight, TextInputType.number))
            ])
          else
            Column(children: [
              _buildDropdown(
                  value: _height,
                  label: 'Height',
                  items: _heights
                      .map((h) => DropdownMenuItem(value: h, child: Text(h)))
                      .toList(),
                  onChanged: (v) => setState(() => _height = v),
                  validator: (v) => v == null ? 'Required' : null),
              SizedBox(height: 16),
              _buildTextField(_weight, 'Weight (lbs)', Icons.monitor_weight,
                  TextInputType.number)
            ]),
          SizedBox(height: 16),
          _buildDropdown(
              value: _gender,
              label: 'Gender',
              items: ['Male', 'Female']
                  .map((g) => DropdownMenuItem(value: g, child: Text(g)))
                  .toList(),
              onChanged: (v) => setState(() => _gender = v),
              validator: (v) => v == null ? 'Required' : null)
        ]));
  }

  Widget _buildOnboardingHealthInfo() {
    return Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(16),
            border:
                Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.health_and_safety, color: joviCoral),
            SizedBox(width: 8),
            Text('Health Information',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.white))
          ]),
          SizedBox(height: 16),
          TextFormField(
              controller: _conds,
              maxLines: 3,
              style: const TextStyle(color: Colors.white, fontSize: 16),
              cursorColor: joviCoral,
              decoration: InputDecoration(
                  labelText: 'Preexisting Conditions (Optional)',
                  hintText: 'List any known medical conditions...',
                  alignLabelWithHint: true,
                  labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
                  hintStyle: TextStyle(color: Colors.white.withOpacity(0.4)),
                  border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12)),
                  enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide:
                          BorderSide(color: Colors.white.withOpacity(0.15))),
                  focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide: BorderSide(color: joviCoral, width: 2)),
                  filled: true,
                  fillColor: Colors.white.withOpacity(0.06),
                  prefixIcon:
                      Icon(Icons.medical_information, color: joviCoral)),
              onChanged: (v) => _saveProgressData())
        ]));
  }

  Widget _buildOnboardingEmergencyContact() {
    return Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(16),
            border:
                Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.contact_emergency, color: joviCoral),
            SizedBox(width: 8),
            Text('Emergency Contact',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.white))
          ]),
          SizedBox(height: 8),
          Text('Required for all members',
              style: TextStyle(
                  color: Colors.white.withOpacity(0.65), fontSize: 14)),
          SizedBox(height: 16),
          _buildTextField(_emName, 'Emergency Contact Name', Icons.person_pin),
          SizedBox(height: 16),
          _buildPhoneField(_emPhone, 'Emergency Contact Phone')
        ]));
  }

  Widget _buildOnboardingLocationInfo() {
    return Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(16),
            border:
                Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.location_on, color: joviCoral),
            SizedBox(width: 8),
            Text('Location Information',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.white))
          ]),
          SizedBox(height: 16),
          _buildAddressPicker(_address, 'Mailing Address', Icons.home),
          SizedBox(height: 16),
          _buildAddressPicker(
              _pharmacy, 'Preferred Pharmacy', Icons.local_pharmacy)
        ]));
  }

  Widget _buildOnboardingReferral() {
    return Container(
        padding: EdgeInsets.all(20),
        decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.07),
            borderRadius: BorderRadius.circular(16),
            border:
                Border.all(color: Colors.white.withOpacity(0.12), width: 1)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.info, color: joviCoral),
            SizedBox(width: 8),
            Text('How did you hear about us?',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: Colors.white))
          ]),
          SizedBox(height: 16),
          _buildTextField(
              _referral, 'Referral Source (Optional)', Icons.record_voice_over)
        ]));
  }

  Widget _buildCompletionScreen() {
    return Container(
      padding: EdgeInsets.all(40),
      decoration: BoxDecoration(
        gradient: LinearGradient(
            colors: [joviCoral, joviCoralLight],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
              color: joviCoral.withOpacity(0.45),
              blurRadius: 40,
              spreadRadius: 2,
              offset: Offset(0, 16)),
          BoxShadow(
              color: joviCoral.withOpacity(0.2),
              blurRadius: 60,
              spreadRadius: -8,
              offset: Offset(0, 28)),
        ],
      ),
      child: Column(children: [
        Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(60)),
            child: Icon(Icons.celebration, size: 80, color: Colors.white)),
        SizedBox(height: 24),
        Text('You’re all set',
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: layoutSettings.wideMode ? 36 : 32,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.7,
                height: 1.1,
                color: Colors.white)),
        SizedBox(height: 16),
        Text('Welcome to the Jovi Health family!',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, color: Colors.white70)),
        SizedBox(height: 12),
        Text('Your account is fully set up',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 16, color: Colors.white60)),
        SizedBox(height: 32),
        Container(
            padding: EdgeInsets.all(24),
            decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.15),
                borderRadius: BorderRadius.circular(16)),
            child: Column(children: [
              Text('What\'s Next?',
                  style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white)),
              SizedBox(height: 16),
              Row(children: [
                Icon(Icons.credit_card, color: Colors.white, size: 20),
                SizedBox(width: 12),
                Expanded(
                    child: Text('Digital membership card available',
                        style: TextStyle(color: Colors.white, fontSize: 14)))
              ]),
              SizedBox(height: 8),
              Row(children: [
                Icon(Icons.local_hospital, color: Colors.white, size: 20),
                SizedBox(width: 12),
                Expanded(
                    child: Text('Find nearby healthcare providers',
                        style: TextStyle(color: Colors.white, fontSize: 14)))
              ]),
              SizedBox(height: 8),
              Row(children: [
                Icon(Icons.support_agent, color: Colors.white, size: 20),
                SizedBox(width: 12),
                Expanded(
                    child: Text('Access 24/7 member support',
                        style: TextStyle(color: Colors.white, fontSize: 14)))
              ]),
              if (_numPets > 0) ...[
                SizedBox(height: 8),
                Row(children: [
                  Icon(Icons.pets, color: Colors.white, size: 20),
                  SizedBox(width: 12),
                  Expanded(
                      child: Text('Pet sharing cards ready',
                          style: TextStyle(color: Colors.white, fontSize: 14)))
                ])
              ],
            ])),
      ]),
    );
  }
}

/// Paints a fixed set of confetti pieces at progress [t] in 0..1. The
/// pieces are generated once by the caller; r2.5 regenerated a random set
/// on every frame, so the confetti flickered instead of falling.
class ConfettiPainter extends CustomPainter {
  final List<Confetti> pieces;
  final double t;

  ConfettiPainter(this.pieces, this.t);

  @override
  void paint(Canvas canvas, Size size) {
    if (t <= 0 || t >= 1) return;
    final paint = Paint();
    // Fully visible for the first 70%, then fades out so nothing is left
    // frozen on screen when the animation completes.
    final fade = t < 0.7 ? 1.0 : ((1 - t) / 0.3).clamp(0.0, 1.0);
    for (int i = 0; i < pieces.length; i++) {
      final c = pieces[i];
      final y = (c.y + t * c.speed * 2) * size.height;
      if (y > size.height + 50 || y < -50) continue;
      final x = c.x * size.width + sin(t * 2 + c.x * 10) * 20;
      paint.color = c.color.withOpacity(fade);
      canvas.save();
      canvas.translate(x, y);
      canvas.rotate((c.rotation + t * c.rotationSpeed) * pi / 180);
      switch (i % 3) {
        case 0:
          canvas.drawRect(
              Rect.fromCenter(
                  center: Offset.zero, width: c.size, height: c.size / 2),
              paint);
          break;
        case 1:
          canvas.drawCircle(Offset.zero, c.size / 2, paint);
          break;
        default:
          final path = Path()
            ..moveTo(0, -c.size / 2)
            ..lineTo(-c.size / 2, c.size / 2)
            ..lineTo(c.size / 2, c.size / 2)
            ..close();
          canvas.drawPath(path, paint);
      }
      canvas.restore();
    }
  }

  @override
  bool shouldRepaint(covariant ConfettiPainter old) =>
      old.t != t || !identical(old.pieces, pieces);
}

class Confetti {
  final double x;
  final double y;
  final Color color;
  final double size;
  final double speed;
  final double rotation;
  final double rotationSpeed;
  const Confetti(
      {required this.x,
      required this.y,
      required this.color,
      required this.size,
      required this.speed,
      required this.rotation,
      required this.rotationSpeed});

  static const List<Color> _palette = [
    joviCoral,
    joviCoralLight,
    joviMint,
    joviGold,
    Colors.white,
  ];

  /// Deterministic set so the celebration looks the same every time.
  static List<Confetti> generate({int seed = 0, int count = 90}) {
    final random = Random(seed);
    return List.generate(
        count,
        (_) => Confetti(
            x: random.nextDouble(),
            y: random.nextDouble() * -1,
            color: _palette[random.nextInt(_palette.length)],
            size: random.nextDouble() * 9 + 5,
            speed: random.nextDouble() * 0.5 + 0.5,
            rotation: random.nextDouble() * 360,
            rotationSpeed: random.nextDouble() * 240 - 120));
  }
}
