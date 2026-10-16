// LzCallQueue (call screen v3, JC-LAZO-CALLS-1016-APP-003): a media step that
// never finishes - a request the network swallowed - must not stop the steps
// behind it (later video, a reconnect).
import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:junecheck/call_screen_main.dart';

void main() {
  test('steps run one at a time, in order', () async {
    final LzCallQueue q = LzCallQueue();
    final List<int> seen = <int>[];
    final Future<void> a = q.run(() async {
      await Future<void>.delayed(const Duration(milliseconds: 30));
      seen.add(1);
    });
    final Future<void> b = q.run(() async => seen.add(2));
    await Future.wait(<Future<void>>[a, b]);
    expect(seen, <int>[1, 2]);
  });

  test('a stuck step is given up and the next step still runs', () async {
    final LzCallQueue q = LzCallQueue(limit: const Duration(milliseconds: 100));
    final Completer<void> never = Completer<void>();
    final Future<void> stuck = q.run(() => never.future);
    final Future<String> next = q.run(() async => 'video pulled');
    await expectLater(stuck, throwsA(isA<TimeoutException>()));
    expect(await next.timeout(const Duration(seconds: 2)), 'video pulled');
  });

  test('a failing step does not break the queue', () async {
    final LzCallQueue q = LzCallQueue();
    await expectLater(q.run<void>(() async => throw StateError('sfu 500')), throwsStateError);
    expect(await q.run(() async => 7), 7);
  });
}
