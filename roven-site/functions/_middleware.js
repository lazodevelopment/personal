// roven-site/functions/_middleware.js (JC-RVN-TRACK-1005-001)
//
// Appends the visitor tracker to every HTML page on the way out, so none of the ~3,000 generated
// pages has to carry the tag (and a tracker change never needs a page regeneration). Static assets
// and the /api/* functions pass through untouched.

const TRACK_V = "1005-001";
const TAG = `<script defer src="/assets/rvn-track.js?v=${TRACK_V}"></script>`;

export async function onRequest({ request, next }) {
  const response = await next();
  try {
    const ct = response.headers.get("content-type") || "";
    if (!ct.includes("text/html")) return response;
    return new HTMLRewriter()
      .on("head", { element(el) { el.append(TAG, { html: true }); } })
      .transform(response);
  } catch (e) {
    return response;
  }
}
