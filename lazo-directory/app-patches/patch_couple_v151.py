"""patch_couple_v151.py - JC-LAZO-COUPLE-1011-V151
Couple_master_v150 -> v151: the booking celebration fires once per booking, ever.
Why it repeated: the inquiries listener's first snapshot is Firestore's cache (often empty), the
celebration logic saw fewer bookings than it had celebrated and quietly re-baselined DOWN to 0, then
the server snapshot arrived with the signed contract and it celebrated it again - every sign-in.
Now: cache-only snapshots are ignored, celebrations are keyed by inquiry id (couples.celebratedBookingIds)
so the count can never go backwards, and the record lives on the couple's own doc (_cid), which a
joining partner shares, not on couples/{uid}.
  python app-patches\\patch_couple_v151.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent


def rep(s, old, new, label, count=1):
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    return s.replace(old, new)


s = (HERE / "Couple_master_v150.txt").read_text(encoding="utf-8-sig")
s = rep(s, "// (v150: ", "// (v151: BOOKED ONCE - the 'contract signed' celebration fires once per booking: cache-only snapshots are ignored, celebrations are keyed by inquiry id on the couple doc (celebratedBookingIds) so it never re-baselines down and never repeats on sign-in. JC-LAZO-COUPLE-1011-V151; base v150)\n// (v150: ", 'note')
s = rep(s, "// END OF FILE - JC-LAZO-COUPLE-1010-V150", "// END OF FILE - JC-LAZO-COUPLE-1011-V151", 'end')

s = rep(s, '''        .listen((QuerySnapshot<Map<String, dynamic>> snap) {
      _inqDocs = snap.docs;
      _maybeCelebrateBooking(snap.docs);
      _runBookedSync(_lastPlanForSync);
    });''',
        '''        .listen((QuerySnapshot<Map<String, dynamic>> snap) {
      _inqDocs = snap.docs;
      // JC-LAZO-COUPLE-1011-V151: the cache's first answer is not the truth
      if (!snap.metadata.isFromCache) _maybeCelebrateBooking(snap.docs);
      _runBookedSync(_lastPlanForSync);
    });''', 'listener')

a = s.index("  Future<void> _maybeCelebrateBooking(")
b = s.index("  void _fireBookingCelebration() {")
s = s[:a] + '''  // JC-LAZO-COUPLE-1011-V151: once per booking, ever. Keyed by inquiry id on
  // the couple's doc; the first run baselines silently; the set only grows.
  Future<void> _maybeCelebrateBooking(
      List<QueryDocumentSnapshot<Map<String, dynamic>>> docs) async {
    if (_uid == null || _bookingCelebrateBusy) {
      return;
    }
    final List<String> booked = <String>[];
    for (final QueryDocumentSnapshot<Map<String, dynamic>> d in docs) {
      final Map<String, dynamic> inq = d.data();
      final bool isBooked = (inq['status'] ?? '') == 'booked' ||
          inq['bookedAt'] != null ||
          (inq['contractStatus'] ?? '') == 'signed';
      if (isBooked) booked.add(d.id);
    }
    _bookingCelebrateBusy = true;
    try {
      final DocumentReference<Map<String, dynamic>> cRef =
          FirebaseFirestore.instance.collection('couples').doc(_cid);
      final DocumentSnapshot<Map<String, dynamic>> cSnap = await cRef.get();
      final Map<String, dynamic> cd = cSnap.data() ?? <String, dynamic>{};
      final dynamic raw = cd['celebratedBookingIds'];
      if (raw is! List) {
        // First run (or a plan from before ids): baseline silently - no
        // confetti for history. Keeps the old count in step for older builds.
        await cRef.set(<String, dynamic>{
          'celebratedBookingIds': booked,
          'celebratedBookings': booked.length,
        }, SetOptions(merge: true));
        return;
      }
      final Set<String> seen = raw.map((dynamic e) => e.toString()).toSet();
      final List<String> fresh =
          booked.where((String id) => !seen.contains(id)).toList();
      if (fresh.isEmpty) return;
      await cRef.set(<String, dynamic>{
        'celebratedBookingIds': FieldValue.arrayUnion(fresh),
        'celebratedBookings': seen.length + fresh.length,
      }, SetOptions(merge: true));
      if (mounted) {
        _fireBookingCelebration();
      }
    } catch (e) {
      debugPrint('LAZO booking celebrate: ' + e.toString());
    } finally {
      _bookingCelebrateBusy = false;
    }
  }

''' + s[b:]
(HERE / "Couple_master_v151.txt").write_text(s, encoding="utf-8")
print("wrote Couple_master_v151.txt", len(s))
