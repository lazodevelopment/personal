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
// JOVI HEALTH - HELP CENTER / CHAT (NAVY + GLASS)
// Version: 2026.09.22-r3 (Apple HIG refinement pass)
//
// r3 changes vs r2:
//  Cost / correctness
//  - Typing status wrote to Firestore on EVERY keystroke. Now writes only
//    on the idle→typing transition and once when typing stops.
//  - Every message bubble fetched the sender's user document afresh on
//    every rebuild (one read per message per keystroke on the staff side).
//    Role is now part of the cached UserProfile; no per-message reads.
//  - Every user-document update tore down and re-created all ticket
//    streams. They are now (re)built only when the role changes.
//  - Selected issue type was invisible: dropdown item text was navy on the
//    navy field. Items are now white on a navy menu.
//  - Send could get stuck spinning forever if an upload failed (no
//    try/catch). Now recovers with an error toast.
//  - The chat list jumped to the bottom on every rebuild, yanking a reader
//    who had scrolled up. It now scrolls only when a new message arrives
//    and the reader is already near the bottom (or sent it), animated.
//  - Removed two print() calls that logged members' phone numbers.
//  - Dropped every in-scroll BackdropFilter (11 of them, one per bubble).
//    They blurred a flat gradient at a saveLayer per item per frame.
//  Apple design
//  - Press feedback on pointer-down for chips, rows, radio cards, send.
//  - Long-press a bubble to copy its text, with haptic + toast.
//  - iOS-style typing indicator (three dots in a sine wave), 44 pt input
//    controls, arrow-up send button, drag-to-dismiss keyboard, message
//    field capped at five lines. Title case throughout, 17 pt semibold
//    nav title. Queue banner no longer invents a "5 minutes per person"
//    wait time. Reduce Motion honoured.
//  Flagged, not changed: members cannot type in "Live Chat" at all (the
//  input bar is staff-only and _sendMessage rejects non-team users), so a
//  member can only read agent replies. That looks like a product decision
//  worth revisiting before launch.
// ============================================================

import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:ui' as ui_dart;
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:image_picker/image_picker.dart';
import 'package:firebase_storage/firebase_storage.dart';
import 'package:intl/intl.dart';
import 'package:flutter/services.dart';
import 'package:file_picker/file_picker.dart';

// ─── Motion (Apple "response" values; critically damped, no overshoot) ──
class _Motion {
  static const Duration pressIn = Duration(milliseconds: 90);
  static const Duration pressOut = Duration(milliseconds: 260);
  static const Duration enter = Duration(milliseconds: 380);
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
    duration: duration ?? const Duration(milliseconds: 2200),
    backgroundColor: const Color(0xFF243352),
    elevation: 0,
    behavior: SnackBarBehavior.floating,
    margin: const EdgeInsets.fromLTRB(16, 0, 16, 24),
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

/// Jovi Health brand colors — [BrandColors] class retained for API
/// compatibility, but primary/dark/light repointed to the Jovi palette.
class BrandColors {
  // Jovi palette
  static const Color joviCoral = Color(0xFFFF6B4A);
  static const Color joviCoralLight = Color(0xFFFF8F73);
  static const Color joviCoralDark = Color(0xFFE5583A);
  static const Color joviNavy = Color(0xFF1A2744);
  static const Color joviNavyDark = Color(0xFF0F1A2E);
  static const Color joviNavyMid = Color(0xFF1F2B47);
  static const Color joviMint = Color(0xFF00D4AA);
  static const Color joviMintDark = Color(0xFF00B894);
  static const Color joviGold = Color(0xFFFFD166);
  static const Color joviGoldDark = Color(0xFFE6B84D);
  static const Color joviErrorRed = Color(0xFFE53935);

  // Legacy aliases (mapped to new palette)
  static const Color primary = joviCoral;
  static const Color dark = joviNavyDark;
  static const Color light = joviCoralLight;

  // Primary coral gradient
  static LinearGradient get primaryGradient => LinearGradient(
        colors: [joviCoral, joviCoralDark],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );

  // Soft coral tint (was lightGradient)
  static LinearGradient get lightGradient => LinearGradient(
        colors: [joviCoral.withOpacity(0.08), joviCoralDark.withOpacity(0.04)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );

  // Navy gradient for scaffold
  static LinearGradient get navyGradient => LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [joviNavy, joviNavy, joviNavyDark],
      );
}

enum TicketPriority {
  critical(color: Color(0xFFEF4444), responseTime: '5 min', icon: Icons.error),
  high(color: Color(0xFFFB923C), responseTime: '30 min', icon: Icons.warning),
  medium(color: Color(0xFFFFD166), responseTime: '2 hours', icon: Icons.info),
  low(
      color: Color(0xFF00D4AA),
      responseTime: '24 hours',
      icon: Icons.check_circle);

  final Color color;
  final String responseTime;
  final IconData icon;

  const TicketPriority({
    required this.color,
    required this.responseTime,
    required this.icon,
  });
}

class UserProfile {
  final String displayName;
  final String photoUrl;
  final String email;
  final String phone;
  final bool hasKurvPass;
  final bool isPremium;
  final List<String> allergies;
  final String? onboardConditions;
  final bool tobacco;
  final bool dental;
  final bool vision;
  final int? age;
  final String? memberId;
  final List<String> members;
  final bool isTeam; // role == 'team' (cached so bubbles need no reads)

  UserProfile({
    required this.displayName,
    required this.photoUrl,
    required this.email,
    required this.phone,
    this.hasKurvPass = false,
    this.isPremium = false,
    this.allergies = const [],
    this.onboardConditions,
    this.tobacco = false,
    this.dental = false,
    this.vision = false,
    this.age,
    this.memberId,
    this.members = const [],
    this.isTeam = false,
  });

  factory UserProfile.fromMap(Map<String, dynamic> data) {
    String displayName = data['display_name'] ?? '';
    if (displayName.isEmpty) {
      final first =
          data['first'] ?? data['onboard_fullName']?.split(' ').first ?? '';
      final last =
          data['last'] ?? data['onboard_fullName']?.split(' ').last ?? '';
      displayName = '$first $last'.trim();
    }
    if (displayName.isEmpty) displayName = 'User';

    List<String> membersList = [];
    if (data['members'] != null && data['members'] is List) {
      membersList = List<String>.from(data['members']);
    }
    if (data['deps'] != null && data['deps'] is List) {
      membersList.addAll(List<String>.from(data['deps']));
    }

    List<String> allergiesList = [];
    if (data['allergies'] != null && data['allergies'] is List) {
      allergiesList = List<String>.from(data['allergies']);
    }

    return UserProfile(
      displayName: displayName,
      photoUrl: data['photo_url'] ?? '',
      email: data['email'] ?? '',
      phone: data['phone'] ??
          data['phone_number'] ??
          data['onboard_phone'] ??
          data['onboard_emPhone'] ??
          '',
      hasKurvPass: data['hasKurvPass'] ?? false,
      isPremium: data['premium'] != null && data['premium'] > 0,
      allergies: allergiesList,
      onboardConditions: data['onboard_conditions'],
      tobacco: data['tobacco'] ?? false,
      dental: data['dental'] ?? false,
      vision: data['vision'] ?? false,
      age: data['age'],
      memberId: data['memberId'],
      members: membersList,
      isTeam: data['role'] == 'team',
    );
  }
}

class CannedResponse {
  final String id;
  final String title;
  final String message;
  final String category;
  final String shortcut;

  CannedResponse({
    required this.id,
    required this.title,
    required this.message,
    required this.category,
    required this.shortcut,
  });
}

/// Modern MessageBubble — navy glass for received, coral for sent
class MessageBubble extends StatelessWidget {
  final String? text;
  final String? imageUrl;
  final String? fileUrl;
  final String? fileName;
  final DateTime? timestamp;
  final bool isMe;
  final String avatarUrl;
  final bool isLastSentByMe;
  final bool readByRecipient;
  final String senderName;
  final bool isStaff;
  final ResponsiveConfig layoutSettings;

  const MessageBubble({
    Key? key,
    this.text,
    this.imageUrl,
    this.fileUrl,
    this.fileName,
    this.timestamp,
    required this.isMe,
    required this.avatarUrl,
    this.isLastSentByMe = false,
    this.readByRecipient = false,
    required this.senderName,
    this.isStaff = false,
    required this.layoutSettings,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final timeLabel =
        timestamp == null ? '' : DateFormat.jm().format(timestamp!);

    return Padding(
      padding: EdgeInsets.symmetric(
        vertical: layoutSettings.paddingV * 0.3,
        horizontal: layoutSettings.paddingH * 0.6,
      ),
      child: Column(
        crossAxisAlignment:
            isMe ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          // Staff name badge above received messages
          if (!isMe && isStaff)
            Padding(
              padding: EdgeInsets.only(
                left: layoutSettings.actionIconDimension + 16,
                bottom: layoutSettings.paddingV * 0.2,
              ),
              child: Container(
                padding: EdgeInsets.symmetric(
                  horizontal: layoutSettings.paddingH * 0.4,
                  vertical: layoutSettings.paddingV * 0.15,
                ),
                decoration: BoxDecoration(
                  color: BrandColors.joviCoral.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                      color: BrandColors.joviCoral.withOpacity(0.35)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.support_agent,
                        size: layoutSettings.actionIconDimension * 0.4,
                        color: BrandColors.joviCoral),
                    SizedBox(width: layoutSettings.paddingH * 0.2),
                    Text(
                      senderName,
                      style: TextStyle(
                        fontSize: layoutSettings.actionTextSize - 1,
                        fontWeight: FontWeight.w600,
                        color: BrandColors.joviCoral,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          Row(
            mainAxisAlignment:
                isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isMe)
                Container(
                  margin: EdgeInsets.only(right: layoutSettings.paddingH * 0.4),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isStaff
                          ? BrandColors.joviCoral.withOpacity(0.5)
                          : Colors.white.withOpacity(0.2),
                      width: 2,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: isStaff
                            ? BrandColors.joviCoral.withOpacity(0.25)
                            : Colors.black.withOpacity(0.25),
                        blurRadius: 8,
                        offset: Offset(0, 2),
                      ),
                    ],
                  ),
                  child: CircleAvatar(
                    radius: layoutSettings.actionIconDimension * 0.64,
                    backgroundColor: BrandColors.joviNavyDark,
                    backgroundImage:
                        avatarUrl.isNotEmpty ? NetworkImage(avatarUrl) : null,
                    child: avatarUrl.isEmpty
                        ? Icon(
                            isStaff ? Icons.support_agent : Icons.person,
                            size: layoutSettings.actionIconDimension * 0.64,
                            color: isStaff
                                ? BrandColors.joviCoral
                                : Colors.white.withOpacity(0.6),
                          )
                        : null,
                  ),
                ),
              Flexible(
                child: Semantics(
                  label:
                      '${isMe ? 'You' : senderName}${timeLabel.isEmpty ? '' : ', $timeLabel'}: ${text ?? ''}${imageUrl != null ? ' (photo)' : ''}${fileUrl != null ? ' (attachment)' : ''}',
                  child: GestureDetector(
                  // Long-press copies the text, as in Messages.
                  onLongPress: (text == null || text!.isEmpty)
                      ? null
                      : () {
                          Clipboard.setData(ClipboardData(text: text!));
                          HapticFeedback.mediumImpact();
                          final messenger = ScaffoldMessenger.maybeOf(context);
                          messenger?.hideCurrentSnackBar();
                          messenger?.showSnackBar(_joviToast('Message copied',
                              accent: BrandColors.joviMint,
                              icon: Icons.check_circle_rounded));
                        },
                  child: Container(
                  constraints: BoxConstraints(
                      maxWidth: MediaQuery.of(context).size.width *
                          (layoutSettings.wideMode ? 0.6 : 0.7)),
                  decoration: BoxDecoration(
                    gradient: isMe ? BrandColors.primaryGradient : null,
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(18),
                      topRight: Radius.circular(18),
                      bottomLeft:
                          isMe ? Radius.circular(18) : Radius.circular(4),
                      bottomRight:
                          isMe ? Radius.circular(4) : Radius.circular(18),
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: isMe
                            ? BrandColors.joviCoral.withOpacity(0.4)
                            : Colors.black.withOpacity(0.25),
                        blurRadius: isMe ? 14 : 10,
                        offset: Offset(0, isMe ? 5 : 3),
                      ),
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(18),
                      topRight: Radius.circular(18),
                      bottomLeft:
                          isMe ? Radius.circular(18) : Radius.circular(4),
                      bottomRight:
                          isMe ? Radius.circular(4) : Radius.circular(18),
                    ),
                    child: RepaintBoundary(
                      child: Container(
                        padding: EdgeInsets.all(layoutSettings.paddingH * 0.75),
                        decoration: BoxDecoration(
                          color: isMe ? null : Colors.white.withOpacity(0.08),
                          border: isMe
                              ? null
                              : Border.all(
                                  color: Colors.white.withOpacity(0.12),
                                  width: 1,
                                ),
                        ),
                        child: Column(
                          crossAxisAlignment: isMe
                              ? CrossAxisAlignment.end
                              : CrossAxisAlignment.start,
                          children: [
                            if (imageUrl != null)
                              ClipRRect(
                                borderRadius: BorderRadius.circular(12),
                                child: Image.network(
                                  imageUrl!,
                                  width: layoutSettings.wideMode ? 250 : 200,
                                  fit: BoxFit.cover,
                                  loadingBuilder: (ctx, child, progress) {
                                    if (progress == null) return child;
                                    return Container(
                                      width:
                                          layoutSettings.wideMode ? 250 : 200,
                                      height:
                                          layoutSettings.wideMode ? 250 : 200,
                                      decoration: BoxDecoration(
                                        color: Colors.white.withOpacity(0.05),
                                        borderRadius: BorderRadius.circular(12),
                                      ),
                                      child: Center(
                                        child: CircularProgressIndicator(
                                          value: progress.expectedTotalBytes !=
                                                  null
                                              ? progress.cumulativeBytesLoaded /
                                                  progress.expectedTotalBytes!
                                              : null,
                                          color: Colors.white,
                                          strokeWidth: 2,
                                        ),
                                      ),
                                    );
                                  },
                                ),
                              ),
                            if (fileUrl != null)
                              Container(
                                padding: EdgeInsets.all(
                                    layoutSettings.paddingH * 0.6),
                                decoration: BoxDecoration(
                                  color: isMe
                                      ? Colors.white.withOpacity(0.2)
                                      : Colors.white.withOpacity(0.1),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(
                                      Icons.attach_file,
                                      color: Colors.white,
                                      size: layoutSettings.actionIconDimension *
                                          0.7,
                                    ),
                                    SizedBox(
                                        width: layoutSettings.paddingH * 0.4),
                                    Flexible(
                                      child: Text(
                                        fileName ?? 'Attachment',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w600,
                                          fontSize:
                                              layoutSettings.actionTextSize + 1,
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            if ((imageUrl != null || fileUrl != null) &&
                                text != null &&
                                text!.isNotEmpty)
                              SizedBox(height: layoutSettings.paddingV * 0.5),
                            if (text != null && text!.isNotEmpty)
                              Text(
                                text!,
                                style: const TextStyle(
                                  fontSize: 16,
                                  color: Colors.white,
                                  height: 1.35,
                                  letterSpacing: -0.2,
                                ),
                              ),
                            if (timeLabel.isNotEmpty)
                              Padding(
                                padding: EdgeInsets.only(
                                    top: layoutSettings.paddingV * 0.3),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Text(
                                      timeLabel,
                                      style: TextStyle(
                                        fontSize:
                                            layoutSettings.actionTextSize - 2,
                                        color: isMe
                                            ? Colors.white.withOpacity(0.8)
                                            : Colors.white.withOpacity(0.45),
                                      ),
                                    ),
                                    if (isLastSentByMe) ...[
                                      SizedBox(
                                          width: layoutSettings.paddingH * 0.2),
                                      Icon(
                                        readByRecipient
                                            ? Icons.done_all
                                            : Icons.check,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.5,
                                        color: readByRecipient
                                            ? Colors.white
                                            : Colors.white.withOpacity(0.7),
                                      ),
                                    ],
                                  ],
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
              ),
              if (isMe)
                Container(
                  margin: EdgeInsets.only(left: layoutSettings.paddingH * 0.4),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: BrandColors.primaryGradient,
                    boxShadow: [
                      BoxShadow(
                        color: BrandColors.joviCoral.withOpacity(0.4),
                        blurRadius: 10,
                        offset: Offset(0, 3),
                      ),
                    ],
                  ),
                  child: CircleAvatar(
                    radius: layoutSettings.actionIconDimension * 0.64,
                    backgroundColor: Colors.transparent,
                    backgroundImage:
                        avatarUrl.isNotEmpty ? NetworkImage(avatarUrl) : null,
                    child: avatarUrl.isEmpty
                        ? Icon(Icons.person,
                            size: layoutSettings.actionIconDimension * 0.64,
                            color: Colors.white)
                        : null,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class TypingIndicator extends StatefulWidget {
  final ResponsiveConfig layoutSettings;

  const TypingIndicator({Key? key, required this.layoutSettings})
      : super(key: key);

  @override
  _TypingIndicatorState createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  bool _reduceMotion = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1100),
      vsync: this,
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = MediaQuery.of(context).disableAnimations;
    if (_reduceMotion) {
      _controller.stop();
      _controller.value = 0.0;
    } else if (!_controller.isAnimating) {
      _controller.repeat();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dot = widget.layoutSettings.actionIconDimension * 0.28;
    return Semantics(
      liveRegion: true,
      label: 'Support is typing',
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: widget.layoutSettings.paddingH * 0.8,
          vertical: widget.layoutSettings.paddingV * 0.4,
        ),
        child: Row(
          children: [
            Text(
              'Support is typing',
              style: TextStyle(
                fontSize: widget.layoutSettings.actionTextSize,
                color: Colors.white.withOpacity(0.65),
              ),
            ),
            SizedBox(width: widget.layoutSettings.paddingH * 0.4),
            AnimatedBuilder(
              animation: _controller,
              builder: (context, child) {
                return Row(
                  children: List.generate(3, (index) {
                    // Three dots on one sine wave, each a fifth of a cycle
                    // behind the last — the Messages-style ripple.
                    final t = _controller.value - index * 0.2;
                    final wave = _reduceMotion
                        ? 0.5
                        : 0.5 + 0.5 * math.sin(2 * math.pi * t);
                    return Transform.translate(
                      offset: Offset(0, -2.5 * wave),
                      child: Container(
                        margin: EdgeInsets.symmetric(
                            horizontal: widget.layoutSettings.paddingH * 0.1),
                        width: dot,
                        height: dot,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: BrandColors.joviCoral
                              .withOpacity(0.35 + 0.65 * wave),
                        ),
                      ),
                    );
                  }),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class ChatWidget extends StatefulWidget {
  final double width;
  final double height;

  const ChatWidget({
    Key? key,
    required this.width,
    required this.height,
  }) : super(key: key);

  @override
  _ChatWidgetState createState() => _ChatWidgetState();
}

class _ChatWidgetState extends State<ChatWidget> with TickerProviderStateMixin {
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

  final _auth = FirebaseAuth.instance;
  late final String _uid;

  String? _userRole;
  StreamSubscription<DocumentSnapshot>? _userSub;
  UserProfile? _currentUserProfile;

  DocumentSnapshot? _openTicketSnap;
  StreamSubscription<QuerySnapshot>? _openTicketSub;
  List<DocumentSnapshot> _closedTickets = [];
  StreamSubscription<QuerySnapshot>? _closedTicketsSub;
  List<DocumentSnapshot> _allOpenTickets = [];
  StreamSubscription<QuerySnapshot>? _allOpenTicketsSub;

  String? _viewingTranscriptTicketId;
  bool _showingConfirmation = false;
  String? _confirmationContactMethod;

  bool _agentIsTyping = false;
  Timer? _typingTimer;
  StreamSubscription<DocumentSnapshot>? _typingSubscription;

  final _formKey = GlobalKey<FormState>();
  final TextEditingController _nameCtrl = TextEditingController();
  final TextEditingController _phoneCtrl = TextEditingController();
  final TextEditingController _emailCtrl = TextEditingController();
  final TextEditingController _issueDescriptionCtrl = TextEditingController();
  String? _selectedIssueType;
  String? _selectedContactMethod;
  TicketPriority _selectedPriority = TicketPriority.medium;
  bool _isSubmittingTicket = false;
  bool _showContactMethodError = false; // only after a submit attempt

  bool _reduceMotion = false; // MediaQuery.disableAnimations
  bool _subscriptionsReady = false;
  bool _typingSent = false; // last agentTyping value we wrote
  int _lastMessageCount = 0; // for auto-scroll decisions
  final Map<String, Future<DocumentSnapshot>> _ticketDocCache = {};

  final Map<String, TicketPriority> _issueTypePriority = {
    'Medical Emergency': TicketPriority.critical,
    'Urgent Medical Question': TicketPriority.high,
    'Billing Issue': TicketPriority.medium,
    'Technical Support': TicketPriority.medium,
    'Appointment Scheduling': TicketPriority.low,
    'General Question': TicketPriority.low,
    'Account Issue': TicketPriority.medium,
    'Report a Bug': TicketPriority.high,
    'Medication Refill': TicketPriority.high,
    'Other': TicketPriority.medium,
  };

  final List<String> _contactMethods = ['Chat', 'Email', 'Phone'];

  final List<CannedResponse> _cannedResponses = [
    CannedResponse(
      id: '1',
      title: 'Greeting',
      message:
          'Hello! Thank you for contacting Jovi Health support. I\'m reviewing your issue and will assist you shortly.',
      category: 'Greeting',
      shortcut: '/hello',
    ),
    CannedResponse(
      id: '2',
      title: 'Investigating',
      message:
          'I\'m looking into this for you. Please give me a moment to review your account.',
      category: 'Status',
      shortcut: '/check',
    ),
    CannedResponse(
      id: '3',
      title: 'Need More Info',
      message:
          'To better assist you, could you please provide more details about the issue you\'re experiencing?',
      category: 'Request',
      shortcut: '/info',
    ),
    CannedResponse(
      id: '4',
      title: 'Resolved',
      message:
          'I\'ve resolved the issue for you. Is there anything else I can help you with today?',
      category: 'Resolution',
      shortcut: '/resolved',
    ),
    CannedResponse(
      id: '5',
      title: 'Appointment Confirmed',
      message:
          'Your appointment has been confirmed. You\'ll receive a confirmation email shortly with all the details.',
      category: 'Appointment',
      shortcut: '/confirmed',
    ),
  ];

  final TextEditingController _messageCtrl = TextEditingController();
  bool _isSendingMessage = false;
  XFile? _pickedImage;
  PlatformFile? _pickedFile;
  bool _showCannedResponses = false;
  List<CannedResponse> _filteredCannedResponses = [];

  final ScrollController _scrollController = ScrollController();

  final Map<String, UserProfile> _userCache = {};

  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  int? _queuePosition;
  StreamSubscription<QuerySnapshot>? _queueSubscription;

  @override
  void initState() {
    super.initState();
    final user = _auth.currentUser!;
    _uid = user.uid;

    _fadeController =
        AnimationController(duration: _Motion.enter, vsync: this);
    _slideController =
        AnimationController(duration: _Motion.enter, vsync: this);

    _fadeAnimation =
        CurvedAnimation(parent: _fadeController, curve: _Motion.settle);
    // A 3% rise reads as content settling; the old 10% read as movement.
    _slideAnimation =
        Tween<Offset>(begin: const Offset(0, 0.03), end: Offset.zero).animate(
            CurvedAnimation(parent: _slideController, curve: _Motion.settle));

    _fadeController.forward();
    _slideController.forward();

    _userSub = FirebaseFirestore.instance
        .collection('users')
        .doc(_uid)
        .snapshots()
        .listen((snap) {
      if (!snap.exists) return;
      final data = snap.data()!;
      if (!mounted) return;
      final newRole = data['role'] as String?;
      final roleChanged = newRole != _userRole || !_subscriptionsReady;
      final profile = UserProfile.fromMap(data);
      setState(() {
        _userRole = newRole;
        _currentUserProfile = profile;
      });
      _userCache[_uid] = profile;
      // (Re)subscribe only when the role changes. r2 tore down and re-created
      // every ticket stream each time the user document changed.
      if (roleChanged) {
        _subscriptionsReady = true;
        _setupSubscriptions();
      }

      setState(() {
        if (_nameCtrl.text.isEmpty &&
            _currentUserProfile?.displayName != null) {
          _nameCtrl.text = _currentUserProfile!.displayName;
        }
        if (_phoneCtrl.text.isEmpty &&
            _currentUserProfile?.phone != null &&
            _currentUserProfile!.phone.isNotEmpty) {
          _phoneCtrl.text = _currentUserProfile!.phone;
        }
        if (_emailCtrl.text.isEmpty) {
          _emailCtrl.text = _currentUserProfile?.email ?? user.email ?? '';
        }
      });
    });

    _messageCtrl.addListener(() {
      if (_userRole == 'team') {
        final text = _messageCtrl.text;
        if (text.startsWith('/')) {
          setState(() {
            _showCannedResponses = true;
            final query = text.substring(1).toLowerCase();
            _filteredCannedResponses = _cannedResponses
                .where((r) =>
                    r.shortcut.toLowerCase().contains(query) ||
                    r.title.toLowerCase().contains(query))
                .toList();
          });
        } else {
          setState(() {
            _showCannedResponses = false;
            _filteredCannedResponses = [];
          });
        }
      }
      setState(() {});
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = MediaQuery.of(context).disableAnimations;
    if (_reduceMotion) {
      if (_fadeController.value != 1.0) _fadeController.value = 1.0;
      if (_slideController.value != 1.0) _slideController.value = 1.0;
    }
    analyzeScreenConfiguration();
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

  void _setupSubscriptions() {
    _openTicketSub?.cancel();
    _closedTicketsSub?.cancel();
    _allOpenTicketsSub?.cancel();
    _queueSubscription?.cancel();

    if (_userRole == 'team') {
      _allOpenTicketsSub = FirebaseFirestore.instance
          .collection('helpTickets')
          .where('status', isEqualTo: 'open')
          .orderBy('priority', descending: true)
          .orderBy('createdAt', descending: false)
          .snapshots()
          .listen((snap) {
        setState(() {
          _allOpenTickets = snap.docs;
        });
      });
      setState(() {
        _openTicketSnap = null;
        _closedTickets = [];
      });
    } else {
      _openTicketSub = FirebaseFirestore.instance
          .collection('helpTickets')
          .where('userId', isEqualTo: _uid)
          .where('status', isEqualTo: 'open')
          .limit(1)
          .snapshots()
          .listen((snap) {
        if (snap.docs.isNotEmpty) {
          setState(() {
            _openTicketSnap = snap.docs.first;
            final data = snap.docs.first.data() as Map<String, dynamic>;
            if (data['contactMethod'] == 'Chat') {
              _showingConfirmation = false;
              _setupTypingListener(snap.docs.first.id);
              _calculateQueuePosition(snap.docs.first.id);
            }
          });
        } else {
          setState(() {
            _openTicketSnap = null;
          });
        }
      });

      _closedTicketsSub = FirebaseFirestore.instance
          .collection('helpTickets')
          .where('userId', isEqualTo: _uid)
          .where('status', isEqualTo: 'closed')
          .orderBy('createdAt', descending: true)
          .snapshots()
          .listen((snap) {
        setState(() {
          _closedTickets = snap.docs;
        });
      });

      setState(() {
        _allOpenTickets = [];
      });
    }
  }

  void _setupTypingListener(String ticketId) {
    _typingSubscription?.cancel();
    _typingSubscription = FirebaseFirestore.instance
        .collection('helpTickets')
        .doc(ticketId)
        .snapshots()
        .listen((snap) {
      if (snap.exists) {
        final data = snap.data() as Map<String, dynamic>;
        setState(() {
          _agentIsTyping = data['agentTyping'] ?? false;
        });
      }
    });
  }

  void _calculateQueuePosition(String ticketId) async {
    _queueSubscription?.cancel();
    _queueSubscription = FirebaseFirestore.instance
        .collection('helpTickets')
        .where('status', isEqualTo: 'open')
        .where('contactMethod', isEqualTo: 'Chat')
        .where('assignedTo', isEqualTo: null)
        .orderBy('createdAt')
        .snapshots()
        .listen((snap) {
      int position = 0;
      for (var doc in snap.docs) {
        position++;
        if (doc.id == ticketId) {
          setState(() {
            _queuePosition = position;
          });
          break;
        }
      }
    });
  }

  /// Writes agentTyping only on transitions. r2 wrote on every keystroke.
  Future<void> _updateTypingStatus(String ticketId, bool isTyping) async {
    if (_userRole != 'team') return;
    _typingTimer?.cancel();

    final ref = FirebaseFirestore.instance.collection('helpTickets').doc(ticketId);

    if (isTyping) {
      if (!_typingSent) {
        _typingSent = true;
        try {
          await ref.update({'agentTyping': true});
        } catch (_) {}
      }
      _typingTimer = Timer(const Duration(seconds: 3), () {
        _typingSent = false;
        ref.update({'agentTyping': false}).catchError((_) {});
      });
    } else if (_typingSent) {
      _typingSent = false;
      try {
        await ref.update({'agentTyping': false});
      } catch (_) {}
    }
  }

  /// One ticket read per ticket, not one per rebuild.
  Future<DocumentSnapshot> _ticketDoc(String ticketId) {
    return _ticketDocCache[ticketId] ??=
        FirebaseFirestore.instance.collection('helpTickets').doc(ticketId).get();
  }

  /// Builds with the sender's cached profile synchronously when we have it
  /// (no one-frame "User" flash on every rebuild), otherwise fetches once.
  Widget _withProfile(String userId, Widget Function(UserProfile) builder) {
    final cached = _userCache[userId];
    if (cached != null) return builder(cached);
    return FutureBuilder<UserProfile>(
      future: _getUserProfile(userId),
      builder: (ctx, snap) => builder(snap.data ??
          UserProfile(displayName: 'User', photoUrl: '', email: '', phone: '')),
    );
  }

  void _toast(String message,
      {bool isError = false, bool isSuccess = false}) {
    final messenger = ScaffoldMessenger.maybeOf(context);
    if (messenger == null) return;
    final accent = isError
        ? const Color(0xFFFF8A80)
        : (isSuccess ? BrandColors.joviMint : BrandColors.joviCoral);
    messenger.hideCurrentSnackBar();
    messenger.showSnackBar(_joviToast(
      message,
      accent: accent,
      icon: isError
          ? Icons.error_rounded
          : (isSuccess ? Icons.check_circle_rounded : Icons.info_rounded),
      duration: isError
          ? const Duration(milliseconds: 3500)
          : const Duration(milliseconds: 2200),
    ));
  }

  @override
  void dispose() {
    _userSub?.cancel();
    _openTicketSub?.cancel();
    _closedTicketsSub?.cancel();
    _allOpenTicketsSub?.cancel();
    _queueSubscription?.cancel();
    _typingSubscription?.cancel();
    _typingTimer?.cancel();
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _emailCtrl.dispose();
    _issueDescriptionCtrl.dispose();
    _messageCtrl.dispose();
    _scrollController.dispose();
    _fadeController.dispose();
    _slideController.dispose();
    super.dispose();
  }

  Future<void> _assignTicketIfNeeded(String ticketId) async {
    final ticketRef =
        FirebaseFirestore.instance.collection('helpTickets').doc(ticketId);
    final doc = await ticketRef.get();
    if (!doc.exists) return;
    final data = doc.data()!;
    if (data['assignedTo'] == null) {
      await ticketRef.update({
        'assignedTo': _uid,
        'assignedAt': FieldValue.serverTimestamp(),
      });
    }
  }

  Future<UserProfile> _getUserProfile(String userId) async {
    if (_userCache.containsKey(userId)) {
      return _userCache[userId]!;
    }
    final snap =
        await FirebaseFirestore.instance.collection('users').doc(userId).get();
    if (snap.exists && snap.data() != null) {
      final profile = UserProfile.fromMap(snap.data()!);
      _userCache[userId] = profile;
      return profile;
    }
    final fallback =
        UserProfile(displayName: 'User', photoUrl: '', email: '', phone: '');
    _userCache[userId] = fallback;
    return fallback;
  }

  Future<void> _sendMessage(String ticketId) async {
    if (_isSendingMessage) return;
    final text = _messageCtrl.text.trim();
    if (text.isEmpty && _pickedImage == null && _pickedFile == null) return;

    if (_userRole != 'team') {
      _toast('Please wait for a support agent to respond');
      return;
    }

    setState(() => _isSendingMessage = true);
    HapticFeedback.selectionClick();

    try {
      final chatRef = FirebaseFirestore.instance
          .collection('helpTickets')
          .doc(ticketId)
          .collection('messages');

      await _assignTicketIfNeeded(ticketId);

      final msgData = {
        'senderId': _uid,
        'text': text,
        'timestamp': FieldValue.serverTimestamp(),
        'readByUser': false,
        'readByTeam': true,
      };

      if (_pickedImage != null) {
        final storageRef = FirebaseStorage.instance.ref().child(
            'helpTickets/$ticketId/${DateTime.now().millisecondsSinceEpoch}.jpg');
        final bytes = await _pickedImage!.readAsBytes();
        final task = await storageRef.putData(bytes);
        final url = await task.ref.getDownloadURL();
        msgData['imageUrl'] = url;
      }

      if (_pickedFile != null) {
        final fileBytes = _pickedFile!.bytes;
        if (fileBytes == null) {
          throw Exception('Could not read the selected file');
        }
        final storageRef = FirebaseStorage.instance.ref().child(
            'helpTickets/$ticketId/files/${DateTime.now().millisecondsSinceEpoch}_${_pickedFile!.name}');
        final task = await storageRef.putData(fileBytes);
        final url = await task.ref.getDownloadURL();
        msgData['fileUrl'] = url;
        msgData['fileName'] = _pickedFile!.name;
      }

      await chatRef.add(msgData);
      if (!mounted) return;
      _messageCtrl.clear();
      _pickedImage = null;
      _pickedFile = null;
      HapticFeedback.mediumImpact();
      _updateTypingStatus(ticketId, false);
    } catch (e) {
      // r2 had no error path: a failed upload left the send button spinning
      // forever.
      if (mounted) _toast('Couldn’t send. Please try again.', isError: true);
    } finally {
      if (mounted) setState(() => _isSendingMessage = false);
    }
  }

  Future<void> _submitHelpTicket() async {
    if (!_formKey.currentState!.validate()) return;
    if (_isSubmittingTicket) return;
    setState(() => _isSubmittingTicket = true);
    HapticFeedback.selectionClick();

    final priority =
        _issueTypePriority[_selectedIssueType] ?? TicketPriority.medium;

    final finalPriority = (_currentUserProfile?.hasKurvPass ?? false) &&
            priority != TicketPriority.critical
        ? TicketPriority.values[priority.index - 1]
        : priority;

    final newTicketRef =
        FirebaseFirestore.instance.collection('helpTickets').doc();

    await newTicketRef.set({
      'userId': _uid,
      'userName': _nameCtrl.text.trim(),
      'phone': _phoneCtrl.text.trim(),
      'email': _emailCtrl.text.trim(),
      'issueType': _selectedIssueType,
      'issueDescription': _issueDescriptionCtrl.text.trim(),
      'contactMethod': _selectedContactMethod,
      'status': 'open',
      'priority': finalPriority.index,
      'priorityLevel': finalPriority.name,
      'responseTime': finalPriority.responseTime,
      'hasKurvPass': _currentUserProfile?.hasKurvPass ?? false,
      'isPremium': _currentUserProfile?.isPremium ?? false,
      'createdAt': FieldValue.serverTimestamp(),
      'assignedTo': null,
      'agentTyping': false,
    });

    setState(() {
      _isSubmittingTicket = false;
      _showingConfirmation = true;
      _confirmationContactMethod = _selectedContactMethod;
    });

    _issueDescriptionCtrl.clear();
    _selectedIssueType = null;
    _selectedContactMethod = null;

    HapticFeedback.mediumImpact();
  }

  void _viewTranscript(String ticketId) async {
    HapticFeedback.lightImpact();
    if (_userRole == 'team') {
      await _assignTicketIfNeeded(ticketId);
    }
    setState(() {
      _viewingTranscriptTicketId = ticketId;
    });
  }

  void _exitTranscriptView() {
    HapticFeedback.lightImpact();
    setState(() {
      _viewingTranscriptTicketId = null;
    });
  }

  void _applyCannedResponse(CannedResponse response) {
    _messageCtrl.text = response.message;
    setState(() {
      _showCannedResponses = false;
    });
  }

  // ═══════════════════════════════════════════════════════════════
  // Form field helpers — navy glass variants
  // ═══════════════════════════════════════════════════════════════

  Widget _buildStyledTextField(
    TextEditingController controller,
    String label,
    String hint,
    IconData icon, {
    int maxLines = 1,
    TextInputType? keyboardType,
    String? Function(String?)? validator,
  }) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 10,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: RepaintBoundary(
                      child: Container(
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.07),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white.withOpacity(0.15)),
            ),
            child: TextFormField(
              controller: controller,
              maxLines: maxLines,
              keyboardType: keyboardType,
              validator: validator,
              cursorColor: BrandColors.joviCoral,
              style: TextStyle(
                color: Colors.white,
                fontSize: layoutSettings.actionTextSize + 1,
              ),
              decoration: InputDecoration(
                labelText: label,
                hintText: hint,
                labelStyle: TextStyle(
                  color: Colors.white.withOpacity(0.7),
                ),
                floatingLabelStyle: TextStyle(
                  color: BrandColors.joviCoral,
                  fontWeight: FontWeight.w600,
                ),
                hintStyle: TextStyle(
                  fontSize: layoutSettings.actionTextSize + 1,
                  color: Colors.white.withOpacity(0.4),
                ),
                prefixIcon: Icon(icon,
                    color: BrandColors.joviCoral,
                    size: layoutSettings.actionIconDimension),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide:
                      BorderSide(color: BrandColors.joviCoral, width: 2),
                ),
                errorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide:
                      BorderSide(color: BrandColors.joviErrorRed, width: 2),
                ),
                focusedErrorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide:
                      BorderSide(color: BrandColors.joviErrorRed, width: 2),
                ),
                errorStyle: TextStyle(
                  color: Color(0xFFFF8A80),
                  fontSize: layoutSettings.actionTextSize - 1,
                ),
                filled: false,
                contentPadding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStyledDropdown(
    String label,
    IconData icon,
    String? value,
    List<String> items,
    Function(String?) onChanged,
    String? Function(String?)? validator,
  ) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.2),
            blurRadius: 10,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(14),
        child: RepaintBoundary(
                      child: Container(
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.07),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.white.withOpacity(0.15)),
            ),
            child: DropdownButtonFormField<String>(
              value: value,
              validator: validator,
              iconEnabledColor: BrandColors.joviCoral,
              style: TextStyle(
                color: Colors.white,
                fontSize: layoutSettings.actionTextSize + 1,
              ),
              decoration: InputDecoration(
                labelText: label,
                labelStyle: TextStyle(color: Colors.white.withOpacity(0.7)),
                floatingLabelStyle: TextStyle(
                  color: BrandColors.joviCoral,
                  fontWeight: FontWeight.w600,
                ),
                prefixIcon: Icon(icon,
                    color: BrandColors.joviCoral,
                    size: layoutSettings.actionIconDimension),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide:
                      BorderSide(color: BrandColors.joviCoral, width: 2),
                ),
                errorBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide:
                      BorderSide(color: BrandColors.joviErrorRed, width: 2),
                ),
                errorStyle: TextStyle(
                  color: Color(0xFFFF8A80),
                  fontSize: layoutSettings.actionTextSize - 1,
                ),
                filled: false,
                contentPadding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
              ),
              items: items.map((String item) {
                return DropdownMenuItem<String>(
                  value: item,
                  child: Row(
                    children: [
                      if (_issueTypePriority.containsKey(item))
                        Container(
                          width: layoutSettings.actionIconDimension * 0.28,
                          height: layoutSettings.actionIconDimension * 0.28,
                          margin: EdgeInsets.only(
                              right: layoutSettings.paddingH * 0.4),
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _issueTypePriority[item]!.color,
                            boxShadow: [
                              BoxShadow(
                                color: _issueTypePriority[item]!
                                    .color
                                    .withOpacity(0.5),
                                blurRadius: 4,
                              ),
                            ],
                          ),
                        ),
                      // r2 painted these navy, so the SELECTED value was
                      // navy-on-navy in the field.
                      Text(item,
                          style: TextStyle(
                              color: Colors.white,
                              fontSize: layoutSettings.actionTextSize + 1)),
                    ],
                  ),
                );
              }).toList(),
              onChanged: onChanged,
              dropdownColor: BrandColors.joviNavyMid,
              borderRadius: BorderRadius.circular(14),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final role = _userRole;
    final openSnap = _openTicketSnap;
    final bool hasOpen = openSnap != null && openSnap!.get('status') == 'open';
    final bool viewingTranscript = _viewingTranscriptTicketId != null;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        statusBarBrightness: Brightness.dark,
      ),
      child: wrapWithConstraints(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return Container(
              width: constraints.maxWidth,
              height: constraints.maxHeight,
              decoration: BoxDecoration(
                gradient: BrandColors.navyGradient,
              ),
              child: SafeArea(
                bottom: true,
                child: Column(
                  children: [
                    _buildModernTopBar(viewingTranscript, role, hasOpen),
                    Expanded(
                      child: FadeTransition(
                        opacity: _fadeAnimation,
                        child: SlideTransition(
                          position: _slideAnimation,
                          child: () {
                            if (_showingConfirmation) {
                              return _buildConfirmationScreen();
                            }
                            if (viewingTranscript) {
                              return _buildTranscript();
                            }
                            if (role == 'team') {
                              return _buildAdminOpenTicketList();
                            }
                            if (hasOpen) {
                              final data =
                                  openSnap!.data() as Map<String, dynamic>;
                              if (data['contactMethod'] == 'Chat') {
                                return _buildChat(openSnap!.id);
                              } else {
                                return _buildConfirmationScreen();
                              }
                            }
                            return _buildTicketForm();
                          }(),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _buildModernTopBar(
      bool viewingTranscript, String? role, bool hasOpen) {
    String title = 'Help Center';
    if (viewingTranscript) {
      title = 'Transcript';
    } else if (role == 'team') {
      title = 'Support Dashboard';
    } else if (hasOpen) {
      final data = _openTicketSnap!.data() as Map<String, dynamic>;
      if (data['contactMethod'] == 'Chat') {
        title = 'Live Chat';
      }
    }

    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Colors.white.withOpacity(0.08), width: 1),
        ),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Row(
        children: [
          _Pressable(
            reduceMotion: _reduceMotion,
            pressedScale: 0.92,
            semanticsLabel: viewingTranscript ? 'Back to tickets' : 'Back',
            onTap: () {
              HapticFeedback.lightImpact();
              if (viewingTranscript) {
                _exitTranscriptView();
              } else {
                Navigator.of(context).maybePop();
              }
            },
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.08),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white.withOpacity(0.14)),
              ),
              child: const Icon(
                Icons.arrow_back_ios_new_rounded,
                color: Colors.white,
                size: 18,
              ),
            ),
          ),
          Expanded(
            child: Semantics(
              header: true,
              child: Text(
                title,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.4,
                ),
              ),
            ),
          ),
          if (_currentUserProfile?.hasKurvPass ?? false)
            Container(
              height: 32,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                    colors: [BrandColors.joviGold, BrandColors.joviGoldDark]),
                borderRadius: BorderRadius.circular(12),
                boxShadow: [
                  BoxShadow(
                    color: BrandColors.joviGold.withOpacity(0.4),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.bolt_rounded,
                      size: 14, color: BrandColors.joviNavyDark),
                  SizedBox(width: 3),
                  Text(
                    'Jovi Pass',
                    style: TextStyle(
                      color: BrandColors.joviNavyDark,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.1,
                    ),
                  ),
                ],
              ),
            )
          else
            const SizedBox(width: 44),
        ],
      ),
    );
  }

  Widget _buildTicketForm() {
    return SingleChildScrollView(
      padding: EdgeInsets.all(layoutSettings.paddingH),
      child: Center(
        child: Container(
          constraints: BoxConstraints(
            maxWidth: layoutSettings.wideMode ? 600 : double.infinity,
          ),
          child: Form(
            key: _formKey,
            child: Column(
              children: [
                // ─── Header glass card ──────────────────────────
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(22),
                    boxShadow: [
                      BoxShadow(
                        color: BrandColors.joviCoral.withOpacity(0.2),
                        blurRadius: 20,
                        offset: Offset(0, 8),
                        spreadRadius: -4,
                      ),
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(22),
                    child: RepaintBoundary(
                      child: Container(
                        padding: EdgeInsets.all(layoutSettings.paddingH * 1.2),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(22),
                          border: Border.all(
                              color: BrandColors.joviCoral.withOpacity(0.3),
                              width: 1),
                        ),
                        child: Column(
                          children: [
                            Container(
                              padding: EdgeInsets.all(layoutSettings.paddingH),
                              decoration: BoxDecoration(
                                gradient: BrandColors.primaryGradient,
                                shape: BoxShape.circle,
                                boxShadow: [
                                  BoxShadow(
                                    color:
                                        BrandColors.joviCoral.withOpacity(0.5),
                                    blurRadius: 16,
                                    offset: Offset(0, 6),
                                  ),
                                ],
                              ),
                              child: Icon(
                                Icons.support_agent,
                                size: layoutSettings.wideMode ? 48 : 40,
                                color: Colors.white,
                              ),
                            ),
                            SizedBox(height: layoutSettings.paddingV),
                            Text(
                              'How can we help?',
                              style: TextStyle(
                                fontSize: layoutSettings.wideMode ? 26 : 24,
                                fontWeight: FontWeight.w700,
                                color: Colors.white,
                                letterSpacing: -0.6,
                                height: 1.1,
                              ),
                            ),
                            if (_currentUserProfile?.hasKurvPass ?? false) ...[
                              SizedBox(height: layoutSettings.paddingV * 0.6),
                              Container(
                                padding: EdgeInsets.symmetric(
                                  horizontal: layoutSettings.paddingH * 0.7,
                                  vertical: layoutSettings.paddingV * 0.35,
                                ),
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(colors: [
                                    BrandColors.joviGold,
                                    BrandColors.joviGoldDark
                                  ]),
                                  borderRadius: BorderRadius.circular(20),
                                  boxShadow: [
                                    BoxShadow(
                                      color:
                                          BrandColors.joviGold.withOpacity(0.4),
                                      blurRadius: 10,
                                    ),
                                  ],
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.flash_on,
                                        size:
                                            layoutSettings.actionIconDimension *
                                                0.57,
                                        color: BrandColors.joviNavyDark),
                                    SizedBox(
                                        width: layoutSettings.paddingH * 0.2),
                                    Text(
                                      'Priority Support Active',
                                      style: TextStyle(
                                        color: BrandColors.joviNavyDark,
                                        fontSize: layoutSettings.actionTextSize,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                            SizedBox(height: layoutSettings.paddingV * 0.4),
                            // Neutral, not red: nothing is wrong yet.
                            Text(
                              'Tell us a little about the issue and how you’d like us to reach you.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: layoutSettings.actionTextSize + 1,
                                color: Colors.white.withOpacity(0.65),
                                height: 1.35,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                SizedBox(height: layoutSettings.paddingV * 1.2),

                _buildStyledTextField(
                  _nameCtrl,
                  'Full Name *',
                  'Enter your full name',
                  Icons.person,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Name is required';
                    }
                    return null;
                  },
                ),

                SizedBox(height: layoutSettings.paddingV * 0.8),

                _buildStyledTextField(
                  _phoneCtrl,
                  'Phone Number *',
                  'Enter your phone number',
                  Icons.phone,
                  keyboardType: TextInputType.phone,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Phone number is required';
                    }
                    return null;
                  },
                ),

                SizedBox(height: layoutSettings.paddingV * 0.8),

                _buildStyledTextField(
                  _emailCtrl,
                  'Email Address *',
                  'Enter your email',
                  Icons.email,
                  keyboardType: TextInputType.emailAddress,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Email is required';
                    }
                    if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(value)) {
                      return 'Enter a valid email';
                    }
                    return null;
                  },
                ),

                SizedBox(height: layoutSettings.paddingV * 0.8),

                _buildStyledDropdown(
                  'Issue Type *',
                  Icons.category,
                  _selectedIssueType,
                  _issueTypePriority.keys.toList(),
                  (value) {
                    setState(() {
                      _selectedIssueType = value;
                      _selectedPriority =
                          _issueTypePriority[value] ?? TicketPriority.medium;
                    });
                  },
                  (value) {
                    if (value == null) return 'Please select an issue type';
                    return null;
                  },
                ),

                if (_selectedIssueType != null) ...[
                  SizedBox(height: layoutSettings.paddingV * 0.6),
                  Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH * 0.6),
                    decoration: BoxDecoration(
                      color: _selectedPriority.color.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color: _selectedPriority.color.withOpacity(0.45)),
                    ),
                    child: Row(
                      children: [
                        Icon(_selectedPriority.icon,
                            color: _selectedPriority.color,
                            size: layoutSettings.actionIconDimension * 0.7),
                        SizedBox(width: layoutSettings.paddingH * 0.4),
                        Text(
                          'Priority: ${_selectedPriority.name.toUpperCase()}',
                          style: TextStyle(
                            color: _selectedPriority.color,
                            fontWeight: FontWeight.bold,
                            fontSize: layoutSettings.actionTextSize + 1,
                          ),
                        ),
                        Spacer(),
                        Text(
                          'Response: ${_selectedPriority.responseTime}',
                          style: TextStyle(
                            color: _selectedPriority.color.withOpacity(0.85),
                            fontSize: layoutSettings.actionTextSize,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                SizedBox(height: layoutSettings.paddingV * 0.8),

                _buildStyledTextField(
                  _issueDescriptionCtrl,
                  'Describe Your Issue *',
                  'Tell us what’s going on…',
                  Icons.description,
                  maxLines: 5,
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Description is required';
                    }
                    if (value.trim().length < 10) {
                      return 'Please provide more details (at least 10 characters)';
                    }
                    return null;
                  },
                ),

                SizedBox(height: layoutSettings.paddingV),

                // Contact Method selection — navy glass card
                Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.2),
                        blurRadius: 10,
                        offset: Offset(0, 4),
                      ),
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(18),
                    child: RepaintBoundary(
                      child: Container(
                        padding: EdgeInsets.all(layoutSettings.paddingH),
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.07),
                          borderRadius: BorderRadius.circular(18),
                          border:
                              Border.all(color: Colors.white.withOpacity(0.15)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.contact_support,
                                    color: BrandColors.joviCoral,
                                    size: layoutSettings.actionIconDimension),
                                SizedBox(width: layoutSettings.paddingH * 0.4),
                                Text(
                                  'Preferred Contact Method *',
                                  style: TextStyle(
                                    fontSize: layoutSettings.actionTextSize + 3,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                  ),
                                ),
                              ],
                            ),
                            SizedBox(height: layoutSettings.paddingV * 0.8),
                            ..._contactMethods.map((method) {
                              IconData icon = Icons.chat;
                              if (method == 'Email') icon = Icons.email;
                              if (method == 'Phone') icon = Icons.phone;
                              final selected = _selectedContactMethod == method;

                              return Padding(
                                padding: EdgeInsets.only(
                                    bottom: layoutSettings.paddingV * 0.6),
                                child: _Pressable(
                                  reduceMotion: _reduceMotion,
                                  pressedScale: 0.98,
                                  semanticsLabel:
                                      '$method${selected ? ', selected' : ''}',
                                  onTap: () {
                                    HapticFeedback.selectionClick();
                                    setState(() {
                                      _selectedContactMethod = method;
                                      _showContactMethodError = false;
                                    });
                                  },
                                  child: AnimatedContainer(
                                      duration: _reduceMotion
                                          ? Duration.zero
                                          : const Duration(milliseconds: 200),
                                      curve: _Motion.settle,
                                      padding: EdgeInsets.all(
                                          layoutSettings.paddingH * 0.8),
                                      decoration: BoxDecoration(
                                        gradient: selected
                                            ? BrandColors.primaryGradient
                                            : null,
                                        color: selected
                                            ? null
                                            : Colors.white.withOpacity(0.05),
                                        borderRadius: BorderRadius.circular(12),
                                        border: Border.all(
                                          color: selected
                                              ? BrandColors.joviCoral
                                              : Colors.white.withOpacity(0.15),
                                          width: selected ? 0 : 1,
                                        ),
                                        boxShadow: selected
                                            ? [
                                                BoxShadow(
                                                  color: BrandColors.joviCoral
                                                      .withOpacity(0.35),
                                                  blurRadius: 12,
                                                  offset: Offset(0, 4),
                                                ),
                                              ]
                                            : null,
                                      ),
                                      child: Row(
                                        children: [
                                          Icon(
                                            icon,
                                            color: selected
                                                ? Colors.white
                                                : Colors.white.withOpacity(0.6),
                                            size: layoutSettings
                                                .actionIconDimension,
                                          ),
                                          SizedBox(
                                              width: layoutSettings.paddingH *
                                                  0.6),
                                          Text(
                                            method,
                                            style: TextStyle(
                                              fontSize: layoutSettings
                                                      .actionTextSize +
                                                  3,
                                              fontWeight: selected
                                                  ? FontWeight.bold
                                                  : FontWeight.w500,
                                              color: Colors.white,
                                            ),
                                          ),
                                          Spacer(),
                                          Container(
                                            width: layoutSettings
                                                    .actionIconDimension *
                                                0.86,
                                            height: layoutSettings
                                                    .actionIconDimension *
                                                0.86,
                                            decoration: BoxDecoration(
                                              shape: BoxShape.circle,
                                              border: Border.all(
                                                color: selected
                                                    ? Colors.white
                                                    : Colors.white
                                                        .withOpacity(0.4),
                                                width: 2,
                                              ),
                                            ),
                                            child: selected
                                                ? Center(
                                                    child: Container(
                                                      width: layoutSettings
                                                              .actionIconDimension *
                                                          0.43,
                                                      height: layoutSettings
                                                              .actionIconDimension *
                                                          0.43,
                                                      decoration: BoxDecoration(
                                                        shape: BoxShape.circle,
                                                        color: Colors.white,
                                                      ),
                                                    ),
                                                  )
                                                : null,
                                          ),
                                        ],
                                      ),
                                    ),
                                ),
                              );
                            }).toList(),
                            if (_showContactMethodError &&
                                _selectedContactMethod == null)
                              Padding(
                                padding: EdgeInsets.only(
                                    top: layoutSettings.paddingV * 0.4),
                                child: Text(
                                  'Please select a contact method',
                                  style: TextStyle(
                                    color: Color(0xFFFF8A80),
                                    fontSize: layoutSettings.actionTextSize,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                SizedBox(height: layoutSettings.paddingV * 1.2),

                // Submit button — coral gradient
                _Pressable(
                  reduceMotion: _reduceMotion,
                  pressedScale: 0.975,
                  child: Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    gradient: _isSubmittingTicket
                        ? LinearGradient(colors: [
                            Colors.white.withOpacity(0.15),
                            Colors.white.withOpacity(0.08)
                          ])
                        : BrandColors.primaryGradient,
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: _isSubmittingTicket
                        ? []
                        : [
                            BoxShadow(
                              color: BrandColors.joviCoral.withOpacity(0.45),
                              blurRadius: 16,
                              offset: Offset(0, 6),
                            ),
                          ],
                  ),
                  child: ElevatedButton(
                    onPressed: _isSubmittingTicket
                        ? null
                        : () {
                            if (_selectedContactMethod == null) {
                              HapticFeedback.heavyImpact();
                              setState(() => _showContactMethodError = true);
                              _toast('Please choose how we should contact you',
                                  isError: true);
                              return;
                            }
                            FocusManager.instance.primaryFocus?.unfocus();
                            _submitHelpTicket();
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.transparent,
                      foregroundColor: Colors.white,
                      shadowColor: Colors.transparent,
                      padding: EdgeInsets.symmetric(
                          vertical: layoutSettings.paddingV * 0.9),
                      minimumSize: Size(double.infinity,
                          layoutSettings.actionItemHeight * 0.53),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14)),
                    ),
                    child: _isSubmittingTicket
                        ? SizedBox(
                            width: layoutSettings.actionIconDimension * 0.86,
                            height: layoutSettings.actionIconDimension * 0.86,
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2,
                            ),
                          )
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.send,
                                  size:
                                      layoutSettings.actionIconDimension * 0.7,
                                  color: Colors.white),
                              SizedBox(width: layoutSettings.paddingH * 0.4),
                              const Text(
                                'Submit Ticket',
                                style: TextStyle(
                                  fontSize: 17,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white,
                                  letterSpacing: -0.3,
                                ),
                              ),
                            ],
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
    );
  }

  Widget _buildConfirmationScreen() {
    final contactMethod = _confirmationContactMethod ??
        (_openTicketSnap != null
            ? (_openTicketSnap!.data() as Map<String, dynamic>)['contactMethod']
            : 'Email');

    IconData icon = Icons.email;
    Color iconColor = BrandColors.joviCoral;
    String message = 'We will contact you via email shortly';

    if (contactMethod == 'Phone') {
      icon = Icons.phone;
      iconColor = BrandColors.joviMint;
      message = 'We will call you shortly';
    } else if (contactMethod == 'Chat') {
      icon = Icons.chat;
      iconColor = BrandColors.joviCoral;
      message = 'A support agent will be with you shortly';
    }

    return Center(
      child: SingleChildScrollView(
        padding: EdgeInsets.all(layoutSettings.paddingH * 1.2),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TweenAnimationBuilder<double>(
              tween: Tween(begin: _reduceMotion ? 1.0 : 0.0, end: 1.0),
              duration: _reduceMotion
                  ? Duration.zero
                  : const Duration(milliseconds: 420),
              curve: _Motion.settle,
              builder: (context, value, child) {
                // Materialise: fade + scale from 0.6, no overshoot.
                return Opacity(
                  opacity: value.clamp(0.0, 1.0),
                  child: Transform.scale(
                  scale: 0.6 + 0.4 * value,
                  child: Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH * 1.6),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [iconColor.withOpacity(0.85), iconColor],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: iconColor.withOpacity(0.4),
                          blurRadius: 30,
                          offset: Offset(0, 10),
                        ),
                      ],
                    ),
                    child: Icon(
                      icon,
                      size: layoutSettings.wideMode ? 64 : 56,
                      color: Colors.white,
                    ),
                  ),
                  ),
                );
              },
            ),
            SizedBox(height: layoutSettings.paddingV * 1.6),
            Text(
              'Ticket submitted',
              style: TextStyle(
                fontSize: layoutSettings.wideMode ? 30 : 28,
                fontWeight: FontWeight.w700,
                color: Colors.white,
                letterSpacing: -0.6,
                height: 1.1,
              ),
            ),
            SizedBox(height: layoutSettings.paddingV * 0.8),
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.2),
                    blurRadius: 12,
                    offset: Offset(0, 4),
                  ),
                ],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(18),
                child: RepaintBoundary(
                      child: Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.07),
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: Colors.white.withOpacity(0.15)),
                    ),
                    child: Column(
                      children: [
                        Icon(
                          Icons.check_circle,
                          color: BrandColors.joviMint,
                          size: layoutSettings.wideMode ? 52 : 48,
                        ),
                        SizedBox(height: layoutSettings.paddingV * 0.6),
                        Text(
                          message,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 5,
                            fontWeight: FontWeight.w600,
                            color: Colors.white,
                          ),
                        ),
                        SizedBox(height: layoutSettings.paddingV * 0.4),
                        Text(
                          'Our support team has received your request',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: layoutSettings.actionTextSize + 1,
                            color: Colors.white.withOpacity(0.65),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            if (_closedTickets.isNotEmpty) ...[
              SizedBox(height: layoutSettings.paddingV * 1.6),
              Text(
                'Past Tickets',
                style: TextStyle(
                  fontSize: layoutSettings.actionTextSize + 3,
                  fontWeight: FontWeight.w600,
                  color: Colors.white.withOpacity(0.7),
                ),
              ),
              SizedBox(height: layoutSettings.paddingV * 0.6),
              Container(
                constraints: BoxConstraints(
                    maxHeight: layoutSettings.wideMode ? 250 : 200),
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: _closedTickets.length.clamp(0, 3),
                  itemBuilder: (context, index) {
                    final doc = _closedTickets[index];
                    final data = doc.data() as Map<String, dynamic>;
                    final date = (data['createdAt'] as Timestamp?)?.toDate() ??
                        DateTime.now();

                    return Container(
                      margin: EdgeInsets.only(
                          bottom: layoutSettings.paddingV * 0.4),
                      child: _Pressable(
                        reduceMotion: _reduceMotion,
                        pressedScale: 0.98,
                        semanticsLabel:
                            '${data['issueType'] ?? 'Support ticket'}, ${DateFormat.yMMMd().format(date)}',
                        semanticsHint: 'Opens the transcript',
                        onTap: () => _viewTranscript(doc.id),
                        child: Container(
                            padding:
                                EdgeInsets.all(layoutSettings.paddingH * 0.6),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.05),
                              border: Border.all(
                                  color: Colors.white.withOpacity(0.12)),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Row(
                              children: [
                                Icon(Icons.history,
                                    color: Colors.white.withOpacity(0.6),
                                    size: layoutSettings.actionIconDimension *
                                        0.7),
                                SizedBox(width: layoutSettings.paddingH * 0.6),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        data['issueType'] ?? 'Support Ticket',
                                        style: TextStyle(
                                          fontSize:
                                              layoutSettings.actionTextSize + 1,
                                          fontWeight: FontWeight.w600,
                                          color: Colors.white,
                                        ),
                                      ),
                                      Text(
                                        DateFormat.yMMMd().format(date),
                                        style: TextStyle(
                                          fontSize:
                                              layoutSettings.actionTextSize,
                                          color: Colors.white.withOpacity(0.55),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Icon(Icons.chevron_right,
                                    color: BrandColors.joviCoral,
                                    size: layoutSettings.actionIconDimension *
                                        0.7),
                              ],
                            ),
                          ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAdminOpenTicketList() {
    if (_allOpenTickets.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: EdgeInsets.all(layoutSettings.paddingH * 1.6),
              decoration: BoxDecoration(
                color: BrandColors.joviCoral.withOpacity(0.15),
                shape: BoxShape.circle,
                border:
                    Border.all(color: BrandColors.joviCoral.withOpacity(0.3)),
              ),
              child: Icon(
                Icons.check_circle_outline,
                size: layoutSettings.wideMode ? 68 : 64,
                color: BrandColors.joviCoral,
              ),
            ),
            SizedBox(height: layoutSettings.paddingV * 1.2),
            Text(
              'All caught up!',
              style: TextStyle(
                fontSize: layoutSettings.wideMode ? 26 : 24,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            SizedBox(height: layoutSettings.paddingV * 0.4),
            Text(
              'No pending help tickets',
              style: TextStyle(
                fontSize: layoutSettings.actionTextSize + 3,
                color: Colors.white.withOpacity(0.6),
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: EdgeInsets.all(layoutSettings.paddingH * 0.8),
      itemCount: _allOpenTickets.length,
      itemBuilder: (ctx, idx) {
        final doc = _allOpenTickets[idx];
        final data = doc.data()! as Map<String, dynamic>;
        final ts =
            (data['createdAt'] as Timestamp?)?.toDate() ?? DateTime.now();
        final userId = data['userId'] as String;
        final isNew = data['assignedTo'] == null;
        final contactMethod = data['contactMethod'] ?? 'Email';
        final issueType = data['issueType'] ?? 'General';
        final priorityIndex = data['priority'] ?? 2;
        final priority = TicketPriority.values[priorityIndex];
        final hasKurvPass = data['hasKurvPass'] ?? false;

        final elapsed = DateTime.now().difference(ts);
        String elapsedText = '';
        if (elapsed.inDays > 0) {
          elapsedText = '${elapsed.inDays}d ago';
        } else if (elapsed.inHours > 0) {
          elapsedText = '${elapsed.inHours}h ago';
        } else if (elapsed.inMinutes > 0) {
          elapsedText = '${elapsed.inMinutes}m ago';
        } else {
          elapsedText = 'Just now';
        }

        return FutureBuilder<UserProfile>(
          future: _getUserProfile(userId),
          builder: (context, snap) {
            final profile = snap.data ??
                UserProfile(
                  displayName: data['userName'] ?? 'User',
                  photoUrl: '',
                  email: data['email'] ?? '',
                  phone: data['phone'] ?? '',
                );

            return TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.95, end: 1.0),
              duration: _reduceMotion
                  ? Duration.zero
                  : Duration(milliseconds: 220 + (idx.clamp(0, 6) * 40)),
              curve: _Motion.settle,
              builder: (context, scale, child) {
                return Transform.scale(
                  scale: scale,
                  child: Container(
                    margin:
                        EdgeInsets.only(bottom: layoutSettings.paddingV * 0.6),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      boxShadow: [
                        BoxShadow(
                          color: isNew
                              ? BrandColors.joviCoral.withOpacity(0.22)
                              : Colors.black.withOpacity(0.2),
                          blurRadius: isNew ? 16 : 10,
                          offset: Offset(0, isNew ? 6 : 3),
                        ),
                      ],
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: RepaintBoundary(
                      child: Container(
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.07),
                            borderRadius: BorderRadius.circular(18),
                            border: Border(
                              left: BorderSide(
                                color: priority.color,
                                width: 4,
                              ),
                              top: BorderSide(
                                color: isNew
                                    ? BrandColors.joviCoral.withOpacity(0.5)
                                    : Colors.white.withOpacity(0.1),
                              ),
                              right: BorderSide(
                                color: isNew
                                    ? BrandColors.joviCoral.withOpacity(0.5)
                                    : Colors.white.withOpacity(0.1),
                              ),
                              bottom: BorderSide(
                                color: isNew
                                    ? BrandColors.joviCoral.withOpacity(0.5)
                                    : Colors.white.withOpacity(0.1),
                              ),
                            ),
                          ),
                          child: _Pressable(
                            reduceMotion: _reduceMotion,
                            pressedScale: 0.98,
                            semanticsLabel:
                                'Ticket from ${data['userName'] ?? profile.displayName}, $issueType, ${priority.name} priority, $elapsedText${isNew ? ', unassigned' : ''}',
                            semanticsHint: 'Opens the conversation',
                            onTap: () => _viewTranscript(doc.id),
                            child: Padding(
                                padding: EdgeInsets.all(
                                    layoutSettings.paddingH * 0.8),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Container(
                                          decoration: BoxDecoration(
                                            shape: BoxShape.circle,
                                            gradient: isNew
                                                ? BrandColors.primaryGradient
                                                : null,
                                            color: isNew
                                                ? null
                                                : Colors.white
                                                    .withOpacity(0.08),
                                            boxShadow: isNew
                                                ? [
                                                    BoxShadow(
                                                      color: BrandColors
                                                          .joviCoral
                                                          .withOpacity(0.4),
                                                      blurRadius: 10,
                                                    ),
                                                  ]
                                                : null,
                                          ),
                                          child: CircleAvatar(
                                            radius: layoutSettings
                                                    .actionIconDimension *
                                                0.86,
                                            backgroundColor: Colors.transparent,
                                            backgroundImage: profile
                                                    .photoUrl.isNotEmpty
                                                ? NetworkImage(profile.photoUrl)
                                                : null,
                                            child: profile.photoUrl.isEmpty
                                                ? Icon(
                                                    Icons.person,
                                                    size: layoutSettings
                                                            .actionIconDimension *
                                                        0.86,
                                                    color: isNew
                                                        ? Colors.white
                                                        : Colors.white
                                                            .withOpacity(0.7),
                                                  )
                                                : null,
                                          ),
                                        ),
                                        SizedBox(
                                            width:
                                                layoutSettings.paddingH * 0.8),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Wrap(
                                                spacing:
                                                    layoutSettings.paddingH *
                                                        0.4,
                                                runSpacing:
                                                    layoutSettings.paddingV *
                                                        0.3,
                                                crossAxisAlignment:
                                                    WrapCrossAlignment.center,
                                                children: [
                                                  Text(
                                                    data['userName'] ??
                                                        profile.displayName,
                                                    style: TextStyle(
                                                      fontSize: layoutSettings
                                                              .actionTextSize +
                                                          3,
                                                      fontWeight:
                                                          FontWeight.bold,
                                                      color: Colors.white,
                                                    ),
                                                  ),
                                                  if (hasKurvPass)
                                                    Container(
                                                      padding:
                                                          EdgeInsets.symmetric(
                                                        horizontal:
                                                            layoutSettings
                                                                    .paddingH *
                                                                0.35,
                                                        vertical: layoutSettings
                                                                .paddingV *
                                                            0.15,
                                                      ),
                                                      decoration: BoxDecoration(
                                                        gradient:
                                                            LinearGradient(
                                                                colors: [
                                                              BrandColors
                                                                  .joviGold,
                                                              BrandColors
                                                                  .joviGoldDark
                                                            ]),
                                                        borderRadius:
                                                            BorderRadius
                                                                .circular(10),
                                                      ),
                                                      child: Row(
                                                        mainAxisSize:
                                                            MainAxisSize.min,
                                                        children: [
                                                          Icon(Icons.flash_on,
                                                              size: layoutSettings
                                                                      .actionIconDimension *
                                                                  0.36,
                                                              color: BrandColors
                                                                  .joviNavyDark),
                                                          SizedBox(
                                                              width: layoutSettings
                                                                      .paddingH *
                                                                  0.1),
                                                          Text(
                                                            'PASS',
                                                            style: TextStyle(
                                                              color: BrandColors
                                                                  .joviNavyDark,
                                                              fontSize:
                                                                  layoutSettings
                                                                          .actionTextSize -
                                                                      4,
                                                              fontWeight:
                                                                  FontWeight
                                                                      .bold,
                                                            ),
                                                          ),
                                                        ],
                                                      ),
                                                    ),
                                                  if (isNew)
                                                    Container(
                                                      padding:
                                                          EdgeInsets.symmetric(
                                                        horizontal:
                                                            layoutSettings
                                                                    .paddingH *
                                                                0.4,
                                                        vertical: layoutSettings
                                                                .paddingV *
                                                            0.15,
                                                      ),
                                                      decoration: BoxDecoration(
                                                        gradient: BrandColors
                                                            .primaryGradient,
                                                        borderRadius:
                                                            BorderRadius
                                                                .circular(10),
                                                      ),
                                                      child: Text(
                                                        'NEW',
                                                        style: TextStyle(
                                                          color: Colors.white,
                                                          fontSize: layoutSettings
                                                                  .actionTextSize -
                                                              3,
                                                          fontWeight:
                                                              FontWeight.bold,
                                                        ),
                                                      ),
                                                    ),
                                                ],
                                              ),
                                              SizedBox(
                                                  height:
                                                      layoutSettings.paddingV *
                                                          0.35),
                                              Wrap(
                                                spacing:
                                                    layoutSettings.paddingH *
                                                        0.4,
                                                runSpacing:
                                                    layoutSettings.paddingV *
                                                        0.3,
                                                children: [
                                                  Container(
                                                    padding:
                                                        EdgeInsets.symmetric(
                                                      horizontal: layoutSettings
                                                              .paddingH *
                                                          0.4,
                                                      vertical: layoutSettings
                                                              .paddingV *
                                                          0.15,
                                                    ),
                                                    decoration: BoxDecoration(
                                                      color: priority.color
                                                          .withOpacity(0.15),
                                                      borderRadius:
                                                          BorderRadius.circular(
                                                              8),
                                                      border: Border.all(
                                                        color: priority.color
                                                            .withOpacity(0.4),
                                                      ),
                                                    ),
                                                    child: Row(
                                                      mainAxisSize:
                                                          MainAxisSize.min,
                                                      children: [
                                                        Icon(priority.icon,
                                                            size: layoutSettings
                                                                    .actionIconDimension *
                                                                0.43,
                                                            color:
                                                                priority.color),
                                                        SizedBox(
                                                            width: layoutSettings
                                                                    .paddingH *
                                                                0.2),
                                                        Text(
                                                          priority.name
                                                              .toUpperCase(),
                                                          style: TextStyle(
                                                            fontSize: layoutSettings
                                                                    .actionTextSize -
                                                                3,
                                                            color:
                                                                priority.color,
                                                            fontWeight:
                                                                FontWeight.bold,
                                                          ),
                                                        ),
                                                      ],
                                                    ),
                                                  ),
                                                  Container(
                                                    padding:
                                                        EdgeInsets.symmetric(
                                                      horizontal: layoutSettings
                                                              .paddingH *
                                                          0.4,
                                                      vertical: layoutSettings
                                                              .paddingV *
                                                          0.15,
                                                    ),
                                                    decoration: BoxDecoration(
                                                      color: BrandColors
                                                          .joviCoral
                                                          .withOpacity(0.12),
                                                      borderRadius:
                                                          BorderRadius.circular(
                                                              8),
                                                    ),
                                                    child: Text(
                                                      issueType,
                                                      style: TextStyle(
                                                        fontSize: layoutSettings
                                                            .actionTextSize,
                                                        color: BrandColors
                                                            .joviCoralLight,
                                                        fontWeight:
                                                            FontWeight.w600,
                                                      ),
                                                      overflow:
                                                          TextOverflow.ellipsis,
                                                    ),
                                                  ),
                                                  Container(
                                                    padding:
                                                        EdgeInsets.symmetric(
                                                      horizontal: layoutSettings
                                                              .paddingH *
                                                          0.4,
                                                      vertical: layoutSettings
                                                              .paddingV *
                                                          0.15,
                                                    ),
                                                    decoration: BoxDecoration(
                                                      color: (contactMethod ==
                                                                  'Chat'
                                                              ? BrandColors
                                                                  .joviMint
                                                              : BrandColors
                                                                  .joviGold)
                                                          .withOpacity(0.15),
                                                      borderRadius:
                                                          BorderRadius.circular(
                                                              8),
                                                    ),
                                                    child: Row(
                                                      mainAxisSize:
                                                          MainAxisSize.min,
                                                      children: [
                                                        Icon(
                                                          contactMethod ==
                                                                  'Chat'
                                                              ? Icons.chat
                                                              : contactMethod ==
                                                                      'Phone'
                                                                  ? Icons.phone
                                                                  : Icons.email,
                                                          size: layoutSettings
                                                                  .actionIconDimension *
                                                              0.43,
                                                          color:
                                                              contactMethod ==
                                                                      'Chat'
                                                                  ? BrandColors
                                                                      .joviMint
                                                                  : BrandColors
                                                                      .joviGold,
                                                        ),
                                                        SizedBox(
                                                            width: layoutSettings
                                                                    .paddingH *
                                                                0.2),
                                                        Text(
                                                          contactMethod,
                                                          style: TextStyle(
                                                            fontSize: layoutSettings
                                                                .actionTextSize,
                                                            color: contactMethod ==
                                                                    'Chat'
                                                                ? BrandColors
                                                                    .joviMint
                                                                : BrandColors
                                                                    .joviGold,
                                                            fontWeight:
                                                                FontWeight.w600,
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
                                        Icon(
                                          Icons.chevron_right,
                                          color: BrandColors.joviCoral,
                                          size: layoutSettings
                                              .actionIconDimension,
                                        ),
                                      ],
                                    ),
                                    SizedBox(
                                        height: layoutSettings.paddingV * 0.6),
                                    Text(
                                      data['issueDescription'] != null &&
                                              (data['issueDescription']
                                                          as String)
                                                      .length >
                                                  80
                                          ? '${(data['issueDescription'] as String).substring(0, 77)}…'
                                          : (data['issueDescription']
                                                  as String? ??
                                              ''),
                                      style: TextStyle(
                                        fontSize:
                                            layoutSettings.actionTextSize + 1,
                                        color: Colors.white.withOpacity(0.65),
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    SizedBox(
                                        height: layoutSettings.paddingV * 0.4),
                                    Row(
                                      children: [
                                        Icon(
                                          Icons.access_time,
                                          size: layoutSettings
                                                  .actionIconDimension *
                                              0.5,
                                          color: Colors.white.withOpacity(0.4),
                                        ),
                                        SizedBox(
                                            width:
                                                layoutSettings.paddingH * 0.2),
                                        Text(
                                          elapsedText,
                                          style: TextStyle(
                                            fontSize:
                                                layoutSettings.actionTextSize,
                                            color:
                                                Colors.white.withOpacity(0.45),
                                          ),
                                        ),
                                        SizedBox(
                                            width:
                                                layoutSettings.paddingH * 0.8),
                                        Text(
                                          'SLA: ${priority.responseTime}',
                                          style: TextStyle(
                                            fontSize:
                                                layoutSettings.actionTextSize,
                                            color: priority.color,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                        Spacer(),
                                        if (data['phone'] != null) ...[
                                          Icon(Icons.phone,
                                              size: layoutSettings
                                                      .actionIconDimension *
                                                  0.5,
                                              color: Colors.white
                                                  .withOpacity(0.4)),
                                          SizedBox(
                                              width: layoutSettings.paddingH *
                                                  0.2),
                                          Flexible(
                                            child: Text(
                                              data['phone'],
                                              style: TextStyle(
                                                fontSize: layoutSettings
                                                    .actionTextSize,
                                                color: Colors.white
                                                    .withOpacity(0.45),
                                              ),
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                    if (profile.allergies.isNotEmpty ||
                                        profile.onboardConditions != null ||
                                        profile.tobacco) ...[
                                      SizedBox(
                                          height:
                                              layoutSettings.paddingV * 0.4),
                                      Container(
                                        padding: EdgeInsets.all(
                                            layoutSettings.paddingH * 0.4),
                                        decoration: BoxDecoration(
                                          color: BrandColors.joviErrorRed
                                              .withOpacity(0.15),
                                          borderRadius:
                                              BorderRadius.circular(8),
                                          border: Border.all(
                                              color: BrandColors.joviErrorRed
                                                  .withOpacity(0.4)),
                                        ),
                                        child: Row(
                                          children: [
                                            Icon(Icons.medical_information,
                                                size: layoutSettings
                                                        .actionIconDimension *
                                                    0.5,
                                                color: Color(0xFFFF8A80)),
                                            SizedBox(
                                                width: layoutSettings.paddingH *
                                                    0.4),
                                            Expanded(
                                              child: Text(
                                                _buildMedicalSummary(profile),
                                                style: TextStyle(
                                                  fontSize: layoutSettings
                                                          .actionTextSize -
                                                      2,
                                                  color: Color(0xFFFF8A80),
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
                                  ],
                                ),
                              ),
                            ),
                        ),
                      ),
                    ),
                  ),
                );
              },
            );
          },
        );
      },
    );
  }

  String _buildMedicalSummary(UserProfile profile) {
    List<String> items = [];
    if (profile.allergies.isNotEmpty) {
      items.add('Allergies: ${profile.allergies.join(", ")}');
    }
    if (profile.onboardConditions != null) {
      items.add('Conditions: ${profile.onboardConditions}');
    }
    if (profile.tobacco) {
      items.add('Tobacco use');
    }
    return items.join(' • ');
  }

  Widget _buildChat(String ticketId) {
    final bottomInset = MediaQuery.of(context).padding.bottom;
    final isStaff = _userRole == 'team';

    return Column(
      children: [
        // Staff: user info banner / User: queue or waiting
        if (isStaff)
          FutureBuilder<DocumentSnapshot>(
            future: _ticketDoc(ticketId),
            builder: (context, snapshot) {
              if (!snapshot.hasData) return SizedBox();
              final data = snapshot.data!.data() as Map<String, dynamic>;
              final userId = data['userId'] as String;

              return _withProfile(userId, (profile) {
                  return Container(
                    margin: EdgeInsets.all(layoutSettings.paddingH * 0.8),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(14),
                      child: RepaintBoundary(
                      child: Container(
                          padding:
                              EdgeInsets.all(layoutSettings.paddingH * 0.7),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.07),
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                                color: BrandColors.joviCoral.withOpacity(0.3)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  CircleAvatar(
                                    radius: layoutSettings.actionIconDimension *
                                        0.7,
                                    backgroundColor: BrandColors.joviNavyDark,
                                    backgroundImage: profile.photoUrl.isNotEmpty
                                        ? NetworkImage(profile.photoUrl)
                                        : null,
                                    child: profile.photoUrl.isEmpty
                                        ? Icon(Icons.person,
                                            size: layoutSettings
                                                    .actionIconDimension *
                                                0.7,
                                            color:
                                                Colors.white.withOpacity(0.7))
                                        : null,
                                  ),
                                  SizedBox(
                                      width: layoutSettings.paddingH * 0.6),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Flexible(
                                              child: Text(
                                                profile.displayName,
                                                style: TextStyle(
                                                  fontSize: layoutSettings
                                                          .actionTextSize +
                                                      3,
                                                  fontWeight: FontWeight.bold,
                                                  color: Colors.white,
                                                ),
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                            if (profile.hasKurvPass) ...[
                                              SizedBox(
                                                  width:
                                                      layoutSettings.paddingH *
                                                          0.4),
                                              Container(
                                                padding: EdgeInsets.symmetric(
                                                  horizontal:
                                                      layoutSettings.paddingH *
                                                          0.35,
                                                  vertical:
                                                      layoutSettings.paddingV *
                                                          0.15,
                                                ),
                                                decoration: BoxDecoration(
                                                  gradient: LinearGradient(
                                                      colors: [
                                                        BrandColors.joviGold,
                                                        BrandColors.joviGoldDark
                                                      ]),
                                                  borderRadius:
                                                      BorderRadius.circular(10),
                                                ),
                                                child: Row(
                                                  mainAxisSize:
                                                      MainAxisSize.min,
                                                  children: [
                                                    Icon(Icons.flash_on,
                                                        size: layoutSettings
                                                                .actionIconDimension *
                                                            0.36,
                                                        color: BrandColors
                                                            .joviNavyDark),
                                                    SizedBox(
                                                        width: layoutSettings
                                                                .paddingH *
                                                            0.1),
                                                    Text(
                                                      'PASS',
                                                      style: TextStyle(
                                                        color: BrandColors
                                                            .joviNavyDark,
                                                        fontSize: layoutSettings
                                                                .actionTextSize -
                                                            4,
                                                        fontWeight:
                                                            FontWeight.bold,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            ],
                                          ],
                                        ),
                                        Text(
                                          '${profile.email} • ${profile.phone}',
                                          style: TextStyle(
                                            fontSize:
                                                layoutSettings.actionTextSize,
                                            color:
                                                Colors.white.withOpacity(0.55),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              if (profile.allergies.isNotEmpty ||
                                  profile.onboardConditions != null) ...[
                                SizedBox(height: layoutSettings.paddingV * 0.4),
                                Container(
                                  padding: EdgeInsets.all(
                                      layoutSettings.paddingH * 0.4),
                                  decoration: BoxDecoration(
                                    color: BrandColors.joviErrorRed
                                        .withOpacity(0.15),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(
                                        color: BrandColors.joviErrorRed
                                            .withOpacity(0.4)),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(Icons.warning,
                                          size: layoutSettings
                                                  .actionIconDimension *
                                              0.5,
                                          color: Color(0xFFFF8A80)),
                                      SizedBox(
                                          width: layoutSettings.paddingH * 0.4),
                                      Expanded(
                                        child: Text(
                                          _buildMedicalSummary(profile),
                                          style: TextStyle(
                                            fontSize:
                                                layoutSettings.actionTextSize,
                                            color: Color(0xFFFF8A80),
                                            fontWeight: FontWeight.w500,
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
                      ),
                    ),
                  );
              });
            },
          )
        else ...[
          if (_queuePosition != null && _queuePosition! > 0)
            Container(
              margin: EdgeInsets.all(layoutSettings.paddingH * 0.8),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: RepaintBoundary(
                      child: Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH * 0.7),
                    decoration: BoxDecoration(
                      color: BrandColors.joviGold.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color: BrandColors.joviGold.withOpacity(0.4)),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.people,
                            color: BrandColors.joviGold,
                            size: layoutSettings.actionIconDimension),
                        SizedBox(width: layoutSettings.paddingH * 0.6),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'You’re number $_queuePosition in line',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize + 1,
                                  fontWeight: FontWeight.bold,
                                  color: BrandColors.joviGold,
                                ),
                              ),
                              Text(
                                'A support agent will join as soon as one is free',
                                style: TextStyle(
                                  fontSize: layoutSettings.actionTextSize,
                                  color: BrandColors.joviGold.withOpacity(0.85),
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
            )
          else if (_agentIsTyping)
            Padding(
              padding: EdgeInsets.symmetric(
                  horizontal: layoutSettings.paddingH * 0.8),
              child: TypingIndicator(layoutSettings: layoutSettings),
            )
          else
            Container(
              margin: EdgeInsets.all(layoutSettings.paddingH * 0.8),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: RepaintBoundary(
                      child: Container(
                    padding: EdgeInsets.all(layoutSettings.paddingH * 0.7),
                    decoration: BoxDecoration(
                      color: BrandColors.joviCoral.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color: BrandColors.joviCoral.withOpacity(0.3)),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.access_time,
                            color: BrandColors.joviCoral,
                            size: layoutSettings.actionIconDimension),
                        SizedBox(width: layoutSettings.paddingH * 0.6),
                        Expanded(
                          child: Text(
                            'Waiting for a support agent to connect…',
                            style: TextStyle(
                              fontSize: layoutSettings.actionTextSize + 1,
                              fontWeight: FontWeight.w600,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],

        Expanded(
          child: StreamBuilder<QuerySnapshot>(
            stream: FirebaseFirestore.instance
                .collection('helpTickets')
                .doc(ticketId)
                .collection('messages')
                .orderBy('timestamp', descending: false)
                .snapshots(),
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.error_outline,
                        size: layoutSettings.wideMode ? 68 : 64,
                        color: Color(0xFFFF8A80),
                      ),
                      SizedBox(height: layoutSettings.paddingV * 0.8),
                      Text(
                        'Error loading chat',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 5,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFFF8A80),
                        ),
                      ),
                      SizedBox(height: layoutSettings.paddingV * 0.4),
                      ElevatedButton.icon(
                        onPressed: () => setState(() {}),
                        icon: Icon(Icons.refresh,
                            size: layoutSettings.actionIconDimension * 0.7),
                        label: Text('Retry'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: BrandColors.joviCoral,
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              }

              if (!snapshot.hasData) {
                return Center(
                  child:
                      CircularProgressIndicator(color: BrandColors.joviCoral),
                );
              }

              final docs = snapshot.data!.docs;
              if (docs.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        padding: EdgeInsets.all(layoutSettings.paddingH * 1.2),
                        decoration: BoxDecoration(
                          gradient: BrandColors.lightGradient,
                          shape: BoxShape.circle,
                          border: Border.all(
                              color: BrandColors.joviCoral.withOpacity(0.3)),
                        ),
                        child: Icon(
                          Icons.chat_bubble_outline,
                          size: layoutSettings.wideMode ? 52 : 48,
                          color: BrandColors.joviCoral,
                        ),
                      ),
                      SizedBox(height: layoutSettings.paddingV * 0.8),
                      Text(
                        isStaff ? 'Start the conversation' : 'No messages yet',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 5,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                      SizedBox(height: layoutSettings.paddingV * 0.4),
                      Text(
                        isStaff
                            ? 'Send a message to the user'
                            : 'Waiting for support agent',
                        style: TextStyle(
                          fontSize: layoutSettings.actionTextSize + 1,
                          color: Colors.white.withOpacity(0.6),
                        ),
                      ),
                    ],
                  ),
                );
              }

              // Auto-scroll only when a new message arrives AND the reader
              // is near the bottom (or sent it themselves). r2 jumped to the
              // bottom on every rebuild, yanking anyone who scrolled up.
              final newCount = docs.length;
              if (newCount != _lastMessageCount) {
                final firstLoad = _lastMessageCount == 0;
                final lastIsMine =
                    (docs.last.data() as Map<String, dynamic>)['senderId'] ==
                        _uid;
                final nearBottom = !_scrollController.hasClients ||
                    (_scrollController.position.maxScrollExtent -
                            _scrollController.offset) <
                        160;
                _lastMessageCount = newCount;
                if (firstLoad || lastIsMine || nearBottom) {
                  WidgetsBinding.instance.addPostFrameCallback((_) {
                    if (!_scrollController.hasClients) return;
                    final target = _scrollController.position.maxScrollExtent;
                    if (firstLoad || _reduceMotion) {
                      _scrollController.jumpTo(target);
                    } else {
                      _scrollController.animateTo(target,
                          duration: const Duration(milliseconds: 320),
                          curve: _Motion.settle);
                    }
                  });
                }
              }

              return ListView.builder(
                controller: _scrollController,
                keyboardDismissBehavior:
                    ScrollViewKeyboardDismissBehavior.onDrag,
                padding: EdgeInsets.symmetric(
                    vertical: layoutSettings.paddingV * 0.8),
                itemCount: docs.length,
                itemBuilder: (context, idx) {
                  final msg = docs[idx].data() as Map<String, dynamic>;
                  final senderId = msg['senderId'] as String?;
                  final text = (msg['text'] as String?) ?? '';
                  final imageUrl = msg['imageUrl'] as String?;
                  final fileUrl = msg['fileUrl'] as String?;
                  final fileName = msg['fileName'] as String?;
                  final ts = (msg['timestamp'] as Timestamp?)?.toDate();
                  final isMe = senderId == _uid;

                  bool isLastSentByMe = false;
                  bool readByRecipient = false;
                  if (isMe && idx == docs.length - 1) {
                    isLastSentByMe = true;
                    readByRecipient = _userRole == 'team'
                        ? (msg['readByUser'] as bool? ?? false)
                        : (msg['readByTeam'] as bool? ?? false);
                  }

                  // Role comes from the cached profile; r2 read the sender's
                  // user document afresh for every message on every rebuild.
                  return _withProfile(senderId!, (profile) {
                    return MessageBubble(
                      text: text,
                      imageUrl: imageUrl,
                      fileUrl: fileUrl,
                      fileName: fileName,
                      timestamp: ts,
                      isMe: isMe,
                      avatarUrl: profile.photoUrl,
                      isLastSentByMe: isLastSentByMe,
                      readByRecipient: readByRecipient,
                      senderName: isMe ? 'You' : profile.displayName,
                      isStaff: profile.isTeam,
                      layoutSettings: layoutSettings,
                    );
                  });
                },
              );
            },
          ),
        ),

        // Canned Responses Overlay (for staff) — glass
        if (isStaff &&
            _showCannedResponses &&
            _filteredCannedResponses.isNotEmpty)
          Container(
            constraints:
                BoxConstraints(maxHeight: layoutSettings.wideMode ? 250 : 200),
            margin:
                EdgeInsets.symmetric(horizontal: layoutSettings.paddingH * 0.8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.25),
                  blurRadius: 12,
                  offset: Offset(0, -2),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
              child: RepaintBoundary(
                      child: Container(
                  decoration: BoxDecoration(
                    color: BrandColors.joviNavy.withOpacity(0.9),
                    border: Border.all(color: Colors.white.withOpacity(0.12)),
                  ),
                  child: ListView.builder(
                    shrinkWrap: true,
                    padding: EdgeInsets.all(layoutSettings.paddingH * 0.4),
                    itemCount: _filteredCannedResponses.length,
                    itemBuilder: (context, index) {
                      final response = _filteredCannedResponses[index];
                      return ListTile(
                        dense: true,
                        leading: Container(
                          padding:
                              EdgeInsets.all(layoutSettings.paddingH * 0.3),
                          decoration: BoxDecoration(
                            color: BrandColors.joviCoral.withOpacity(0.18),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                                color: BrandColors.joviCoral.withOpacity(0.4)),
                          ),
                          child: Text(
                            response.shortcut,
                            style: TextStyle(
                              color: BrandColors.joviCoral,
                              fontSize: layoutSettings.actionTextSize,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        title: Text(
                          response.title,
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: layoutSettings.actionTextSize + 1,
                            color: Colors.white,
                          ),
                        ),
                        subtitle: Text(
                          response.message,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              fontSize: layoutSettings.actionTextSize,
                              color: Colors.white.withOpacity(0.6)),
                        ),
                        onTap: () => _applyCannedResponse(response),
                      );
                    },
                  ),
                ),
              ),
            ),
          ),

        // Input Bar (only for staff)
        if (isStaff)
          Container(
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(color: Colors.white.withOpacity(0.08)),
              ),
            ),
            padding: EdgeInsets.fromLTRB(
              layoutSettings.paddingH * 0.6,
              layoutSettings.paddingV * 0.6,
              layoutSettings.paddingH * 0.6,
              bottomInset + layoutSettings.paddingV * 0.6,
            ),
            child: Column(
              children: [
                // Quick Actions Bar
                Container(
                  height: layoutSettings.actionItemHeight * 0.38,
                  margin:
                      EdgeInsets.only(bottom: layoutSettings.paddingV * 0.4),
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      _buildQuickAction('Greeting', Icons.waving_hand,
                          () => _applyCannedResponse(_cannedResponses[0])),
                      _buildQuickAction('Investigating', Icons.search,
                          () => _applyCannedResponse(_cannedResponses[1])),
                      _buildQuickAction('Need Info', Icons.info,
                          () => _applyCannedResponse(_cannedResponses[2])),
                      _buildQuickAction('Resolved', Icons.check_circle,
                          () => _applyCannedResponse(_cannedResponses[3])),
                    ],
                  ),
                ),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    _inputChip(
                      icon: Icons.add_photo_alternate_rounded,
                      label: 'Attach photo',
                      onTap: () async {
                        HapticFeedback.selectionClick();
                        final picked = await ImagePicker().pickImage(
                            source: ImageSource.gallery,
                            maxWidth: 1600,
                            imageQuality: 85);
                        if (picked != null && mounted) {
                          setState(() => _pickedImage = picked);
                        }
                      },
                    ),
                    SizedBox(width: layoutSettings.paddingH * 0.2),
                    _inputChip(
                      icon: Icons.attach_file_rounded,
                      label: 'Attach file',
                      onTap: () async {
                        HapticFeedback.selectionClick();
                        final result = await FilePicker.platform
                            .pickFiles(withData: true);
                        if (result != null && mounted) {
                          setState(() => _pickedFile = result.files.first);
                        }
                      },
                    ),
                    SizedBox(width: layoutSettings.paddingH * 0.4),

                    // Image/File preview
                    if (_pickedImage != null || _pickedFile != null) ...[
                      Container(
                        margin: EdgeInsets.only(bottom: 2),
                        child: Stack(
                          children: [
                            Container(
                              padding:
                                  EdgeInsets.all(layoutSettings.paddingH * 0.4),
                              decoration: BoxDecoration(
                                color: BrandColors.joviCoral.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    _pickedImage != null
                                        ? Icons.image
                                        : Icons.description,
                                    color: BrandColors.joviCoral,
                                    size: layoutSettings.actionIconDimension *
                                        0.7,
                                  ),
                                  SizedBox(
                                      width: layoutSettings.paddingH * 0.2),
                                  Text(
                                    _pickedImage != null
                                        ? 'Image'
                                        : (_pickedFile?.name ?? 'File'),
                                    style: TextStyle(
                                      color: BrandColors.joviCoral,
                                      fontSize: layoutSettings.actionTextSize,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Positioned(
                              top: -2,
                              right: -2,
                              child: GestureDetector(
                                onTap: () {
                                  HapticFeedback.selectionClick();
                                  setState(() {
                                    _pickedImage = null;
                                    _pickedFile = null;
                                  });
                                },
                                child: Container(
                                  padding: EdgeInsets.all(
                                      layoutSettings.paddingH * 0.1),
                                  decoration: BoxDecoration(
                                    color: BrandColors.joviErrorRed,
                                    shape: BoxShape.circle,
                                  ),
                                  child: Icon(
                                    Icons.close,
                                    size: layoutSettings.actionIconDimension *
                                        0.5,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      SizedBox(width: layoutSettings.paddingH * 0.4),
                    ],

                    // Message input field — glass
                    Expanded(
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(24),
                          border:
                              Border.all(color: Colors.white.withOpacity(0.15)),
                        ),
                        child: TextField(
                          controller: _messageCtrl,
                          cursorColor: BrandColors.joviCoral,
                          style: const TextStyle(
                              color: Colors.white, fontSize: 16),
                          decoration: InputDecoration(
                            hintText: 'Type a message or "/" for quick replies',
                            hintStyle: TextStyle(
                              color: Colors.white.withOpacity(0.45),
                              fontSize: layoutSettings.actionTextSize + 1,
                            ),
                            border: InputBorder.none,
                            contentPadding: EdgeInsets.symmetric(
                              horizontal: layoutSettings.paddingH * 0.8,
                              vertical: layoutSettings.paddingV * 0.5,
                            ),
                          ),
                          minLines: 1,
                          maxLines: 5,
                          textCapitalization: TextCapitalization.sentences,
                          onChanged: (text) {
                            if (text.isNotEmpty) {
                              _updateTypingStatus(ticketId, true);
                            } else {
                              _updateTypingStatus(ticketId, false);
                            }
                          },
                        ),
                      ),
                    ),
                    SizedBox(width: layoutSettings.paddingH * 0.4),

                    _buildSendButton(ticketId),
                  ],
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildQuickAction(String label, IconData icon, VoidCallback onTap) {
    return Container(
      margin: EdgeInsets.only(right: layoutSettings.paddingH * 0.4),
      child: _Pressable(
        reduceMotion: _reduceMotion,
        pressedScale: 0.95,
        semanticsLabel: 'Quick reply: $label',
        onTap: () {
          HapticFeedback.selectionClick();
          onTap();
        },
        child: Container(
          padding:
              EdgeInsets.symmetric(horizontal: layoutSettings.paddingH * 0.6),
          decoration: BoxDecoration(
            color: BrandColors.joviCoral.withOpacity(0.12),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: BrandColors.joviCoral.withOpacity(0.4)),
          ),
          child: Row(
            children: [
              Icon(icon,
                  size: layoutSettings.actionIconDimension * 0.57,
                  color: BrandColors.joviCoral),
              SizedBox(width: layoutSettings.paddingH * 0.3),
              Text(
                label,
                style: TextStyle(
                  color: BrandColors.joviCoral,
                  fontSize: layoutSettings.actionTextSize,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 44 pt attach control for the input bar.
  Widget _inputChip(
      {required IconData icon,
      required String label,
      required VoidCallback onTap}) {
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.9,
      semanticsLabel: label,
      onTap: onTap,
      child: Container(
        width: 44,
        height: 44,
        margin: const EdgeInsets.only(bottom: 2),
        decoration: BoxDecoration(
          color: BrandColors.joviCoral.withOpacity(0.15),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: BrandColors.joviCoral.withOpacity(0.3)),
        ),
        child: Icon(icon, color: BrandColors.joviCoral, size: 22),
      ),
    );
  }

  /// Arrow-up send, as in Messages. Lights up only when there is something
  /// to send; spins while sending.
  Widget _buildSendButton(String ticketId) {
    final hasContent = _messageCtrl.text.trim().isNotEmpty ||
        _pickedImage != null ||
        _pickedFile != null;
    final canSend = hasContent && !_isSendingMessage;
    return _Pressable(
      reduceMotion: _reduceMotion,
      pressedScale: 0.9,
      semanticsLabel: 'Send',
      onTap: canSend ? () => _sendMessage(ticketId) : null,
      child: AnimatedContainer(
        duration:
            _reduceMotion ? Duration.zero : const Duration(milliseconds: 200),
        curve: _Motion.settle,
        width: 44,
        height: 44,
        margin: const EdgeInsets.only(bottom: 2),
        decoration: BoxDecoration(
          gradient: hasContent ? BrandColors.primaryGradient : null,
          color: hasContent ? null : Colors.white.withOpacity(0.12),
          borderRadius: BorderRadius.circular(14),
          boxShadow: hasContent
              ? [
                  BoxShadow(
                    color: BrandColors.joviCoral.withOpacity(0.4),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ]
              : null,
        ),
        child: _isSendingMessage
            ? const Center(
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white),
                ),
              )
            : Icon(
                Icons.arrow_upward_rounded,
                color: hasContent ? Colors.white : Colors.white.withOpacity(0.4),
                size: 24,
              ),
      ),
    );
  }

  Widget _buildTranscript() {
    final ticketId = _viewingTranscriptTicketId!;

    return StreamBuilder<QuerySnapshot>(
      stream: FirebaseFirestore.instance
          .collection('helpTickets')
          .doc(ticketId)
          .collection('messages')
          .orderBy('timestamp', descending: false)
          .snapshots(),
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return Center(
            child: Text('Error loading transcript',
                style: TextStyle(color: Color(0xFFFF8A80))),
          );
        }

        if (!snapshot.hasData) {
          return Center(
            child: CircularProgressIndicator(color: BrandColors.joviCoral),
          );
        }

        final docs = snapshot.data!.docs;
        if (docs.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.inbox,
                  size: layoutSettings.wideMode ? 68 : 64,
                  color: Colors.white.withOpacity(0.3),
                ),
                SizedBox(height: layoutSettings.paddingV * 0.8),
                Text(
                  'No messages in this transcript',
                  style: TextStyle(
                    fontSize: layoutSettings.actionTextSize + 3,
                    color: Colors.white.withOpacity(0.6),
                  ),
                ),
              ],
            ),
          );
        }

        return ListView.builder(
          padding:
              EdgeInsets.symmetric(vertical: layoutSettings.paddingV * 0.8),
          itemCount: docs.length,
          itemBuilder: (context, idx) {
            final msg = docs[idx].data() as Map<String, dynamic>;
            final senderId = msg['senderId'] as String?;
            final text = (msg['text'] as String?) ?? '';
            final imageUrl = msg['imageUrl'] as String?;
            final fileUrl = msg['fileUrl'] as String?;
            final fileName = msg['fileName'] as String?;
            final ts = (msg['timestamp'] as Timestamp?)?.toDate();
            final isMe = senderId == _uid;

            return _withProfile(senderId!, (profile) {
              return MessageBubble(
                text: text,
                imageUrl: imageUrl,
                fileUrl: fileUrl,
                fileName: fileName,
                timestamp: ts,
                isMe: isMe,
                avatarUrl: profile.photoUrl,
                senderName: profile.displayName,
                isStaff: profile.isTeam,
                layoutSettings: layoutSettings,
              );
            });
          },
        );
      },
    );
  }
}
