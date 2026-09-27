// Canonical host: www.elizabethscottweddings.com -> elizabethscottweddings.com (301, path + query kept).
// GSC was indexing the www copy of the homepage as a separate URL; Pages' _redirects cannot match on host.
export async function onRequest({ request, next }) {
  const url = new URL(request.url);
  if (url.hostname === "www.elizabethscottweddings.com") {
    url.hostname = "elizabethscottweddings.com";
    return Response.redirect(url.toString(), 301);
  }
  return next();
}
