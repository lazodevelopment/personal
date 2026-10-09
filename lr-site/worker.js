/**
 * LeaseReputation - KV-backed static site Worker.
 *
 * Replaces Cloudflare Pages, which caps direct-upload deployments at 20,000
 * files regardless of plan. KV has no such limit, so the community page count
 * can keep growing.
 *
 * Keys mirror the on-disk paths written by kv_sync.py, so a URL resolves to a
 * key by the same rules a static file server would use.
 *
 * JC-LR-TRACK-1005-001: every HTML page leaves with the first-party visitor
 * tracker appended to <head> (track.js), and the worker answers /api/geo and
 * /assets/lr-track.js itself. JARVIS reads the resulting Firestore sessions.
 */

import { geoResponse, trackerResponse, withTracker } from "./track.js";

const TYPES = {
  html: "text/html; charset=utf-8",
  htm: "text/html; charset=utf-8",
  css: "text/css; charset=utf-8",
  js: "application/javascript; charset=utf-8",
  json: "application/json; charset=utf-8",
  xml: "application/xml; charset=utf-8",
  txt: "text/plain; charset=utf-8",
  svg: "image/svg+xml",
  webmanifest: "application/manifest+json",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  gif: "image/gif",
  avif: "image/avif",
  ico: "image/x-icon",
  woff2: "font/woff2",
  pdf: "application/pdf",
};

const BINARY = new Set(["jpg", "jpeg", "png", "webp", "gif", "avif", "ico", "woff2", "pdf"]);

// Long cache for fingerprinted/immutable assets, short for HTML so nightly
// regeneration is visible without a purge.
function cacheFor(ext) {
  if (ext === "html" || ext === "htm") return "public, max-age=300, s-maxage=3600";
  if (ext === "xml" || ext === "txt" || ext === "json") return "public, max-age=3600";
  return "public, max-age=31536000, immutable";
}

function ext(key) {
  const i = key.lastIndexOf(".");
  return i === -1 ? "" : key.slice(i + 1).toLowerCase();
}

/** Candidate keys for a URL path, in resolution order. */
function candidates(pathname) {
  let p = decodeURIComponent(pathname).replace(/^\/+/, "");
  // reject traversal and control characters before they reach KV
  if (p.includes("..") || /[\x00-\x1f]/.test(p)) return [];
  if (p === "") return ["index.html"];
  if (p.endsWith("/")) return [p + "index.html"];
  if (ext(p)) return [p];
  // extensionless: /az/phoenix -> az/phoenix.html, then az/phoenix/index.html
  return [p + ".html", p + "/index.html"];
}

async function serve(env, key, request) {
  const e = ext(key);
  const isBin = BINARY.has(e);
  const body = await env.SITE.get(key, { type: isBin ? "arrayBuffer" : "text" });
  if (body === null) return null;

  const headers = {
    "content-type": TYPES[e] || "application/octet-stream",
    "cache-control": cacheFor(e),
    "x-content-type-options": "nosniff",
    "referrer-policy": "strict-origin-when-cross-origin",
  };
  if (request.method === "HEAD") return new Response(null, { headers });
  return new Response(body, { headers });
}

export default {
  async fetch(request, env, ctx) {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", {
        status: 405,
        headers: { allow: "GET, HEAD" },
      });
    }

    const url = new URL(request.url);

    // Visitor tracking endpoints (not in KV).
    if (url.pathname === "/api/geo") return geoResponse(request);
    if (url.pathname === "/assets/lr-track.js") return trackerResponse();

    // One origin: https + apex. www.leasereputation.com and plain http were
    // both serving 200 copies of every page (duplicate hosts in GSC).
    if (url.protocol !== "https:" || url.hostname.startsWith("www.")) {
      url.protocol = "https:";
      url.hostname = url.hostname.replace(/^www\./, "");
      return Response.redirect(url.toString(), 301);
    }

    // /index.html and /dir/index.html -> / and /dir/ (canonical form).
    if (url.pathname.endsWith("/index.html")) {
      url.pathname = url.pathname.slice(0, -"index.html".length);
      return Response.redirect(url.toString(), 301);
    }

    // Trailing-slash normalisation: /az/phoenix/ -> /az/phoenix when the
    // extensionless form exists. One canonical URL per page, so the crawler
    // is not fed two addresses for the same content.
    if (url.pathname.length > 1 && url.pathname.endsWith("/")) {
      const bare = url.pathname.replace(/\/+$/, "");
      const hit = await env.SITE.get(bare.replace(/^\/+/, "") + ".html", { type: "text" });
      if (hit !== null) {
        url.pathname = bare;
        return Response.redirect(url.toString(), 301);
      }
    }

    for (const key of candidates(url.pathname)) {
      // /apartments/addison-tx resolved to apartments/addison-tx/index.html
      // and served it at both addresses; send the bare form to the
      // canonical trailing-slash URL instead.
      if (key.endsWith("/index.html") && !url.pathname.endsWith("/")) {
        if ((await env.SITE.get(key, { type: "text" })) !== null) {
          url.pathname = url.pathname + "/";
          return Response.redirect(url.toString(), 301);
        }
        continue;
      }
      const res = await serve(env, key, request);
      if (res) return withTracker(request, res);
    }

    const notFound = await env.SITE.get("404.html", { type: "text" });
    return new Response(notFound ?? "Not Found", {
      status: 404,
      headers: { "content-type": "text/html; charset=utf-8" },
    });
  },
};
