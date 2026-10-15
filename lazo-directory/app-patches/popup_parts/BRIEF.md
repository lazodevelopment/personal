# Popup pass (JC-LAZO-POPUP-1014) - brief for each part

Jesse (owner of Lazo, a wedding-planning app) asked: go through the couple dashboard and the vendor dashboard,
everywhere a button opens a popup, and make the popup experience a lot better. His example: the "switching from
another planning site" popup felt juvenile (a wall of paragraphs, plain text-box dialogs, text-dump previews,
toasts as progress). That one is already rebuilt - read it as the quality bar:
`app-patches/import_v158.dart.txt` (`_importSheet`).

## The files
- Both dashboards are single FlutterFlow custom-widget files (Dart), ~30k lines each.
- FROZEN BASES you work against (do not edit them):
  - `app-patches/popup_parts/base_couple.txt` (Couple dashboard v158 base)
  - `app-patches/popup_parts/base_vendor.txt` (Vendor dashboard v197 base)
- Already done in the bases: every `showModalBottomSheet` / `showDialog` call was renamed to `_lzSheet` / `_lzDialog`
  (same parameters). `_lzSheet` shows a bottom sheet WITH A GRAB HANDLE on phones and a centred card on wide
  screens; `_lzDialog` themes AlertDialogs. The shared kit is in `app-patches/popup_kit_1014.dart.txt` (also
  inserted into both bases, just above `void _toast(`). Read it first. API:
  - `_lzSheet<T>({context, builder, backgroundColor, shape, isScrollControlled, constraints, isDismissible, barrierColor})`
  - `_lzDialog<T>({context, builder, barrierDismissible, barrierColor})`
  - `_lzFrame(ctx, {icon, title, subtitle, children, footer, headerExtra, onBack, bodyPadding, fill})` - the standard
    layout: icon chip + serif title + one-line subtitle + close (and optional back), a divider, a scrolling body,
    and a footer that never scrolls away. Lifts above the keyboard. Use it as the builder's root inside `_lzSheet`.
  - `_lzActions({secondary, onSecondary, primary, onPrimary, busy, danger, icon})` - footer row: quiet text button
    left, one gold filled button right (spinner while busy; red when danger; disabled when onPrimary is null).
  - `_lzConfirm(title, body, {confirm, cancel, danger, icon})` -> Future<bool>. Use for yes/no and destructive
    confirmations instead of hand-built AlertDialogs.
  - `_lzBusy(label)` inline "working" row; `_lzNote(icon, text)` hint box; `_lzSection(label, {trailing})` small caps
    section label; `_lzSteps(current, labels)` step dots.
- Theme helpers you must keep using for every colour on a surface: `_lzFg()` text/icons, `_lzBg()` surfaces,
  `_lzLine()` borders (dark mode depends on it). Static colours: plum, plumDeep, gold, ivory, ink, muted, goldLine,
  vGreen; couple also has gold2 and cardBg; vendor has `card` instead of cardBg. Fonts: `_serif(size:)` for titles.
  Taps: `_h(cb)` wraps callbacks with a haptic tick; `_Press(onTap:, child:)` is the pressable wrapper.

## What "better" means here
1. **One frame.** Rebuild the popup's layout on `_lzFrame` + `_lzActions` where it is a sheet with a title and
   actions. Actions belong in the footer, not at the bottom of a scrolling column. One clear primary action.
2. **No self-drawn grab handles.** `_lzSheet` now draws the handle on phones. Delete any small bar a builder draws
   itself at the top (a ~36-44 x 4-5 rounded Container). Duplicate close buttons too.
3. **No stacked dialogs for simple yes/no.** Replace hand-built confirm AlertDialogs with `_lzConfirm` (danger: true
   for delete/remove/cancel-contract style actions, with a confirm label that names the action, e.g. 'Delete guest').
4. **Progress and errors inside the popup.** Where a popup waits on a network call, show `_lzBusy` or the busy
   spinner on the primary button and keep the popup open; show failures inline in the popup when practical instead
   of only a toast. (A toast after the popup closes on success is fine.)
5. **Structure over text dumps.** Lists of things as rows/cards, counts as stats, choices as tappable cards/chips,
   not paragraphs or `'\n'.join` text.
6. **Copy.** Short, plain, warm, specific. A title + one-line subtitle; cut paragraphs to the one sentence that
   matters. Match the house style: straight hyphen ' - ' for dashes, `\u2019` apostrophes in Dart strings, sentence
   case, no exclamation marks, no emoji, never "Draft".
7. **Forms.** Labelled fields (existing `_lightDeco` in couple / the widget's own input decoration in vendor),
   sensible keyboard types, autofocus on the first field, Enter submits where it's a single field, the primary button
   disabled until the form is valid.
8. **Empty states** inside popups get an icon + one line + the action, not a blank list.
9. Leave genuinely special experiences mostly alone (full-screen editors, photo positioners, emoji pickers, chat
   threads, June's own chat UI): only remove the duplicate handle, fix obvious layout issues, and keep them working.

## Hard rules
- **Behaviour and data stay identical.** Never change Firestore paths/fields, callable function names or arguments,
  what is written, navigation targets, or which feature a button triggers. No new packages, no new imports.
- Only edit code inside the functions assigned to you. Do not rename functions or change their signatures (other
  code calls them). Helper functions you add must be private, uniquely named with your part prefix
  (e.g. `_pcA_rowCard`) and placed inside your assigned functions' region (right after one of them).
- Everything inside `_LazoCoupleDashboardState` / `_LazoVendorDashboardState` (the main State class).
- Dart null-safety and the existing style (explicit types, `<Widget>[...]` literals).

## Deliverable
Write `app-patches/popup_parts/<PART>.py` exposing `apply(s: str) -> str` that performs your edits on the base text
with exact-string replacements. Each `old` string must occur EXACTLY ONCE in the base (assert it) and must lie
entirely inside your assigned functions. Pattern:

```python
def apply(s: str) -> str:
    def rep(old, new):
        nonlocal s
        assert s.count(old) == 1, (s.count(old), old[:80])
        s = s.replace(old, new)
    rep("""...old...""", """...new...""")
    return s
```
Use triple-quoted raw-safe strings carefully: Dart code contains `\u2019`, `\$` and `\n` - write the .py with
the Write tool (not a shell heredoc; the Bash tool mangles backslashes) and use `r"""..."""` raw strings so
backslashes pass through unchanged. Replacing a whole function body is fine and often easiest.

## Compile check (required, must be 0 errors)
```bash
cd /c/Users/kurvh/lazo-directory/app-patches
../.venv/Scripts/python.exe -c "import importlib.util,sys;sp=importlib.util.spec_from_file_location('p','popup_parts/<PART>.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);s=open('popup_parts/base_<couple|vendor>.txt',encoding='utf-8').read();open('/c/Users/kurvh/tools/junecheck/lib/custom_code/widgets/lzp_<PART>.dart','w',encoding='utf-8').write(m.apply(s))"
cd /c/Users/kurvh/tools/junecheck && PUB_CACHE=C:/Users/kurvh/tools/pubcache /c/Users/kurvh/tools/flutter/bin/cache/dart-sdk/bin/dart.exe analyze lib/custom_code/widgets/lzp_<PART>.dart | grep -E "^\s*(error|warning)"
```
(`flutter` itself is blocked by Windows Application Control; the bundled dart.exe works. Do not try to change any
security setting.) Errors must be 0. New warnings only if unavoidable; unused kit helpers are expected and fine.
When done, delete your lzp_<PART>.dart staging file.

## Report back (keep it short)
Per popup: one line - what changed (or "left as is: why"). Then the analyzer result. Mention anything you were
unsure about or a behaviour question for Jesse.
