"""patch_vendor_v179.py - JC-LAZO-VDASH-0924-179
App Store review fixes for the vendor dashboard (submission 9eeaf10a, 2026-09-24):

  3.1.1 / 2.1(a)  No purchasing inside the native apps. _upgradeSheet on iOS and
                  Android now opens the plan-status sheet (v157's _mobilePlanSheet)
                  instead of the Choose Pro / Choose Pro Studio checkout. The
                  status sheet shows the current plan and says plans are managed
                  on meetlazo.com; on US-region devices it also offers a button
                  that opens meetlazo.com/for-vendors/#pricing in the browser,
                  which Apple's review note confirms is permitted on the US
                  storefront. Elsewhere: text only. The web build is untouched.
  5.1.1(v)        "Delete my account" under Sign out in Account, with a
                  confirmation, calling the deleteMyVendorAccount callable
                  (functions-dashboard/deleteAccount.js), then signing out.
  copy            the Studio preview banner no longer promises an in-app unlock.

Anchor-and-assert against Vendor_master.txt; writes Vendor_master_v179.txt.
  python app-patches\\patch_vendor_v179.py
"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
src = HERE / "Vendor_master.txt"; dst = HERE / "Vendor_master_v179.txt"
s = src.read_text(encoding="utf-8")
if "VDASH-0924-179" in s:
    raise SystemExit("already patched")

def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        raise SystemExit(f"{label}: anchor found {n}x, wanted {count}: {old[:70]!r}")
    s = s.replace(old, new)

# ---- build id line
rep("// Build ID: JC-LAZO-VDASH-0917-178 (v178:",
    "// Build ID: JC-LAZO-VDASH-0924-179 (v179: APP STORE - no purchasing in the native apps: _upgradeSheet opens the plan-status sheet on iOS/Android, with a browser link to meetlazo.com/for-vendors/#pricing on US-region devices only (Apple permits link-out on the US storefront; text-only elsewhere); 'Delete my account' under Sign out calls deleteMyVendorAccount then signs out; the Studio preview banner no longer promises an in-app unlock. Web build unchanged.)\n// (v178:", "build id")

# ---- 1. native: the upgrade entry point becomes the status sheet
rep('''      final String currentTier =
          ((vs.data() ?? const <String, dynamic>{})['tier'] ?? '').toString();
      _showUpgradeSheet(vendorId, currentTier);
    }).catchError((Object e) {
      if (mounted) _showUpgradeSheet(vendorId, '');
    });
  }
''', '''      final String currentTier =
          ((vs.data() ?? const <String, dynamic>{})['tier'] ?? '').toString();
      if (!kIsWeb) {
        // v179: App Store 3.1.1 - no purchase flow in the native apps. The
        // status sheet says what the plan is and where plans are managed.
        _mobilePlanSheet(currentTier, '', false);
        return;
      }
      _showUpgradeSheet(vendorId, currentTier);
    }).catchError((Object e) {
      if (!mounted) return;
      if (!kIsWeb) {
        _mobilePlanSheet('', '', false);
        return;
      }
      _showUpgradeSheet(vendorId, '');
    });
  }
''', "upgradeSheet native")

# ---- 2. the status sheet: current plan, where plans are managed, US-only link
rep('''    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (BuildContext ctx) => Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 22),
        decoration: BoxDecoration(
          color: card,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: goldLine),
        ),
        child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(plan, style: _serif(size: 26)),
              const SizedBox(height: 4),
              Text(line,
                  style:
                      const TextStyle(color: muted, fontSize: 13, height: 1.4)),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                    color: ivory,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: goldLine)),
                child: const Row(children: <Widget>[
                  Icon(Icons.language_rounded, color: plum, size: 18),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                        'Plans, upgrades and card details are managed on meetlazo.com from any browser. Changes show here within a minute.',
                        style:
                            TextStyle(color: ink, fontSize: 13, height: 1.4)),
                  ),
                ]),
              ),
            ]),
      ),
    );
  }
''', '''    // v179: Apple permits a link out to the browser for purchases on the US
    // storefront only, so the button appears for US-region devices; everywhere
    // else the sheet is text only. The web build never reaches this sheet.
    final bool usDevice =
        (WidgetsBinding.instance.platformDispatcher.locale.countryCode ?? '')
                .toUpperCase() ==
            'US';
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (BuildContext ctx) => Container(
        margin: const EdgeInsets.all(12),
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 22),
        decoration: BoxDecoration(
          color: card,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: goldLine),
        ),
        child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(plan, style: _serif(size: 26)),
              const SizedBox(height: 4),
              Text(line,
                  style:
                      const TextStyle(color: muted, fontSize: 13, height: 1.4)),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                    color: ivory,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: goldLine)),
                child: const Row(children: <Widget>[
                  Icon(Icons.language_rounded, color: plum, size: 18),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                        'Plans, upgrades and card details are managed on meetlazo.com from any browser. Changes show here within a minute.',
                        style:
                            TextStyle(color: ink, fontSize: 13, height: 1.4)),
                  ),
                ]),
              ),
              if (usDevice) ...<Widget>[
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                        backgroundColor: plum,
                        foregroundColor: ivory,
                        padding: const EdgeInsets.symmetric(vertical: 13)),
                    onPressed: _h(() {
                      Navigator.pop(ctx);
                      _openUrl('https://meetlazo.com/for-vendors/#pricing');
                    }),
                    icon: const Icon(Icons.open_in_new_rounded, size: 18),
                    label: const Text('Manage your plan on meetlazo.com',
                        style: TextStyle(fontWeight: FontWeight.w700)),
                  ),
                ),
              ],
            ]),
      ),
    );
  }
''', "mobile plan sheet")

# ---- 3. the Studio preview banner: no in-app unlock promised
rep('''              Text(
                  'Browse everything below - it all unlocks the moment you upgrade. Founding pricing locks for life.',
                  style: TextStyle(color: ivory, fontSize: 12.5)),''',
    '''              Text(
                  'Browse everything below - it all comes with Pro Studio. Plans are managed on meetlazo.com.',
                  style: TextStyle(color: ivory, fontSize: 12.5)),''', "banner copy")
rep('''          child: const Text('Unlock Studio',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),''',
    '''          child: const Text('About Studio',
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),''', "banner button")

# ---- 4. delete my account, under Sign out
rep('''                onPressed: _h(_logOut),
                icon: const Icon(Icons.logout_rounded, size: 18),
                label: const Text('Sign out',
                    style: TextStyle(fontWeight: FontWeight.w600)),
              ),
            ),
          ],
        );
      },
    );
  }
''', '''                onPressed: _h(_logOut),
                icon: const Icon(Icons.logout_rounded, size: 18),
                label: const Text('Sign out',
                    style: TextStyle(fontWeight: FontWeight.w600)),
              ),
            ),
            // v179: App Store 5.1.1(v) - account deletion, in the app, complete.
            const SizedBox(height: 10),
            Center(
              child: TextButton(
                onPressed: _h(_deleteVendorAccount),
                child: const Text('Delete my account',
                    style: TextStyle(
                        color: Color(0xFFB3413A),
                        fontSize: 13,
                        fontWeight: FontWeight.w600)),
              ),
            ),
          ],
        );
      },
    );
  }

  // v179: deletion runs server-side (functions-dashboard/deleteAccount.js,
  // deleteMyVendorAccount): the claim is released so the public listing goes
  // back to unclaimed, everything the owner added is removed along with their
  // uploads, templates and login, and the login is deleted LAST so a partial
  // failure is retryable rather than permanent.
  Future<void> _deleteVendorAccount() async {
    final User? u = FirebaseAuth.instance.currentUser;
    if (u == null) return;
    final bool? sure = await showDialog<bool>(
      context: context,
      builder: (BuildContext ctx) => AlertDialog(
        backgroundColor: ivory,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Delete account?',
            style: TextStyle(color: plum, fontWeight: FontWeight.w700)),
        content: const Text(
          'This permanently deletes your login, your uploads, templates and everything you added to your profile, and releases your claim on the listing. Any active plan is cancelled. This can\\u2019t be undone.',
          style: TextStyle(color: ink, fontSize: 14, height: 1.4),
        ),
        actions: <Widget>[
          TextButton(
              onPressed: _h(() => Navigator.pop(ctx, false)),
              child:
                  const Text('Keep my account', style: TextStyle(color: ink))),
          FilledButton(
            style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFFB3413A),
                foregroundColor: ivory),
            onPressed: _h(() => Navigator.pop(ctx, true)),
            child: const Text('Delete forever'),
          ),
        ],
      ),
    );
    if (sure != true) return;
    try {
      await FirebaseFunctions.instance
          .httpsCallable('deleteMyVendorAccount',
              options:
                  HttpsCallableOptions(timeout: const Duration(seconds: 300)))
          .call(<String, dynamic>{});
      try {
        await FirebaseAuth.instance.signOut();
      } catch (_) {}
      if (!mounted) return;
      context.goNamed('Welcome');
    } on FirebaseFunctionsException catch (e) {
      _toast(e.message ?? 'Could not delete the account. Try again.');
    } catch (_) {
      _toast('Could not delete the account. Try again.');
    }
  }
''', "delete account")

dst.write_text(s, encoding="utf-8", newline="\n")
print(f"wrote {dst.name}: {len(s):,} bytes")
