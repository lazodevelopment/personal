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
// JOVI HEALTH — RECORDS EXPORT
// Version: 2026.09.22-r1
// Build: JC-EXPORT-0922-001
//
// Widget Name (for FF): RecordsExport
// Params (all optional): width, height
//
// Builds a PDF of the member's records on device (pdf + printing, the same
// packages Billing uses) and hands it to the iOS share sheet: save to
// Files, AirDrop, email to a clinic or vet. Nothing is uploaded.
//
// Sections (each can be toggled):
//   People   appointments (requests where userId), visit records,
//            prescriptions, vaccinations
//   Pets     profile, vaccinations, medications, claims
//   Claims   human claims (users/{uid}/claims)
// Date range: last 12 months or everything.
//
// Field names are read with fallbacks because the writing widgets differ
// slightly (see each _row* helper). Unknown fields are never dumped.
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:async';
import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:intl/intl.dart';
import 'package:pdf/pdf.dart' as pw_pdf;
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

// ─── Jovi Brand Color System ────────────────────────────────────────────
const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviCoralDark = Color(0xFFE5583A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviErrorRed = Color(0xFFE53935);
const Color _petAccent = Color(0xFFA78BFA);


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

class RecordsExport extends StatefulWidget {
  const RecordsExport({
    Key? key,
    this.width,
    this.height,
  }) : super(key: key);

  final double? width;
  final double? height;

  @override
  State<RecordsExport> createState() => _RecordsExportState();
}

enum _Range { year, all }

// ═══════════════════════════════════════════════════════════════════════════
// VALUE HELPERS (defensive readers over loosely-typed docs)
// ═══════════════════════════════════════════════════════════════════════════

String _s(Map<String, dynamic> m, List<String> keys, [String fallback = '']) {
  for (final k in keys) {
    final v = m[k];
    if (v == null) continue;
    if (v is String && v.trim().isNotEmpty) return v.trim();
    if (v is num) return v.toString();
    if (v is bool) return v ? 'Yes' : 'No';
  }
  return fallback;
}

DateTime? _d(Map<String, dynamic> m, List<String> keys) {
  for (final k in keys) {
    final v = m[k];
    if (v is Timestamp) return v.toDate();
    if (v is String && v.isNotEmpty) {
      final iso = DateTime.tryParse(v);
      if (iso != null) return iso;
      final parts = v.split('/');
      if (parts.length == 3) {
        final mo = int.tryParse(parts[0]);
        final da = int.tryParse(parts[1]);
        final y = int.tryParse(parts[2]);
        if (mo != null && da != null && y != null) {
          try {
            return DateTime(y, mo, da);
          } catch (_) {}
        }
      }
    }
  }
  return null;
}

double? _n(Map<String, dynamic> m, List<String> keys) {
  for (final k in keys) {
    final v = m[k];
    if (v is num) return v.toDouble();
    if (v is String) {
      final p = double.tryParse(v.replaceAll(RegExp(r'[^\d.\-]'), ''));
      if (p != null) return p;
    }
  }
  return null;
}

List<String> _list(Map<String, dynamic> m, List<String> keys) {
  for (final k in keys) {
    final v = m[k];
    if (v is List) {
      return v
          .map((e) {
            if (e is String) return e.trim();
            if (e is Map) {
              return _s(Map<String, dynamic>.from(e),
                  ['name', 'label', 'diagnosis', 'description', 'medicationName']);
            }
            return '';
          })
          .where((e) => e.isNotEmpty)
          .toList();
    }
  }
  return const [];
}

String _fmtDate(DateTime? d) => d == null ? '—' : DateFormat('MMM d, y').format(d);
String _fmtUsd(double? v) => v == null ? '—' : NumberFormat.currency(symbol: '\$').format(v);
String _title(String s) =>
    s.replaceAll('_', ' ').split(' ').map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}').join(' ');

// ═══════════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════════

class _RecordsExportState extends State<RecordsExport>
    with SingleTickerProviderStateMixin {
  bool _people = true;
  bool _pets = true;
  bool _claims = true;
  _Range _range = _Range.year;
  bool _busy = false;
  String _progress = '';
  DateTime? _lastExport;

  late final AnimationController _fadeCtrl;
  late final Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(vsync: this, duration: _Motion.enter);
    _fadeAnim = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut);
    if (_platformReduceMotion()) {
      _fadeCtrl.value = 1.0;
    } else {
      _fadeCtrl.forward();
    }
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    super.dispose();
  }

  DateTime? get _since =>
      _range == _Range.year ? DateTime.now().subtract(const Duration(days: 365)) : null;

  bool _inRange(DateTime? d) {
    final since = _since;
    if (since == null || d == null) return true;
    return !d.isBefore(since);
  }

  void _toast(String msg, {bool error = false, bool ok = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(msg,
        accent: error ? _joviErrorRed : ok ? _joviMint : Colors.white70,
        icon: error
            ? CupertinoIcons.exclamationmark_circle
            : ok
                ? CupertinoIcons.checkmark_circle
                : CupertinoIcons.info_circle));
  }

  // ─── Data gathering ─────────────────────────────────────────────────

  Future<List<Map<String, dynamic>>> _docs(Query<Map<String, dynamic>> q) async {
    try {
      final snap = await q.get();
      return snap.docs.map((d) => {...d.data(), '_id': d.id}).toList();
    } catch (e) {
      debugPrint('Export: query failed: $e');
      return const [];
    }
  }

  Future<void> _export() async {
    if (_busy) return;
    if (!_people && !_pets && !_claims) {
      _toast('Pick at least one section to include.', error: true);
      return;
    }
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) {
      _toast('Sign in to export your records.', error: true);
      return;
    }
    HapticFeedback.mediumImpact();
    setState(() {
      _busy = true;
      _progress = 'Gathering records…';
    });

    try {
      final db = FirebaseFirestore.instance;
      final userRef = db.collection('users').doc(uid);
      final userDoc = await userRef.get();
      final user = userDoc.data() ?? {};
      final memberName = _s(user, ['onboard_fullName', 'fullName'],
          '${_s(user, ['firstName', 'first'])} ${_s(user, ['lastName', 'last'])}'.trim());

      // Built-in Helvetica: no network fetch, works offline and on first
      // launch. Diacritics render fine; non-Latin scripts would need a
      // bundled font.
      final doc = pw.Document();

      final sections = <pw.Widget>[];
      var totalRecords = 0;

      // ── People ──────────────────────────────────────────────────────
      if (_people) {
        setState(() => _progress = 'Care records…');
        final requests = (await _docs(db
                .collection('requests')
                .where('userId', isEqualTo: uid)
                .limit(300)))
            .where((m) => _inRange(_d(m, ['appointmentDate', 'startAt', 'createdAt'])))
            .toList()
          ..sort((a, b) => (_d(b, ['appointmentDate', 'startAt', 'createdAt']) ?? DateTime(0))
              .compareTo(_d(a, ['appointmentDate', 'startAt', 'createdAt']) ?? DateTime(0)));
        final visits = (await _docs(userRef.collection('visit_records').limit(300)))
            .where((m) => _inRange(_d(m, ['visitDate', 'date', 'createdAt'])))
            .toList()
          ..sort((a, b) => (_d(b, ['visitDate', 'date', 'createdAt']) ?? DateTime(0))
              .compareTo(_d(a, ['visitDate', 'date', 'createdAt']) ?? DateTime(0)));
        final rxs = (await _docs(db
                .collection('prescriptions')
                .where('userId', isEqualTo: uid)
                .limit(300)))
            .where((m) => _inRange(_d(m, ['prescribedAt', 'createdAt'])))
            .toList();
        final vax = (await _docs(userRef.collection('vaccinations').limit(300)))
            .where((m) => _inRange(_d(m, ['administeredAt'])))
            .toList()
          ..sort((a, b) => (_d(b, ['administeredAt']) ?? DateTime(0))
              .compareTo(_d(a, ['administeredAt']) ?? DateTime(0)));

        totalRecords += requests.length + visits.length + rxs.length + vax.length;
        sections.add(_h1('Care Records'));
        sections.add(_h2('Appointments (${requests.length})'));
        if (requests.isEmpty) sections.add(_empty());
        for (final m in requests) {
          sections.add(_record(
            title: '${_title(_s(m, ['visitType'], 'Visit'))} · ${_fmtDate(_d(m, ['appointmentDate', 'startAt', 'createdAt']))}${_s(m, ['appointmentTime']).isNotEmpty ? ' ${_s(m, ['appointmentTime'])}' : ''}',
            rows: [
              ['Patient', _s(m, ['patientName'], memberName)],
              ['Provider', _s(m, ['providerName', 'provider'])],
              ['Clinic', _s(m, ['clinicName', 'clinic'])],
              ['Mode', _title(_s(m, ['visitMode']))],
              ['Reason', _s(m, ['reason', 'chiefComplaint', 'symptom'])],
              ['Status', _title(_s(m, ['status']))],
            ],
          ));
        }
        sections.add(_h2('Visit Records (${visits.length})'));
        if (visits.isEmpty) sections.add(_empty());
        for (final m in visits) {
          final dx = _list(m, ['diagnoses']);
          final rx = _list(m, ['prescriptions']);
          sections.add(_record(
            title: '${_s(m, ['providerName', 'provider'], 'Visit')} · ${_fmtDate(_d(m, ['visitDate', 'date', 'createdAt']))}',
            rows: [
              ['Patient', _s(m, ['patientName'], memberName)],
              ['Clinic', _s(m, ['clinicName', 'clinic'])],
              ['Reason', _s(m, ['chiefComplaint', 'reason'])],
              ['Diagnoses', dx.join('; ')],
              ['Prescriptions', rx.join('; ')],
              ['Follow-up', _s(m, ['followUp'])],
              ['Notes', _s(m, ['clinicalNotes', 'notes', 'patientEducation'])],
            ],
          ));
        }
        sections.add(_h2('Prescriptions (${rxs.length})'));
        if (rxs.isEmpty) sections.add(_empty());
        for (final m in rxs) {
          sections.add(_record(
            title: _s(m, ['medicationName', 'name', 'medication'], 'Prescription'),
            rows: [
              ['Dose', _s(m, ['dosage', 'dose', 'sig'])],
              ['Frequency', _s(m, ['frequency', 'freq'])],
              ['Prescribed', _fmtDate(_d(m, ['prescribedAt', 'createdAt']))],
              ['Prescriber', _s(m, ['prescriber', 'provider'])],
              ['Pharmacy', _s(m, ['pharmacy'])],
              ['Refills left', _s(m, ['refillsRemaining', 'refills'])],
              ['Status', _title(_s(m, ['status']))],
            ],
          ));
        }
        sections.add(_h2('Vaccinations (${vax.length})'));
        if (vax.isEmpty) sections.add(_empty());
        for (final m in vax) {
          sections.add(_record(
            title: '${_s(m, ['vaccineName'], 'Vaccine')}${_s(m, ['doseLabel']).isNotEmpty ? ' · ${_s(m, ['doseLabel'])}' : ''}',
            rows: [
              ['Patient', _s(m, ['patientName'], memberName)],
              ['Given', _fmtDate(_d(m, ['administeredAt']))],
              ['Next due', _fmtDate(_d(m, ['expiresAt']))],
              ['Provider', _s(m, ['provider'])],
              ['Lot', _s(m, ['lotNumber'])],
              ['Notes', _s(m, ['notes'])],
            ],
          ));
        }
      }

      // ── Claims ──────────────────────────────────────────────────────
      if (_claims) {
        setState(() => _progress = 'Claims…');
        final claims = (await _docs(userRef.collection('claims').limit(300)))
            .where((m) => _inRange(_d(m, ['submittedAt', 'date', 'createdAt'])))
            .toList()
          ..sort((a, b) => (_d(b, ['submittedAt', 'date', 'createdAt']) ?? DateTime(0))
              .compareTo(_d(a, ['submittedAt', 'date', 'createdAt']) ?? DateTime(0)));
        totalRecords += claims.length;
        sections.add(_h1('Claims (${claims.length})'));
        if (claims.isEmpty) sections.add(_empty());
        for (final m in claims) {
          sections.add(_record(
            title: '${_s(m, ['provider', 'providerClinic'], 'Claim')} · ${_fmtUsd(_n(m, ['amount']))}',
            rows: [
              ['Patient', _s(m, ['patientName'], memberName)],
              ['Date of service', _fmtDate(_d(m, ['date', 'dateOfService']))],
              ['Submitted', _fmtDate(_d(m, ['submittedAt']))],
              ['Status', _title(_s(m, ['status']))],
              ['Paid', _fmtUsd(_n(m, ['paidAmount']))],
              ['Reference', _s(m, ['confirmationId', 'claimId', '_id'])],
              ['Description', _s(m, ['description', 'reason'])],
            ],
          ));
        }
      }

      // ── Pets ────────────────────────────────────────────────────────
      if (_pets) {
        setState(() => _progress = 'Pet records…');
        final pets = await _docs(userRef.collection('pets').limit(50));
        // Legacy pets array on the user doc, for accounts never migrated.
        final seen = pets.map((p) => _s(p, ['petId', '_id'])).toSet();
        for (final raw in (user['pets'] as List<dynamic>? ?? const [])) {
          try {
            final m = raw is String
                ? Map<String, dynamic>.from(jsonDecode(raw) as Map)
                : Map<String, dynamic>.from(raw as Map);
            final id = _s(m, ['petId', 'id']);
            if (id.isNotEmpty && seen.contains(id)) continue;
            pets.add({...m, '_id': id, '_legacy': true});
          } catch (_) {}
        }
        sections.add(_h1('Pets (${pets.length})'));
        if (pets.isEmpty) sections.add(_empty());
        for (final p in pets) {
          final pid = _s(p, ['petId', '_id']);
          final name = _s(p, ['name'], 'Pet');
          sections.add(_h2(name));
          sections.add(_record(
            title: 'Profile',
            rows: [
              ['Type', _title(_s(p, ['type']))],
              ['Breed', _s(p, ['breed'])],
              ['Born', _fmtDate(_d(p, ['birthdate', 'dateOfBirth', 'dob']))],
              ['Weight', _n(p, ['weightLbs', 'weight']) == null ? '' : '${_n(p, ['weightLbs', 'weight'])!.toStringAsFixed(1)} lbs'],
              ['Sex', _title(_s(p, ['sex', 'gender']))],
              ['Microchip', _s(p, ['microchipId', 'microchip'])],
              ['Vet', _s(p, ['primaryVetName', 'vetName'])],
              ['Vet clinic', _s(p, ['primaryVetClinic', 'vetClinic'])],
              ['Allergies', _list(p, ['allergies']).join('; ')],
              ['Pre-existing', _s(p, ['preExistingNotes'])],
            ],
          ));
          if (pid.isEmpty || p['_legacy'] == true) continue;
          final petRef = userRef.collection('pets').doc(pid);

          final pvax = (await _docs(petRef.collection('vaccinations').limit(200)))
              .where((m) => _inRange(_d(m, ['administeredDate'])))
              .toList()
            ..sort((a, b) => (_d(b, ['administeredDate']) ?? DateTime(0))
                .compareTo(_d(a, ['administeredDate']) ?? DateTime(0)));
          final pmeds = await _docs(petRef.collection('medications').limit(200));
          final pclaims = (await _docs(petRef.collection('claims').limit(200)))
              .where((m) => _inRange(_d(m, ['submittedAt', 'dateOfService'])))
              .toList();
          totalRecords += pvax.length + pmeds.length + pclaims.length;

          sections.add(_h3('Vaccinations (${pvax.length})'));
          for (final m in pvax) {
            sections.add(_record(
              title: '${_s(m, ['vaccineName'], 'Vaccine')}${_s(m, ['vaccineType']).isNotEmpty ? ' (${_title(_s(m, ['vaccineType']))})' : ''}',
              rows: [
                ['Given', _fmtDate(_d(m, ['administeredDate']))],
                ['Expires', _fmtDate(_d(m, ['expirationDate']))],
                ['Clinic', _s(m, ['clinicName'])],
                ['Administered by', _s(m, ['administeredBy'])],
                ['Lot', _s(m, ['batchNumber'])],
                ['Notes', _s(m, ['notes'])],
              ],
            ));
          }
          sections.add(_h3('Medications (${pmeds.length})'));
          for (final m in pmeds) {
            sections.add(_record(
              title: '${_s(m, ['name'], 'Medication')}${_s(m, ['strength']).isNotEmpty ? ' ${_s(m, ['strength'])}' : ''}',
              rows: [
                ['Dose', _s(m, ['dosage'])],
                ['Type', _title(_s(m, ['type']))],
                ['As needed', _s(m, ['isAsNeeded'])],
                ['Started', _fmtDate(_d(m, ['startDate']))],
                ['Stopped', _fmtDate(_d(m, ['stopDate']))],
                ['Prescribed by', _s(m, ['prescribedBy'])],
                ['Condition', _s(m, ['condition'])],
                ['Instructions', _s(m, ['instructions'])],
              ],
            ));
          }
          sections.add(_h3('Claims (${pclaims.length})'));
          for (final m in pclaims) {
            sections.add(_record(
              title: '${_s(m, ['providerClinic'], 'Vet visit')} · ${_fmtUsd(_n(m, ['amount']))}',
              rows: [
                ['Date of service', _fmtDate(_d(m, ['dateOfService']))],
                ['Submitted', _fmtDate(_d(m, ['submittedAt']))],
                ['Status', _title(_s(m, ['status']))],
                ['Reimbursement', _fmtUsd(_n(m, ['finalReimbursement', 'estimatedReimbursement']))],
                ['Reason', _s(m, ['reason'])],
              ],
            ));
          }
        }
      }

      setState(() => _progress = 'Building PDF…');
      final generated = DateTime.now();
      final rangeLabel = _range == _Range.year ? 'Last 12 months' : 'All time';
      doc.addPage(
        pw.MultiPage(
          pageFormat: pw_pdf.PdfPageFormat.letter,
          margin: const pw.EdgeInsets.all(44),
          header: (ctx) => pw.Padding(
            padding: const pw.EdgeInsets.only(bottom: 10),
            child: pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Text('Jovi Health · Records',
                    style: pw.TextStyle(
                        fontSize: 10, color: _pdfMuted, fontWeight: pw.FontWeight.bold)),
                pw.Text(memberName.isEmpty ? '' : memberName,
                    style: pw.TextStyle(fontSize: 10, color: _pdfMuted)),
              ],
            ),
          ),
          footer: (ctx) => pw.Padding(
            padding: const pw.EdgeInsets.only(top: 10),
            child: pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Text('Generated ${DateFormat('MMM d, y · h:mm a').format(generated)} · $rangeLabel',
                    style: pw.TextStyle(fontSize: 9, color: _pdfMuted)),
                pw.Text('Page ${ctx.pageNumber} of ${ctx.pagesCount}',
                    style: pw.TextStyle(fontSize: 9, color: _pdfMuted)),
              ],
            ),
          ),
          build: (ctx) => [
            pw.Text('Health Records',
                style: pw.TextStyle(
                    fontSize: 24, fontWeight: pw.FontWeight.bold, color: _pdfNavy)),
            pw.SizedBox(height: 4),
            pw.Text(
              'Prepared for ${memberName.isEmpty ? 'the member' : memberName} from records kept in the Jovi Health app. Member-entered information, not a clinical record.',
              style: pw.TextStyle(fontSize: 10.5, color: _pdfMuted),
            ),
            pw.SizedBox(height: 14),
            pw.Container(height: 1, color: _pdfDivider),
            ...sections,
          ],
        ),
      );

      final bytes = await doc.save();
      if (!mounted) return;
      setState(() => _progress = 'Opening share sheet…');
      final stamp = DateFormat('yyyy-MM-dd').format(generated);
      await Printing.sharePdf(bytes: bytes, filename: 'jovi-records-$stamp.pdf');
      if (!mounted) return;
      setState(() => _lastExport = generated);
      HapticFeedback.mediumImpact();
      _toast('$totalRecords record${totalRecords == 1 ? '' : 's'} exported', ok: true);
    } catch (e) {
      debugPrint('Export: failed: $e');
      if (!mounted) return;
      _toast('Could not build the export. Please try again.', error: true);
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _progress = '';
        });
      }
    }
  }

  // ─── PDF pieces ─────────────────────────────────────────────────────

  pw_pdf.PdfColor get _pdfNavy => pw_pdf.PdfColor.fromInt(0xFF1A2744);
  pw_pdf.PdfColor get _pdfCoral => pw_pdf.PdfColor.fromInt(0xFFFF6B4A);
  pw_pdf.PdfColor get _pdfMuted => pw_pdf.PdfColor.fromInt(0xFF6B7280);
  pw_pdf.PdfColor get _pdfDivider => pw_pdf.PdfColor.fromInt(0xFFE5E7EB);
  pw_pdf.PdfColor get _pdfCard => pw_pdf.PdfColor.fromInt(0xFFF9FAFB);

  pw.Widget _h1(String t) => pw.Padding(
        padding: const pw.EdgeInsets.only(top: 18, bottom: 6),
        child: pw.Text(t,
            style: pw.TextStyle(
                fontSize: 16, fontWeight: pw.FontWeight.bold, color: _pdfNavy)),
      );

  pw.Widget _h2(String t) => pw.Padding(
        padding: const pw.EdgeInsets.only(top: 10, bottom: 4),
        child: pw.Text(t,
            style: pw.TextStyle(
                fontSize: 12.5, fontWeight: pw.FontWeight.bold, color: _pdfCoral)),
      );

  pw.Widget _h3(String t) => pw.Padding(
        padding: const pw.EdgeInsets.only(top: 6, bottom: 3),
        child: pw.Text(t,
            style: pw.TextStyle(
                fontSize: 11, fontWeight: pw.FontWeight.bold, color: _pdfMuted)),
      );

  pw.Widget _empty() => pw.Padding(
        padding: const pw.EdgeInsets.only(bottom: 4),
        child: pw.Text('None in this range', style: pw.TextStyle(fontSize: 10, color: _pdfMuted)),
      );

  pw.Widget _record({required String title, required List<List<String>> rows}) {
    final visible = rows.where((r) => r[1].trim().isNotEmpty && r[1] != '—').toList();
    return pw.Container(
      margin: const pw.EdgeInsets.only(bottom: 6),
      padding: const pw.EdgeInsets.all(9),
      decoration: pw.BoxDecoration(
        color: _pdfCard,
        borderRadius: const pw.BorderRadius.all(pw.Radius.circular(5)),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(title,
              style: pw.TextStyle(
                  fontSize: 11, fontWeight: pw.FontWeight.bold, color: _pdfNavy)),
          if (visible.isNotEmpty) pw.SizedBox(height: 4),
          for (final r in visible)
            pw.Padding(
              padding: const pw.EdgeInsets.only(bottom: 1.5),
              child: pw.Row(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.SizedBox(
                    width: 96,
                    child: pw.Text(r[0], style: pw.TextStyle(fontSize: 9.5, color: _pdfMuted)),
                  ),
                  pw.Expanded(
                    child: pw.Text(r[1], style: pw.TextStyle(fontSize: 9.5, color: _pdfNavy)),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  // ═══════════════════════════════════════════════════════════════════════
  // BUILD
  // ═══════════════════════════════════════════════════════════════════════

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context).size;
    return Container(
      width: widget.width ?? mq.width,
      height: widget.height ?? mq.height,
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_joviNavy, _joviNavyDark],
        ),
      ),
      child: SafeArea(
        child: FadeTransition(
          opacity: _fadeAnim,
          child: Column(
            children: [
              _buildHeader(),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                  children: [
                    _intro(),
                    const SizedBox(height: 18),
                    _label('Include'),
                    const SizedBox(height: 8),
                    _toggleRow(
                      icon: CupertinoIcons.person_2,
                      color: _joviCoral,
                      title: 'Care records',
                      subtitle: 'Appointments, visits, prescriptions, vaccinations',
                      value: _people,
                      onChanged: (v) => setState(() => _people = v),
                    ),
                    const SizedBox(height: 8),
                    _toggleRow(
                      icon: CupertinoIcons.paw,
                      color: _petAccent,
                      title: 'Pet records',
                      subtitle: 'Profiles, vaccinations, medications, claims',
                      value: _pets,
                      onChanged: (v) => setState(() => _pets = v),
                    ),
                    const SizedBox(height: 8),
                    _toggleRow(
                      icon: CupertinoIcons.doc_text,
                      color: _joviMint,
                      title: 'Claims',
                      subtitle: 'Your submitted claims and their status',
                      value: _claims,
                      onChanged: (v) => setState(() => _claims = v),
                    ),
                    const SizedBox(height: 18),
                    _label('Date range'),
                    const SizedBox(height: 8),
                    _rangePicker(),
                    const SizedBox(height: 22),
                    _exportButton(),
                    if (_lastExport != null) ...[
                      const SizedBox(height: 10),
                      Center(
                        child: Text(
                          'Last export ${DateFormat('MMM d, h:mm a').format(_lastExport!)}',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.45),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                    const SizedBox(height: 18),
                    _privacyNote(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 16, 4),
      child: Row(
        children: [
          _PressableMaterial(
            child: InkWell(
              onTap: () {
                HapticFeedback.selectionClick();
                if (Navigator.of(context).canPop()) Navigator.of(context).pop();
              },
              borderRadius: BorderRadius.circular(22),
              child: Semantics(
                label: 'Back',
                button: true,
                child: Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.06),
                    shape: BoxShape.circle,
                    border: Border.all(
                        color: Colors.white.withOpacity(0.14), width: 0.8),
                  ),
                  child: Icon(Icons.arrow_back_ios_new_rounded,
                      color: Colors.white.withOpacity(0.85), size: 17),
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Export Records',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.4,
                    height: 1.1,
                  ),
                ),
                SizedBox(height: 1),
                Text(
                  'A PDF you can save or send',
                  style: TextStyle(
                    color: Color(0x88FFFFFF),
                    fontSize: 11.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [_joviCoral, _joviCoralDark]),
              borderRadius: BorderRadius.circular(11),
              boxShadow: [
                BoxShadow(
                  color: _joviCoral.withOpacity(0.35),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: const Icon(CupertinoIcons.square_arrow_up,
                color: Colors.white, size: 20),
          ),
        ],
      ),
    );
  }

  Widget _intro() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: RepaintBoundary(
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withOpacity(0.1)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: _joviGold.withOpacity(0.16),
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(color: _joviGold.withOpacity(0.35), width: 0.8),
                ),
                child: const Icon(CupertinoIcons.doc_richtext, color: _joviGold, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Handy for a new doctor, a vet, or your own files. The PDF is built on your phone and goes wherever you share it. Nothing is uploaded.',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.75),
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    height: 1.45,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _label(String t) => Text(
        t,
        style: TextStyle(
          color: Colors.white.withOpacity(0.6),
          fontSize: 13,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.1,
        ),
      );

  Widget _toggleRow({
    required IconData icon,
    required Color color,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return _PressableMaterial(
      child: InkWell(
        onTap: _busy
            ? null
            : () {
                HapticFeedback.selectionClick();
                onChanged(!value);
              },
        borderRadius: BorderRadius.circular(16),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: RepaintBoundary(
            child: AnimatedContainer(
              duration: _Motion.select,
              curve: _Motion.settle,
              padding: const EdgeInsets.fromLTRB(14, 12, 10, 12),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(value ? 0.09 : 0.05),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: value ? color.withOpacity(0.4) : Colors.white.withOpacity(0.1),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.16),
                      borderRadius: BorderRadius.circular(11),
                      border: Border.all(color: color.withOpacity(0.35), width: 0.8),
                    ),
                    child: Icon(icon, color: color, size: 20),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            letterSpacing: -0.3,
                          ),
                        ),
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
                    ),
                  ),
                  Switch.adaptive(
                    value: value,
                    onChanged: _busy ? null : (v) {
                      HapticFeedback.selectionClick();
                      onChanged(v);
                    },
                    activeColor: Colors.white,
                    activeTrackColor: color,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _rangePicker() {
    Widget seg(_Range r, String label) {
      final selected = _range == r;
      return Expanded(
        child: _PressableMaterial(
          child: InkWell(
            onTap: _busy
                ? null
                : () {
                    if (_range == r) return;
                    HapticFeedback.selectionClick();
                    setState(() => _range = r);
                  },
            borderRadius: BorderRadius.circular(9),
            child: AnimatedContainer(
              duration: _Motion.select,
              curve: _Motion.settle,
              padding: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: selected ? _joviCoral.withOpacity(0.22) : Colors.transparent,
                borderRadius: BorderRadius.circular(9),
                border: selected
                    ? Border.all(color: _joviCoral.withOpacity(0.4), width: 0.8)
                    : null,
              ),
              child: Center(
                child: Text(
                  label,
                  style: TextStyle(
                    color: selected ? Colors.white : Colors.white.withOpacity(0.55),
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    letterSpacing: -0.2,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.06),
        borderRadius: BorderRadius.circular(11),
        border: Border.all(color: Colors.white.withOpacity(0.1), width: 0.8),
      ),
      child: Row(
        children: [
          seg(_Range.year, 'Last 12 months'),
          seg(_Range.all, 'Everything'),
        ],
      ),
    );
  }

  Widget _exportButton() {
    return _Pressable(
      onTap: _busy ? null : _export,
      enabled: !_busy,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [_joviCoral, _joviCoralDark]),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: _joviCoral.withOpacity(_busy ? 0.15 : 0.4),
              blurRadius: 16,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (_busy) ...[
              const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2.2,
                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                ),
              ),
              const SizedBox(width: 10),
              Text(
                _progress.isEmpty ? 'Working…' : _progress,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
              ),
            ] else ...const [
              Icon(CupertinoIcons.square_arrow_up, color: Colors.white, size: 19),
              SizedBox(width: 8),
              Text(
                'Build PDF',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.3,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _privacyNote() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _joviMint.withOpacity(0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _joviMint.withOpacity(0.25), width: 0.8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(CupertinoIcons.lock, color: _joviMintDark, size: 15),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'This export is member-entered information kept in Jovi, not an official clinical record. Once shared, anyone with the file can read it.',
              style: TextStyle(
                color: Colors.white.withOpacity(0.7),
                fontSize: 11.5,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
