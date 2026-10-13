"""patch_clip_range.py - JC-LAZO-JUNE-CLIP-RANGE-1013-001
/clip/<id> answered every request with the whole file and status 200 while advertising
"accept-ranges: bytes". iOS AVPlayer (behind audioplayers / just_audio) probes a clip with
"Range: bytes=0-1", gets the full body back, and refuses to play it: the text shows, no voice.
Live radio streams skip that probe, which is why the radio still played.
Fix: honour single byte ranges (206 + content-range), HEAD, and 416 out of range, in BOTH
workers (june-hub and jovi-hub share the clip design).  python patch_clip_range.py
"""
from pathlib import Path

HELPER = r'''
// JC-LAZO-JUNE-CLIP-RANGE-1013-001: a clip served the way AVPlayer and ExoPlayer expect (byte ranges, HEAD)
function clipResponse(request, buf, type) {
  const size = buf.byteLength;
  const base = { "content-type": type, "cache-control": "private, max-age=600", "accept-ranges": "bytes" };
  const head = request.method === "HEAD";
  const h = (request.headers.get("range") || "").trim();
  const m = /^bytes=(\d*)-(\d*)$/.exec(h);
  if (!m || (m[1] === "" && m[2] === "")) return new Response(head ? null : buf, { status: 200, headers: { ...base, "content-length": String(size) } });
  let start, end;
  if (m[1] === "") { start = Math.max(0, size - +m[2]); end = size - 1; }
  else { start = +m[1]; end = m[2] === "" ? size - 1 : Math.min(+m[2], size - 1); }
  if (start >= size || start > end) return new Response(null, { status: 416, headers: { ...base, "content-range": `bytes */${size}` } });
  return new Response(head ? null : buf.slice(start, end + 1), { status: 206, headers: { ...base, "content-range": `bytes ${start}-${end}/${size}`, "content-length": String(end - start + 1) } });
}
'''

TARGETS = [
    (Path(r"C:\Users\kurvh\lazo-directory\june-hub\src\index.js"), "JUNE"),
    (Path(r"C:\Users\kurvh\jovi-admin\jovi-hub\src\index.js"), "JOVI"),
]
for path, kv in TARGETS:
    s = path.read_text(encoding="utf-8")
    if "JC-LAZO-JUNE-CLIP-RANGE-1013-001" in s:
        print("already patched", path.name, kv); continue
    old = f'const a = await env.{kv}.get("clip_" + id, "arrayBuffer"); if (!a) return new Response("Gone", {{ status: 404 }}); return new Response(a, {{ headers: {{ "content-type": audioType(a), "cache-control": "private, max-age=600", "accept-ranges": "bytes" }} }}); }}'
    new = f'const a = await env.{kv}.get("clip_" + id, "arrayBuffer"); if (!a) return new Response("Gone", {{ status: 404 }}); return clipResponse(request, a, audioType(a)); }}'
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{path}: clip handler anchor found {n}x")
    s = s.replace(old, new)
    anchor = "const isWav = (buf) =>"
    if s.count(anchor) != 1:
        raise SystemExit(f"{path}: isWav anchor not unique")
    s = s.replace(anchor, HELPER.strip() + "\n" + anchor)
    path.write_text(s, encoding="utf-8")
    print("patched", path, kv)
