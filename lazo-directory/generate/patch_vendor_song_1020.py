r"""patch_vendor_song_1020.py - JC-LAZO-VSONG-1020-002: the storefront song on the site.

Appends to generate/static/lazo.js a player that runs only on vendor pages
(.vp[data-vendor-id]): it asks meetlazo.com/music/song?v=<id> and, when the
vendor picked a song in the app, mounts the same record pill the couple sites
use (bottom-left, spins while playing, one tap pauses, the browser's autoplay
refusal turns into 'tap anywhere'). Styles go to lazo.vendor.css under the
vendor page's own variables, with the night theme covered by --card/--ink.

Lives in lazo.js rather than vendor.html so every built page gets it the moment
the two assets are pushed (deploy/push_asset.py), without a rebuild.

    python generate\patch_vendor_song_1020.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAG = "JC-LAZO-VSONG-1020-002"

js = ROOT / "generate" / "static" / "lazo.js"
s = js.read_text(encoding="utf-8")
assert TAG not in s, "lazo.js already patched"
player = r'''
/* JC-LAZO-VSONG-1020-002: the vendor's storefront song. Vendor pages only; the
   worker answers /music/song?v= with a live clip when the vendor picked one in
   the app (vendors.song), else null and nothing is mounted. Same pill as the
   couple sites: a record that turns while it plays, one tap pauses, and when
   the browser refuses autoplay the first tap anywhere starts it. */
(function () {
  if (window.top !== window) return;
  var vp = document.querySelector('.vp[data-vendor-id]');
  var id = vp && vp.getAttribute('data-vendor-id');
  if (!id) return;
  fetch('https://meetlazo.com/music/song?v=' + encodeURIComponent(id))
    .then(function (r) { return r.json(); })
    .then(function (j) { var S = j && j.song; if (S && S.src) mount(S); })
    .catch(function () {});
  function mount(S) {
    var reduce = false; try { reduce = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
    var a = new Audio(); a.preload = 'auto'; a.src = S.src; a.loop = !!S.loop; a.volume = 0;
    var el = document.createElement('button'); el.type = 'button'; el.className = 'oursong'; el.setAttribute('aria-label', 'Play their song');
    var esc = function (t) { return String(t || '').replace(/[<>&"]/g, function (c) { return { '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]; }); };
    el.innerHTML = '<span class="disc"' + (S.art ? ' style="background-image:url(&quot;' + esc(S.art) + '&quot;)"' : '') + '></span>'
      + '<span class="tx"><span class="t">' + esc(S.title || 'Their song') + '</span><span class="a">' + esc(S.artist || '') + '</span><span class="h" data-h>Tap to play</span></span>'
      + '<span class="pp" aria-hidden="true"></span>';
    document.body.appendChild(el);
    var hint = el.querySelector('[data-h]'), fade = null, armed = false;
    function setHint(t) { if (hint) hint.textContent = t; }
    function fadeTo(v, ms) { clearInterval(fade); var steps = Math.max(1, Math.round(ms / 40)), i = 0, from = a.volume; fade = setInterval(function () { i++; a.volume = Math.max(0, Math.min(1, from + (v - from) * (i / steps))); if (i >= steps) clearInterval(fade); }, 40); }
    function play() { var p = a.play(); if (p && p.then) p.then(function () { el.classList.add('playing'); setHint('Now playing'); fadeTo(.9, reduce ? 0 : 1400); try { sessionStorage.removeItem('lzvsongoff'); } catch (e) {} }).catch(function () { arm(); }); }
    function pause() { fadeTo(0, reduce ? 0 : 500); setTimeout(function () { a.pause(); }, reduce ? 0 : 520); el.classList.remove('playing'); el.classList.add('off'); setHint('Paused · tap to play'); try { sessionStorage.setItem('lzvsongoff', '1'); } catch (e) {} }
    function arm() {
      if (armed) return; armed = true; setHint('Tap anywhere to play');
      var go = function () { document.removeEventListener('pointerdown', go, true); document.removeEventListener('keydown', go, true); if (!el.classList.contains('playing') && !el.classList.contains('off')) play(); };
      document.addEventListener('pointerdown', go, true); document.addEventListener('keydown', go, true);
    }
    el.addEventListener('click', function (e) { e.stopPropagation(); if (el.classList.contains('playing')) pause(); else { el.classList.remove('off'); play(); } });
    a.addEventListener('ended', function () { el.classList.remove('playing'); setHint('Play it again'); });
    a.addEventListener('error', function () { el.remove(); });
    var off = false; try { off = sessionStorage.getItem('lzvsongoff') === '1'; } catch (e) {}
    if (off) { el.classList.add('off'); setHint('Tap to play'); }
    else if (S.autoplay !== false) { play(); }
    else { setHint('Tap to play'); }
  }
})();
'''
js.write_text(s.rstrip("\n") + "\n" + player, encoding="utf-8")

css = ROOT / "generate" / "static" / "lazo.vendor.css"
c = css.read_text(encoding="utf-8")
assert TAG not in c, "lazo.vendor.css already patched"
styles = r'''
/* JC-LAZO-VSONG-1020-002: the vendor's storefront song - the record pill, bottom-left,
   mounted by lazo.js when vendors.song is set. Same shape as the couple sites' pill. */
.oursong{position:fixed;left:16px;bottom:16px;z-index:45;display:flex;align-items:center;gap:10px;max-width:min(78vw,300px);padding:6px 14px 6px 6px;border-radius:999px;background:var(--card,#FFFDF9);color:var(--ink,#241E2B);border:1px solid var(--vx-line,rgba(82,40,79,.14));box-shadow:0 14px 34px -14px rgba(36,30,43,.35),0 1px 2px rgba(36,30,43,.08);cursor:pointer;font-family:inherit;text-align:left;transition:transform .26s var(--ease-out,ease),box-shadow .26s var(--ease-out,ease),opacity .4s ease;animation:lzvsong-in .7s var(--ease-out,ease) both;animation-delay:.9s}
.oursong:active{transform:scale(.97);transition-duration:.09s}
.oursong .disc{position:relative;width:42px;height:42px;border-radius:50%;flex:0 0 auto;background:#1a1a1a center/cover;box-shadow:inset 0 0 0 1px rgba(255,255,255,.15),0 2px 6px rgba(0,0,0,.25);overflow:hidden}
.oursong .disc::after{content:"";position:absolute;left:50%;top:50%;width:8px;height:8px;margin:-4px 0 0 -4px;border-radius:50%;background:var(--card,#FFFDF9);box-shadow:0 0 0 2px rgba(0,0,0,.35)}
.oursong.playing .disc{animation:lzvsong-spin 3.2s linear infinite}
.oursong .tx{min-width:0;line-height:1.2}
.oursong .t{display:block;font-size:12.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.oursong .a{display:block;font-size:11px;color:var(--muted,#6B5F72);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.oursong .h{display:block;font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--gold-ink,#8A6A2F);margin-top:2px}
.oursong .pp{width:28px;height:28px;border-radius:50%;flex:0 0 auto;border:1px solid var(--vx-line,rgba(82,40,79,.14));display:flex;align-items:center;justify-content:center;color:var(--gold-ink,#8A6A2F);font-size:11px}
.oursong .pp::before{content:"\25B6";margin-left:2px}
.oursong.playing .pp::before{content:"\2016";margin-left:0;font-weight:700}
.oursong.off{opacity:.82}
@keyframes lzvsong-spin{to{transform:rotate(360deg)}}
@keyframes lzvsong-in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.oursong{animation:none}.oursong.playing .disc{animation:none}}
@media (max-width:640px){.oursong{left:12px;bottom:calc(12px + env(safe-area-inset-bottom,0px))}}
/* on phones the pill steps up over the inquiry bar while the bar is showing */
@media (max-width:720px){.oursong{transition:bottom .45s var(--ease-out,ease),transform .26s var(--ease-out,ease),opacity .4s ease}
  html:not(.vx-io) body:has(.vx-bar) .oursong,html.vx-io body:has(.vx-bar.on) .oursong,html.has-appbar .oursong{bottom:calc(84px + env(safe-area-inset-bottom,0px))}}
'''
css.write_text(c.rstrip("\n") + "\n" + styles, encoding="utf-8")
print("patched lazo.js and lazo.vendor.css")
