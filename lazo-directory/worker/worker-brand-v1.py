# JC-LAZO-WORKER-0913-BRAND-001
# Run from C:\Users\kurvh\lazo-directory\worker:   python worker-brand-v1.py
# Then:  npx wrangler deploy
#
# Vendor branding (vendors.brand {primary, accent, font} + vendors.logoUrl)
# applied to every couple-facing page the worker serves:
#   /f/{inquiry}      already reads brand (PAY-001) - unchanged
#   /g/{slug}         gallery: brand + logo injected as window.LAZO_GALLERY.brand
#                     and CSS variables --brand-primary/--brand-accent/--brand-font
#                     on :root, plus a small header strip with the vendor's logo
#                     and name above the gallery
#   /lead/{vendorId}  hosted lead page: hero + button take the vendor's colors
# Requires LEAD-001 already applied.
import io, sys, shutil

p = "src/index.js"
s = io.open(p, encoding="utf-8").read()
if "BRAND-001" in s:
    sys.exit("already patched")
if "LEAD-001" not in s:
    sys.exit("run worker-lead-v1.py first")

# ---- gallery: pull the vendor's brand alongside the gallery doc -----------
old = '''  const payload = {
    slug,
    names: gal.names,'''
new = '''  // BRAND-001: the vendor's colors and logo ride along with the gallery.
  const brand = await vendorBrand(gal.vendorId);
  const payload = {
    slug,
    brand,
    names: gal.names,'''
if old not in s: sys.exit("gallery payload anchor not found")
s = s.replace(old, new, 1)

old = '''  html = html.replace(/<title>[^<]*<\\/title>/, `<title>${esc(title)}</title>`);
  html = html.replace("</head>", head + inject + "\\n</head>");'''
new = '''  html = html.replace(/<title>[^<]*<\\/title>/, `<title>${esc(title)}</title>`);
  html = html.replace("</head>", head + inject + brandHead(brand) + "\\n</head>");
  if (brand.logoUrl || brand.name) html = html.replace(/<body([^>]*)>/, (m) => m + brandStrip(brand));'''
if old not in s: sys.exit("gallery head anchor not found")
s = s.replace(old, new, 1)

# ---- hosted lead page: colors from the brand ------------------------------
old = '''  const cover = fsVal(v.coverUrl) || "";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Inquire - ${escF(name)}</title>
<style>body{margin:0;background:#FAF6F0;font-family:Helvetica,Arial,sans-serif;color:#241E2B}
.hero{background:#52284F ${cover ? `url('https://wsrv.nl/?url=${encodeURIComponent(cover)}&w=1400&q=70') center/cover` : ""};padding:52px 20px 40px;text-align:center;color:#fff}'''
new = '''  const cover = fsVal(v.coverUrl) || "";
  const b = brandOf(v);
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Inquire - ${escF(name)}</title>
<style>body{margin:0;background:#FAF6F0;font-family:${b.font === "serif" ? "Georgia,serif" : "Helvetica,Arial,sans-serif"};color:#241E2B}
.hero{background:${b.primary} ${cover ? `url('https://wsrv.nl/?url=${encodeURIComponent(cover)}&w=1400&q=70') center/cover` : ""};padding:52px 20px 40px;text-align:center;color:#fff}
.hero img.logo{width:64px;height:64px;border-radius:14px;background:#fff;object-fit:contain;margin-bottom:12px}'''
if old not in s: sys.exit("lead page style anchor not found")
s = s.replace(old, new, 1)

old = '''<body><header class="hero"><h1>${escF(name)}</h1><p>Tell us about your day - we'll get right back to you.</p></header>
<main><script src="https://meetlazo.com/embed/lead.js" data-vendor="${escF(vendorId)}" data-key="${escF(key)}" data-heading=" "></script>'''
new = '''<body><header class="hero">${b.logoUrl ? `<img class="logo" src="https://wsrv.nl/?url=${encodeURIComponent(b.logoUrl)}&w=128&h=128&fit=contain" alt="">` : ""}<h1>${escF(name)}</h1><p>Tell us about your day - we'll get right back to you.</p></header>
<main><script src="https://meetlazo.com/embed/lead.js" data-vendor="${escF(vendorId)}" data-key="${escF(key)}" data-heading=" " data-accent="${b.primary}"></script>'''
if old not in s: sys.exit("lead page body anchor not found")
s = s.replace(old, new, 1)

fn = r'''
// JC-LAZO-WORKER-0913-BRAND-001 -------------------------------------------
const HEX = /^#[0-9a-f]{6}$/i;
function brandOf(v) {
  const raw = v && v.brand ? fsVal(v.brand) : null;
  const b = raw && typeof raw === "object" ? raw : {};
  return {
    name: v ? (fsVal(v.name) || "") : "",
    logoUrl: v ? (fsVal(v.logoUrl) || "") : "",
    primary: HEX.test(b.primary || "") ? b.primary : "#52284F",
    accent: HEX.test(b.accent || "") ? b.accent : "#D9B77C",
    font: b.font === "serif" ? "serif" : "sans",
  };
}
async function vendorBrand(vendorId) {
  if (!vendorId) return brandOf(null);
  const v = await fsDoc("vendors", vendorId);
  return brandOf(v);
}
function brandHead(b) {
  return `\n<style>:root{--brand-primary:${b.primary};--brand-accent:${b.accent};--brand-font:${b.font === "serif" ? "Georgia,serif" : "Helvetica,Arial,sans-serif"}}` +
    `.lazo-brand{display:flex;align-items:center;gap:12px;padding:12px 18px;background:${b.primary};color:#fff;font-family:var(--brand-font);font-size:14px}` +
    `.lazo-brand img{width:36px;height:36px;border-radius:9px;background:#fff;object-fit:contain}.lazo-brand b{font-weight:600;letter-spacing:.2px}</style>`;
}
function brandStrip(b) {
  return `\n<div class="lazo-brand">${b.logoUrl ? `<img src="https://wsrv.nl/?url=${encodeURIComponent(b.logoUrl)}&w=72&h=72&fit=contain" alt="">` : ""}<b>${esc(b.name)}</b></div>`;
}
'''
shutil.copy(p, p + ".bak-brand1")
io.open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip() + "\n" + fn)
print("patched", p, "- now: npx wrangler deploy")
