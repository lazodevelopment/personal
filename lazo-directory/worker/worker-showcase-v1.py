# JC-LAZO-WORKER-0913-SHOWCASE-001
# Run from C:\Users\kurvh\lazo-directory\worker:   python worker-showcase-v1.py
# Then:  npx wrangler deploy
#
#   /real/{slug}   a public, indexable page for a gallery the vendor marked as
#                  a showcase (galleries/{slug}.showcase == true): same
#                  gallery template, no passcode, share previews on, links back
#                  to the vendor's public page. The couple's private /g/{slug}
#                  is untouched.
#   /g/{slug}/i/{id}/thumb|web   readable without a passcode when the gallery
#                  is a showcase (full-size downloads still need the cookie).
# Requires BRAND-001 already applied.
import io, sys, shutil

p = "src/index.js"
s = io.open(p, encoding="utf-8").read()
if "SHOWCASE-001" in s:
    sys.exit("already patched")
if "BRAND-001" not in s:
    sys.exit("run worker-brand-v1.py first")

# loadGallery carries the showcase flag + vendor slug
old = '''    passcodeHash: (g("passcodeHash") || "").toString(),
    expiresAt,
  };
}'''
new = '''    passcodeHash: (g("passcodeHash") || "").toString(),
    expiresAt,
    showcase: g("showcase") === true,
    showcaseTitle: g("showcaseTitle") || "",
    showcaseBlurb: g("showcaseBlurb") || "",
  };
}'''
if old not in s: sys.exit("loadGallery anchor not found")
s = s.replace(old, new, 1)

# images: showcase galleries serve thumb/web without the cookie
old = '''  if (gal.passcodeHash && !(await hasPass(req, slug, env)))
    return new Response("Locked", { status: 403 });
  if (variant === "full" && !gal.downloadsOn)'''
new = '''  const showcasePublic = gal.showcase && variant !== "full";
  if (gal.passcodeHash && !showcasePublic && !(await hasPass(req, slug, env)))
    return new Response("Locked", { status: 403 });
  if (variant === "full" && !gal.downloadsOn)'''
if old not in s: sys.exit("serveGalleryImage anchor not found")
s = s.replace(old, new, 1)

# route
anchor = '    const gMatch = url.pathname.match(/^\\/g\\/([a-z0-9-]{1,80})\\/?$/);'
if anchor not in s: sys.exit("/g/ route anchor not found")
route = '''    // JC-LAZO-WORKER-0913-SHOWCASE-001: public real-wedding pages
    const realMatch = url.pathname.match(/^\\/real\\/([a-z0-9-]{1,80})\\/?$/);
    if (realMatch && req.method === "GET") {
      const resp = await renderShowcase(realMatch[1], req, env);
      if (resp) return resp;
      return new Response("Not found", { status: 404, headers: { "content-type": TYPES.html } });
    }
'''
s = s.replace(anchor, route + anchor, 1)

fn = r'''
// JC-LAZO-WORKER-0913-SHOWCASE-001 ----------------------------------------
async function renderShowcase(slug, req, env) {
  const gal = await loadGallery(slug, env);
  if (!gal || !gal.showcase) return null;
  const asset = await env.SITE.get("gallery/index.html");
  if (!asset) return null;
  let html = await asset.text();
  const photos = await galleryManifest(slug, env);
  const brand = await vendorBrand(gal.vendorId);
  const v = gal.vendorId ? await fsDoc("vendors", gal.vendorId) : null;
  const vendorSlug = v ? (fsVal(v.slug) || gal.vendorSlug) : gal.vendorSlug;
  const metro = v ? (fsVal(v.metroId) || "") : "";
  const cat = v ? (fsVal(v.category) || "") : "";
  const vendorUrl = metro && cat && vendorSlug ? `https://meetlazo.com/${metro}/${cat}/${vendorSlug}/` : "https://meetlazo.com/";
  const title = gal.showcaseTitle || gal.names || "A real wedding";
  const payload = {
    slug, brand, names: gal.names, dateIso: gal.dateIso, message: gal.showcaseBlurb || gal.message,
    vendorName: gal.vendorName, vendorSlug, vendorUrl, coverId: gal.coverId, photoCount: gal.photoCount,
    downloadsOn: false, storeOn: false, expiresAt: "", locked: false, showcase: true,
    photos: photos.map((p) => ({ id: p.id, name: p.name, w: p.w, h: p.h })),
  };
  const cover = gal.coverId ? `https://meetlazo.com/g/${slug}/i/${gal.coverId}/web` : (photos[0] ? `https://meetlazo.com/g/${slug}/i/${photos[0].id}/web` : "");
  const pageUrl = `https://meetlazo.com/real/${slug}`;
  const desc = `${title}${gal.dateIso ? " \u00b7 " + gal.dateIso : ""} \u00b7 photographed by ${gal.vendorName}`;
  const head =
    `<meta property="og:type" content="article">\n<meta property="og:site_name" content="Lazo">\n<meta property="og:title" content="${esc(title + " \u2014 " + gal.vendorName)}">\n<meta property="og:description" content="${esc(desc)}">\n<meta property="og:url" content="${pageUrl}">\n<link rel="canonical" href="${pageUrl}">\n<meta name="description" content="${esc(desc)}">\n` +
    (cover ? `<meta property="og:image" content="${esc(cover)}">\n<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="${esc(cover)}">\n` : `<meta name="twitter:card" content="summary">\n`) +
    `<script type="application/ld+json">${JSON.stringify({ "@context": "https://schema.org", "@type": "ImageGallery", name: title, description: desc, url: pageUrl, author: { "@type": "Organization", name: gal.vendorName, url: vendorUrl } })}</script>\n`;
  const inject = `<script>window.LAZO_GALLERY=${JSON.stringify(payload).replace(/</g, "\\u003c")};</script>`;
  html = html.replace(/<meta name="robots"[^>]*>/gi, "");
  html = html.replace(/<title>[^<]*<\/title>/, `<title>${esc(title)} \u2014 ${esc(gal.vendorName)} | Lazo</title>`);
  html = html.replace("</head>", head + inject + brandHead(brand) + "\n</head>");
  html = html.replace(/<body([^>]*)>/, (m) => m + `\n<div class="lazo-brand"><a href="${esc(vendorUrl)}" style="color:inherit;text-decoration:none;display:flex;align-items:center;gap:12px">${brand.logoUrl ? `<img src="https://wsrv.nl/?url=${encodeURIComponent(brand.logoUrl)}&w=72&h=72&fit=contain" alt="">` : ""}<b>${esc(gal.vendorName)}</b><span style="opacity:.8;font-size:12px">\u00b7 real wedding \u00b7 see more &rarr;</span></a></div>`);
  return new Response(html, { headers: {
    "content-type": TYPES.html,
    "cache-control": "public, max-age=300, s-maxage=3600",
    "x-lazo": "tied-together",
  }});
}
'''
shutil.copy(p, p + ".bak-showcase1")
io.open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip() + "\n" + fn)
print("patched", p, "- now: npx wrangler deploy")
