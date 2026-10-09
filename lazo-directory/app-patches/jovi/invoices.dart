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
// JOVI — INVOICES & RECEIPTS
// Version: 2026.10.01-r1
//
// Widget Name (for FF): JoviInvoices
// Params (all optional): width, height
// FlutterFlow page name: `invoices`
//
// Reads users/{uid}/invoices (written by the BILL billing functions for every
// membership debit, Jovi Pass purchase, and pet add-on). Each receipt opens in
// a sheet with Share (PDF via the share sheet) and Print. PDF is built on the
// device with the pdf/printing packages already used by Records Export.
// ═══════════════════════════════════════════════════════════════════════════

import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:intl/intl.dart';
import 'package:pdf/pdf.dart' as pw_pdf;
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

const Color _joviCoral = Color(0xFFFF6B4A);
const Color _joviNavy = Color(0xFF1A2744);
const Color _joviNavyDark = Color(0xFF0F1A2E);
const Color _joviMint = Color(0xFF00D4AA);
const Color _joviMintDark = Color(0xFF00B894);
const Color _joviGold = Color(0xFFFFD166);
const Color _joviErrorRed = Color(0xFFE53935);


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

class JoviInvoices extends StatefulWidget {
  const JoviInvoices({Key? key, this.width, this.height}) : super(key: key);
  final double? width;
  final double? height;
  @override
  State<JoviInvoices> createState() => _JoviInvoicesState();
}

class _Invoice {
  final String id;
  final String number;
  final String kind;
  final String status;
  final List<Map<String, dynamic>> items;
  final double total;
  final double amountPaid;
  final DateTime? issuedAt;
  final DateTime? paidAt;
  final DateTime? periodStart;
  final DateTime? periodEnd;
  final String? last4;
  final String? reason;
  final String memberName;
  final String? memberEmail;
  final String? memberAddress;
  final Map<String, dynamic> company;

  const _Invoice({
    required this.id, required this.number, required this.kind, required this.status, required this.items, required this.total,
    required this.amountPaid, this.issuedAt, this.paidAt, this.periodStart, this.periodEnd, this.last4, this.reason,
    required this.memberName, this.memberEmail, this.memberAddress, required this.company,
  });

  factory _Invoice.fromDoc(DocumentSnapshot<Map<String, dynamic>> d) {
    final m = d.data() ?? {};
    DateTime? ts(dynamic v) => v is Timestamp ? v.toDate() : null;
    final pm = m['paymentMethod'];
    return _Invoice(
      id: d.id,
      number: (m['number'] as String?) ?? d.id,
      kind: (m['kind'] as String?) ?? 'membership',
      status: ((m['status'] as String?) ?? 'pending').toLowerCase(),
      items: ((m['items'] as List?) ?? const []).map((e) => Map<String, dynamic>.from(e as Map)).toList(),
      total: (m['total'] as num?)?.toDouble() ?? 0,
      amountPaid: (m['amountPaid'] as num?)?.toDouble() ?? 0,
      issuedAt: ts(m['issuedAt']),
      paidAt: ts(m['paidAt']),
      periodStart: ts(m['periodStart']),
      periodEnd: ts(m['periodEnd']),
      last4: pm is Map ? pm['last4'] as String? : null,
      reason: m['reason'] as String?,
      memberName: (m['memberName'] as String?) ?? 'Jovi member',
      memberEmail: m['memberEmail'] as String?,
      memberAddress: m['memberAddress'] as String?,
      company: m['company'] is Map ? Map<String, dynamic>.from(m['company'] as Map) : const {},
    );
  }

  String get title {
    switch (kind) {
      case 'kurvpass':
        return 'Jovi Pass';
      case 'pet_addon_proration':
        return 'Jovi Pets add-on';
      case 'membership_retry':
      case 'membership':
        return 'Monthly membership';
      default:
        return kind.replaceAll('_', ' ');
    }
  }

  String get statusLabel {
    switch (status) {
      case 'paid':
        return 'Paid';
      case 'pending':
        return 'Processing';
      case 'failed':
        return 'Payment failed';
      case 'returned':
        return 'Returned';
      case 'void':
        return 'Void';
      default:
        return status;
    }
  }

  Color get statusColor {
    switch (status) {
      case 'paid':
        return _joviMint;
      case 'pending':
        return _joviGold;
      case 'failed':
      case 'returned':
        return _joviErrorRed;
      default:
        return Colors.white70;
    }
  }
}

class _JoviInvoicesState extends State<JoviInvoices> with SingleTickerProviderStateMixin {
  List<_Invoice> _rows = [];
  bool _loading = true;
  StreamSubscription<QuerySnapshot<Map<String, dynamic>>>? _sub;
  late final AnimationController _fadeCtrl;
  final _money = NumberFormat.currency(locale: 'en_US', symbol: '\$');

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(vsync: this, duration: _Motion.enter);
    if (_platformReduceMotion()) { _fadeCtrl.value = 1; } else { _fadeCtrl.forward(); }
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) { _loading = false; return; }
    _sub = FirebaseFirestore.instance
        .collection('users').doc(uid).collection('invoices')
        .orderBy('issuedAt', descending: true).limit(120)
        .snapshots()
        .listen((s) {
      if (!mounted) return;
      setState(() { _rows = s.docs.map(_Invoice.fromDoc).toList(); _loading = false; });
    }, onError: (e) { debugPrint('Invoices: $e'); if (mounted) setState(() => _loading = false); });
  }

  @override
  void dispose() { _sub?.cancel(); _fadeCtrl.dispose(); super.dispose(); }

  String _fmt(DateTime? d) => d == null ? '—' : DateFormat('MMM d, yyyy').format(d);

  // ─── PDF ─────────────────────────────────────────────────────────────────
  Future<List<int>> _buildPdf(_Invoice inv) async {
    final doc = pw.Document(title: 'Jovi receipt ${inv.number}');
    final navy = pw_pdf.PdfColor.fromInt(0xFF1A2744);
    final coral = pw_pdf.PdfColor.fromInt(0xFFFF6B4A);
    final grey = pw_pdf.PdfColor.fromInt(0xFF6B7590);
    final c = inv.company;
    pw.Widget row(String a, String b, {bool bold = false}) => pw.Padding(
      padding: const pw.EdgeInsets.symmetric(vertical: 4),
      child: pw.Row(mainAxisAlignment: pw.MainAxisAlignment.spaceBetween, children: [
        pw.Text(a, style: pw.TextStyle(fontSize: 11, fontWeight: bold ? pw.FontWeight.bold : pw.FontWeight.normal)),
        pw.Text(b, style: pw.TextStyle(fontSize: 11, fontWeight: bold ? pw.FontWeight.bold : pw.FontWeight.normal)),
      ]));
    doc.addPage(pw.Page(
      pageFormat: pw_pdf.PdfPageFormat.letter,
      margin: const pw.EdgeInsets.all(48),
      build: (ctx) => pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
        pw.Row(mainAxisAlignment: pw.MainAxisAlignment.spaceBetween, crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
          pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
            pw.Text('jovi', style: pw.TextStyle(fontSize: 30, fontWeight: pw.FontWeight.bold, color: navy)),
            pw.Text((c['name'] as String?) ?? 'Jovi Health LLC', style: pw.TextStyle(fontSize: 10, color: grey)),
            pw.Text((c['site'] as String?) ?? 'jovihealth.com', style: pw.TextStyle(fontSize: 10, color: grey)),
            pw.Text((c['phone'] as String?) ?? '', style: pw.TextStyle(fontSize: 10, color: grey)),
          ]),
          pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.end, children: [
            pw.Text(inv.status == 'paid' ? 'RECEIPT' : 'INVOICE', style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold, color: coral)),
            pw.Text(inv.number, style: pw.TextStyle(fontSize: 11, color: grey)),
            pw.Text('Issued ${_fmt(inv.issuedAt)}', style: pw.TextStyle(fontSize: 10, color: grey)),
            if (inv.paidAt != null) pw.Text('Paid ${_fmt(inv.paidAt)}', style: pw.TextStyle(fontSize: 10, color: grey)),
          ]),
        ]),
        pw.SizedBox(height: 28),
        pw.Text('Billed to', style: pw.TextStyle(fontSize: 9, color: grey, letterSpacing: 1.2)),
        pw.Text(inv.memberName, style: pw.TextStyle(fontSize: 12, fontWeight: pw.FontWeight.bold)),
        if (inv.memberEmail != null) pw.Text(inv.memberEmail!, style: const pw.TextStyle(fontSize: 10)),
        if (inv.memberAddress != null) pw.Text(inv.memberAddress!, style: const pw.TextStyle(fontSize: 10)),
        pw.SizedBox(height: 22),
        pw.Container(
          decoration: pw.BoxDecoration(border: pw.Border(bottom: pw.BorderSide(color: grey, width: 0.5))),
          padding: const pw.EdgeInsets.only(bottom: 6),
          child: pw.Row(mainAxisAlignment: pw.MainAxisAlignment.spaceBetween, children: [
            pw.Text('Description', style: pw.TextStyle(fontSize: 9, color: grey, letterSpacing: 1.2)),
            pw.Text('Amount', style: pw.TextStyle(fontSize: 9, color: grey, letterSpacing: 1.2)),
          ])),
        ...inv.items.map((it) => row('${it['description'] ?? inv.title}', _money.format((it['price'] as num?)?.toDouble() ?? 0))),
        if (inv.periodStart != null) pw.Padding(padding: const pw.EdgeInsets.only(top: 2), child: pw.Text('Service period ${_fmt(inv.periodStart)} to ${_fmt(inv.periodEnd)}', style: pw.TextStyle(fontSize: 9, color: grey))),
        pw.SizedBox(height: 10),
        pw.Container(decoration: pw.BoxDecoration(border: pw.Border(top: pw.BorderSide(color: grey, width: 0.5))), padding: const pw.EdgeInsets.only(top: 8), child: pw.Column(children: [
          row('Total', _money.format(inv.total), bold: true),
          row('Amount paid', _money.format(inv.amountPaid)),
          row('Balance', _money.format(inv.total - inv.amountPaid)),
        ])),
        pw.SizedBox(height: 18),
        pw.Text('Payment method: Bank account (ACH)${inv.last4 != null ? ' ending in ${inv.last4}' : ''}', style: const pw.TextStyle(fontSize: 10)),
        pw.Text('Status: ${inv.statusLabel}${inv.reason != null && inv.status != 'paid' ? ' · ${inv.reason}' : ''}', style: const pw.TextStyle(fontSize: 10)),
        pw.Spacer(),
        pw.Text((c['note'] as String?) ?? 'Jovi is a healthcare membership, not insurance.', style: pw.TextStyle(fontSize: 9, color: grey)),
        pw.Text('Questions? ${(c['email'] as String?) ?? 'support@jovihealth.com'} · ${(c['phone'] as String?) ?? ''}', style: pw.TextStyle(fontSize: 9, color: grey)),
      ]),
    ));
    return doc.save();
  }

  Future<void> _share(_Invoice inv) async {
    HapticFeedback.lightImpact();
    try { final bytes = await _buildPdf(inv); await Printing.sharePdf(bytes: Uint8List.fromList(bytes), filename: 'jovi-${inv.number}.pdf'); }
    catch (e) { _toast('Could not create the PDF', error: true); }
  }

  Future<void> _print(_Invoice inv) async {
    HapticFeedback.lightImpact();
    try { final bytes = await _buildPdf(inv); await Printing.layoutPdf(onLayout: (_) async => Uint8List.fromList(bytes), name: 'jovi-${inv.number}'); }
    catch (e) { _toast('Could not print', error: true); }
  }

  void _toast(String msg, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(_joviToast(msg, accent: error ? _joviErrorRed : _joviMint, icon: error ? CupertinoIcons.exclamationmark_circle : CupertinoIcons.checkmark_circle));
  }

  // ─── UI ──────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context).size;
    final paidTotal = _rows.where((r) => r.status == 'paid').fold<double>(0, (a, r) => a + r.amountPaid);
    return Container(
      width: widget.width ?? mq.width,
      height: widget.height ?? mq.height,
      decoration: const BoxDecoration(gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [_joviNavy, _joviNavyDark])),
      child: SafeArea(
        child: FadeTransition(
          opacity: CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeOut),
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 8, 16, 4),
              child: Row(children: [
                _PressableMaterial(child: InkWell(
                  onTap: () { HapticFeedback.selectionClick(); if (Navigator.of(context).canPop()) Navigator.of(context).pop(); },
                  borderRadius: BorderRadius.circular(22),
                  child: Semantics(label: 'Back', button: true, child: Container(width: 44, height: 44, decoration: BoxDecoration(color: Colors.white.withOpacity(0.06), shape: BoxShape.circle, border: Border.all(color: Colors.white.withOpacity(0.14), width: 0.8)), child: Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white.withOpacity(0.85), size: 17))))),
                const SizedBox(width: 10),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  const Text('Invoices & receipts', style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w600, letterSpacing: -0.4, height: 1.1)),
                  const SizedBox(height: 1),
                  Text(_loading ? 'Loading…' : '${_rows.length} ${_rows.length == 1 ? 'record' : 'records'} · ${_money.format(paidTotal)} paid', style: const TextStyle(color: Color(0x88FFFFFF), fontSize: 11.5, fontWeight: FontWeight.w600)),
                ])),
                Container(width: 38, height: 38, decoration: BoxDecoration(gradient: const LinearGradient(colors: [_joviMint, _joviMintDark]), borderRadius: BorderRadius.circular(11)), child: const Icon(Icons.receipt_long_rounded, color: _joviNavy, size: 20)),
              ]),
            ),
            Expanded(child: _loading
              ? const Center(child: SizedBox(width: 28, height: 28, child: CircularProgressIndicator(strokeWidth: 2.5, valueColor: AlwaysStoppedAnimation<Color>(_joviMint))))
              : _rows.isEmpty
                ? _empty()
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                    itemCount: _rows.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (_, i) => _card(_rows[i]))),
          ]),
        ),
      ),
    );
  }

  Widget _empty() => Center(child: Padding(padding: const EdgeInsets.all(32), child: Column(mainAxisSize: MainAxisSize.min, children: [
    Container(width: 60, height: 60, decoration: BoxDecoration(color: Colors.white.withOpacity(0.06), shape: BoxShape.circle), child: Icon(Icons.receipt_long_rounded, color: Colors.white.withOpacity(0.5), size: 28)),
    const SizedBox(height: 14),
    const Text('No receipts yet', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w700, letterSpacing: -0.3)),
    const SizedBox(height: 6),
    Text('Your first membership payment will appear here once it is collected.', textAlign: TextAlign.center, style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 13, height: 1.4)),
  ])));

  Widget _card(_Invoice inv) => _PressableMaterial(child: InkWell(
    onTap: () => _openSheet(inv),
    borderRadius: BorderRadius.circular(16),
    child: ClipRRect(borderRadius: BorderRadius.circular(16), child: RepaintBoundary(child: Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.07), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withOpacity(0.12))),
      child: Row(children: [
        Container(width: 44, height: 44, decoration: BoxDecoration(color: inv.statusColor.withOpacity(0.16), borderRadius: BorderRadius.circular(13), border: Border.all(color: inv.statusColor.withOpacity(0.35), width: 0.8)),
          child: Icon(inv.kind == 'kurvpass' ? CupertinoIcons.bolt_fill : inv.kind.startsWith('pet') ? CupertinoIcons.paw : CupertinoIcons.creditcard, color: inv.statusColor, size: 20)),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Text(inv.title, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700, letterSpacing: -0.3)),
          const SizedBox(height: 2),
          Text('${inv.number} · ${_fmt(inv.paidAt ?? inv.issuedAt)}', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: Colors.white.withOpacity(0.55), fontSize: 12, fontWeight: FontWeight.w500)),
        ])),
        const SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
          Text(_money.format(inv.total), style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
          const SizedBox(height: 3),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3), decoration: BoxDecoration(color: inv.statusColor.withOpacity(0.14), borderRadius: BorderRadius.circular(9), border: Border.all(color: inv.statusColor.withOpacity(0.3), width: 0.8)),
            child: Text(inv.statusLabel, style: TextStyle(color: inv.statusColor, fontSize: 10.5, fontWeight: FontWeight.w700))),
        ]),
      ]),
    ))),
  ));

  Future<void> _openSheet(_Invoice inv) async {
    HapticFeedback.lightImpact();
    await showModalBottomSheet<void>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent, useSafeArea: true,
      builder: (ctx) => ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        child: Container(
          decoration: BoxDecoration(gradient: const LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [_joviNavy, _joviNavyDark]), border: Border.all(color: Colors.white.withOpacity(0.1))),
          child: SafeArea(top: false, child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 10, 20, 20),
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min, children: [
              Center(child: Container(width: 38, height: 4, decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(2)))),
              const SizedBox(height: 16),
              Text(inv.status == 'paid' ? 'Receipt' : 'Invoice', style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 12, fontWeight: FontWeight.w700, letterSpacing: 1.2)),
              const SizedBox(height: 4),
              Text(inv.title, style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w700, letterSpacing: -0.5)),
              Text('${inv.number} · issued ${_fmt(inv.issuedAt)}', style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 13)),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(color: Colors.white.withOpacity(0.06), borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.white.withOpacity(0.1))),
                child: Column(children: [
                  ...inv.items.map((it) => _kv('${it['description'] ?? inv.title}', _money.format((it['price'] as num?)?.toDouble() ?? 0))),
                  if (inv.periodStart != null) _kv('Service period', '${_fmt(inv.periodStart)} – ${_fmt(inv.periodEnd)}', muted: true),
                  Divider(color: Colors.white.withOpacity(0.12), height: 18),
                  _kv('Total', _money.format(inv.total), bold: true),
                  _kv('Paid', _money.format(inv.amountPaid)),
                  _kv('Method', 'Bank account (ACH)${inv.last4 != null ? ' •••• ${inv.last4}' : ''}'),
                  _kv('Status', inv.statusLabel, color: inv.statusColor),
                  if (inv.paidAt != null) _kv('Paid on', _fmt(inv.paidAt)),
                  if (inv.reason != null && inv.status != 'paid') _kv('Note', inv.reason!, muted: true),
                ]),
              ),
              const SizedBox(height: 16),
              Row(children: [
                Expanded(child: _Pressable(onTap: () => _share(inv), child: Container(padding: const EdgeInsets.symmetric(vertical: 14), decoration: BoxDecoration(gradient: const LinearGradient(colors: [_joviMint, _joviMintDark]), borderRadius: BorderRadius.circular(13)), child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(CupertinoIcons.share, color: _joviNavy, size: 18), SizedBox(width: 8), Text('Share PDF', style: TextStyle(color: _joviNavy, fontSize: 15, fontWeight: FontWeight.w600))])))),
                const SizedBox(width: 10),
                Expanded(child: _Pressable(onTap: () => _print(inv), child: Container(padding: const EdgeInsets.symmetric(vertical: 14), decoration: BoxDecoration(color: Colors.white.withOpacity(0.08), borderRadius: BorderRadius.circular(13), border: Border.all(color: Colors.white.withOpacity(0.16))), child: const Row(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(CupertinoIcons.printer, color: Colors.white, size: 18), SizedBox(width: 8), Text('Print', style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600))])))),
              ]),
              const SizedBox(height: 10),
              Text('Jovi is a healthcare membership, not insurance. Keep this receipt for your records.', textAlign: TextAlign.center, style: TextStyle(color: Colors.white.withOpacity(0.45), fontSize: 11.5)),
            ]),
          )),
        ),
      ),
    );
  }

  Widget _kv(String k, String v, {bool bold = false, bool muted = false, Color? color}) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(children: [
      Expanded(child: Text(k, style: TextStyle(color: Colors.white.withOpacity(muted ? 0.5 : 0.7), fontSize: 13.5))),
      Text(v, style: TextStyle(color: color ?? Colors.white, fontSize: bold ? 16 : 13.5, fontWeight: bold ? FontWeight.w700 : FontWeight.w600)),
    ]),
  );
}
