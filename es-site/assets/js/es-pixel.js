/* es-pixel.js — Meta Pixel for elizabethscottweddings.com
 * Base PageView on every page, plus route-based events:
 *   /book        → InitiateCheckout (they opened the booking page)
 *   /booked      → Purchase          (back from signing; value from the booking page)
 *   /contact     → nothing here; the form fires Lead on submit (see contact page)
 * The booking page calls window.eswPixel('Lead', {...}) when a card is saved.
 */
(function () {
  var PIXEL_ID = '1245257617279907';
  if (/bot|crawl|spider|facebookexternalhit|headless|lighthouse/i.test(navigator.userAgent)) return;
  !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};
  if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;t.src=v;
  s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', PIXEL_ID);
  fbq('track', 'PageView');

  window.eswPixel = function (event, params) { try { fbq('track', event, params || {}); } catch (e) {} };

  var p = location.pathname.replace(/\/+$/, '') || '/';
  var ss = null; try { ss = window.sessionStorage; } catch (e) {}
  if (p === '/book') {
    fbq('track', 'InitiateCheckout', { content_category: 'wedding_booking' });
  } else if (p === '/booked' || p.indexOf('/booked') === 0 || p === '/book/thank-you') {
    var v = 0, pkg = '';
    try { v = Number(ss && ss.getItem('esw_fb_value')) || 0; pkg = (ss && ss.getItem('esw_fb_pkg')) || ''; } catch (e) {}
    if (!(ss && ss.getItem('esw_fb_purchased'))) {          // fire once per session
      fbq('track', 'Purchase', { value: v, currency: 'USD', content_name: pkg || 'wedding_booking', content_type: 'product' });
      try { ss.setItem('esw_fb_purchased', '1'); } catch (e) {}
    }
  } else if (/^\/(collections|packages|pricing)/.test(p) || /^\/venues\//.test(p)) {
    fbq('track', 'ViewContent', { content_category: p.split('/')[1], content_name: p });
  }
})();
