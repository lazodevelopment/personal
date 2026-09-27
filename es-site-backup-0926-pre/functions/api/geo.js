// Cloudflare Pages Function: /api/geo — city + coordinates from Cloudflare's edge, no third-party lookup.
export async function onRequestGet({ request }) {
  const cf = request.cf || {};
  const body = {
    city: cf.city || "", region: cf.region || cf.regionCode || "", country: cf.country || "",
    lat: cf.latitude ? Number(cf.latitude) : null, lng: cf.longitude ? Number(cf.longitude) : null,
  };
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store", "Access-Control-Allow-Origin": "*" },
  });
}
