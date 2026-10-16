"""Thread template v2 (JC-LAZO-CALLSCHED-1016-APP-002): dark-mode Join buttons in gold,
the card's Reschedule / Cancel under "More" on phones, and an end marker.
Reads lazo_call_thread_v1.dart.txt, writes lazo_call_thread.dart.txt.
    python app-patches\\patch_call_thread_v2.py
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
s = (HERE / 'lazo_call_thread_v1.dart.txt').read_text(encoding='utf-8')


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (a[:80], c)
    s = s.replace(a, b)


# ---- 6. dark mode: the filled Join buttons go gold with dark text
rep("""              style: FilledButton.styleFrom(
                  backgroundColor: plum,
                  minimumSize: const Size.fromHeight(48),""", """              style: FilledButton.styleFrom(
                  backgroundColor: _lzDark ? gold : plum,
                  foregroundColor: _lzDark ? const Color(0xFF241E2B) : Colors.white,
                  minimumSize: const Size.fromHeight(48),""")
rep("""            style: FilledButton.styleFrom(backgroundColor: plum, shape: const StadiumBorder()),""",
    """            style: FilledButton.styleFrom(
                backgroundColor: _lzDark ? gold : plum,
                foregroundColor: _lzDark ? const Color(0xFF241E2B) : Colors.white,
                shape: const StadiumBorder()),""")

# ---- 10. the card on phones: Add to calendar + More (Reschedule, Cancel)
rep("""                Wrap(spacing: 2, children: <Widget>[
                  TextButton.icon(
                    onPressed: () => _addToCalendarSheet(m, consultId),
                    icon: Icon(Icons.event_available_rounded, size: 16, color: _lzFg(plum)),
                    label: Text('Add to calendar', style: TextStyle(color: _lzFg(plum), fontSize: 12.5)),
                  ),
                  if (lazoCall)""", """                Wrap(spacing: 2, crossAxisAlignment: WrapCrossAlignment.center, children: <Widget>[
                  TextButton.icon(
                    onPressed: () => _addToCalendarSheet(m, consultId),
                    icon: Icon(Icons.event_available_rounded, size: 16, color: _lzFg(plum)),
                    label: Text('Add to calendar', style: TextStyle(color: _lzFg(plum), fontSize: 12.5)),
                  ),
                  if (lazoCall && MediaQuery.of(context).size.width < 520)
                    PopupMenuButton<String>(
                      tooltip: 'More',
                      onSelected: (String v) {
                        if (v == 'move') {
                          _scheduleCallSheet(inquiryId, inq,
                              consultId: consultId, current: start, currentMinutes: minutes);
                        } else if (v == 'cancel') {
                          _cancelCallConfirm(consultId);
                        }
                      },
                      itemBuilder: (BuildContext c) => const <PopupMenuEntry<String>>[
                        PopupMenuItem<String>(value: 'move', child: Text('Reschedule')),
                        PopupMenuItem<String>(value: 'cancel', child: Text('Cancel the call')),
                      ],
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        child: Row(mainAxisSize: MainAxisSize.min, children: <Widget>[
                          Icon(Icons.more_horiz_rounded, size: 18, color: _lzFg(plum)),
                          const SizedBox(width: 4),
                          Text('More', style: TextStyle(color: _lzFg(plum), fontSize: 12.5)),
                        ]),
                      ),
                    ),
                  if (lazoCall && MediaQuery.of(context).size.width >= 520)""")
rep("""                  if (lazoCall)
                    TextButton.icon(
                      onPressed: () => _cancelCallConfirm(consultId),""", """                  if (lazoCall && MediaQuery.of(context).size.width >= 520)
                    TextButton.icon(
                      onPressed: () => _cancelCallConfirm(consultId),""")
rep("""  // SCHEDULE A LAZO VIDEO CALL + AUDIO ONLY.  JC-LAZO-CALLSCHED-1016-APP""",
    """  // SCHEDULE A LAZO VIDEO CALL + AUDIO ONLY.  JC-LAZO-CALLSCHED-1016-APP-002
  // (002: gold Join buttons in dark mode; Reschedule / Cancel under More on phones)""")
s = s.rstrip('\n') + '\n  // END LAZO CALL THREAD (JC-LAZO-CALLSCHED-1016-APP)\n'
(HERE / 'lazo_call_thread.dart.txt').write_text(s, encoding='utf-8')
print('thread template v2 written')
