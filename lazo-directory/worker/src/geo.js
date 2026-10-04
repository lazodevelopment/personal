// worker/src/geo.js — JC-LAZO-GEO-0907-001
// Cloudflare already knows roughly where a visitor is (request.cf.latitude /
// longitude, from the connecting IP). This picks the nearest live Lazo metro
// and hands it to the page as window.LAZO_GEO = {id, name}. The home page
// (JC-LAZO-HOME-0907-005) uses it to show the visitor's own city. No cookies,
// no permission prompt, nothing stored — a page-load hint, not tracking.
//
// Wire it in index.js (two lines):
//   import { withGeo } from './geo.js';
//   ...and where an HTML response is about to be returned:  return withGeo(request, response);
// It is a no-op for non-HTML responses and for visitors more than 250 miles
// from any live metro, so it is safe to wrap every response.

export const METROS = [
  ['phoenix', 'Phoenix', 33.45, -112.07], ['tucson', 'Tucson', 32.22, -110.97],
  ['denver', 'Denver', 39.74, -104.99], ['salt-lake-city', 'Salt Lake City', 40.76, -111.89],
  ['las-vegas', 'Las Vegas', 36.17, -115.14], ['los-angeles', 'Los Angeles', 34.05, -118.24],
  ['san-diego', 'San Diego', 32.72, -117.16], ['san-francisco-bay', 'San Francisco Bay', 37.77, -122.42],
  ['sacramento', 'Sacramento', 38.58, -121.49], ['seattle', 'Seattle', 47.61, -122.33],
  ['portland', 'Portland', 45.52, -122.68], ['dallas-fort-worth', 'Dallas-Fort Worth', 32.78, -96.80],
  ['houston', 'Houston', 29.76, -95.37], ['austin', 'Austin', 30.27, -97.74],
  ['san-antonio', 'San Antonio', 29.42, -98.49], ['chicago', 'Chicago', 41.88, -87.63],
  ['minneapolis', 'Minneapolis', 44.98, -93.27], ['st-louis', 'St. Louis', 38.63, -90.20],
  ['kansas-city', 'Kansas City', 39.10, -94.58], ['new-orleans', 'New Orleans', 29.95, -90.07],
  ['milwaukee', 'Milwaukee', 43.04, -87.91], ['memphis', 'Memphis', 35.15, -90.05],
  ['nashville', 'Nashville', 36.16, -86.78], ['atlanta', 'Atlanta', 33.75, -84.39],
  ['miami', 'Miami', 25.76, -80.19], ['orlando', 'Orlando', 28.54, -81.38],
  ['tampa', 'Tampa', 27.95, -82.46], ['jacksonville', 'Jacksonville', 30.33, -81.66],
  ['charlotte', 'Charlotte', 35.23, -80.84], ['raleigh-durham', 'Raleigh-Durham', 35.78, -78.64],
  ['charleston', 'Charleston', 32.78, -79.93], ['savannah', 'Savannah', 32.08, -81.10],
  ['new-york-city', 'New York City', 40.71, -74.01], ['boston', 'Boston', 42.36, -71.06],
  ['philadelphia', 'Philadelphia', 39.95, -75.17], ['washington-dc', 'Washington DC', 38.91, -77.04],
  ['richmond', 'Richmond', 37.54, -77.44], ['virginia-beach', 'Virginia Beach', 36.85, -75.98],
  ['columbus', 'Columbus', 39.96, -83.00], ['indianapolis', 'Indianapolis', 39.77, -86.16],
  ['detroit', 'Detroit', 42.33, -83.05], ['pittsburgh', 'Pittsburgh', 40.44, -79.99],
  ['cincinnati', 'Cincinnati', 39.10, -84.51], ['cleveland', 'Cleveland', 41.50, -81.69],
  ['louisville', 'Louisville', 38.25, -85.76],
  // tranche 6 (2026-09-16), missed when those metros were added
  ['inland-empire', 'Inland Empire', 33.95, -117.40],
  ['baltimore', 'Baltimore', 39.29, -76.61],
  ['orange-county', 'Orange County', 33.72, -117.83],
  ['providence', 'Providence', 41.82, -71.41],
  ['hartford-new-haven', 'Hartford-New Haven', 41.60, -72.73],
  ['oklahoma-city', 'Oklahoma City', 35.47, -97.52],
  ['buffalo', 'Buffalo', 42.89, -78.88],
  ['birmingham', 'Birmingham', 33.52, -86.81],
  ['grand-rapids', 'Grand Rapids', 42.96, -85.67],
  ['santa-barbara', 'Santa Barbara', 34.42, -119.70],
  ['palm-springs', 'Palm Springs', 33.83, -116.55],
  ['asheville', 'Asheville', 35.60, -82.55],
  ['honolulu', 'Honolulu', 21.31, -157.86],
  // tranche 7 (2026-09-21)
  ['rochester', 'Rochester', 43.16, -77.61],
  ['albany', 'Albany', 42.65, -73.76],
  ['syracuse', 'Syracuse', 43.05, -76.15],
  ['lehigh-valley', 'Lehigh Valley', 40.61, -75.49],
  ['tulsa', 'Tulsa', 36.15, -95.99],
  ['omaha', 'Omaha', 41.26, -95.93],
  ['albuquerque', 'Albuquerque', 35.08, -106.65],
  ['el-paso', 'El Paso', 31.76, -106.48],
  ['fresno', 'Fresno', 36.74, -119.79],
  ['bakersfield', 'Bakersfield', 35.37, -119.02],
  ['colorado-springs', 'Colorado Springs', 38.83, -104.82],
  ['boise', 'Boise', 43.62, -116.20],
  ['des-moines', 'Des Moines', 41.59, -93.62],
  ['madison', 'Madison', 43.07, -89.40],
  ['knoxville', 'Knoxville', 35.96, -83.92],
  ['greenville-sc', 'Greenville', 34.85, -82.39],
  ['columbia-sc', 'Columbia', 34.00, -81.03],
  ['baton-rouge', 'Baton Rouge', 30.45, -91.19],
  ['dayton', 'Dayton', 39.76, -84.19],
  ['toledo', 'Toledo', 41.65, -83.54],
  ['fort-myers-naples', 'Fort Myers', 26.64, -81.87],
  ['sarasota', 'Sarasota', 27.34, -82.53],
  ['daytona-beach', 'Daytona Beach', 29.21, -81.02],
  ['key-west', 'Key West', 24.56, -81.78],
  ['greensboro', 'Greensboro', 36.07, -79.79],
  ['wilmington-nc', 'Wilmington', 34.23, -77.94],
  ['outer-banks', 'Outer Banks', 36.03, -75.68],
  ['napa-sonoma', 'Napa', 38.30, -122.29],
  ['lake-tahoe-reno', 'Lake Tahoe', 38.94, -119.98],
  ['maui', 'Maui', 20.89, -156.47],
  ['sedona', 'Sedona', 34.87, -111.76],
  ['monterey-big-sur', 'Monterey', 36.60, -121.89],
  ['aspen-vail', 'Aspen', 39.19, -106.82],
  ['jackson-hole', 'Jackson Hole', 43.48, -110.76],
  ['cape-cod', 'Cape Cod', 41.65, -70.29],
  ['hudson-valley', 'Hudson Valley', 41.70, -73.92],
  ['hamptons', 'The Hamptons', 40.88, -72.39],
  ['poconos', 'Poconos', 40.99, -75.19],
  ['smoky-mountains', 'Gatlinburg', 35.71, -83.51],
  ['anchorage', 'Anchorage', 61.22, -149.90],
  ['little-rock', 'Little Rock', 34.75, -92.29],
  ['wichita', 'Wichita', 37.69, -97.33],
  ['portland-maine', 'Portland', 43.66, -70.26],
  ['jackson-ms', 'Jackson', 32.30, -90.18],
  ['billings', 'Billings', 45.78, -108.50],
  ['fargo', 'Fargo', 46.88, -96.79],
  ['manchester-nh', 'Manchester', 43.00, -71.45],
  ['sioux-falls', 'Sioux Falls', 43.55, -96.73],
  ['burlington-vt', 'Burlington', 44.48, -73.21],
  ['charleston-wv', 'Charleston', 38.35, -81.63],
];

const MAX_MILES = 250;

function miles(lat1, lon1, lat2, lon2) {
  const r = (d) => (d * Math.PI) / 180;
  const a = Math.sin(r(lat2 - lat1) / 2) ** 2
    + Math.cos(r(lat1)) * Math.cos(r(lat2)) * Math.sin(r(lon2 - lon1) / 2) ** 2;
  return 3958.8 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function nearestMetro(cf) {
  if (!cf || cf.latitude == null || cf.longitude == null) return null;
  const lat = Number(cf.latitude), lon = Number(cf.longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
  let best = null, bestMi = Infinity;
  for (const [id, name, mlat, mlon] of METROS) {
    const d = miles(lat, lon, mlat, mlon);
    if (d < bestMi) { best = { id, name, miles: Math.round(d) }; bestMi = d; }
  }
  return best && bestMi <= MAX_MILES ? best : null;
}

export function withGeo(request, response) {
  try {
    const ct = response.headers.get('content-type') || '';
    if (!ct.includes('text/html')) return response;
    const m = nearestMetro(request.cf);
    if (!m) return response;
    const tag = `<script>window.LAZO_GEO=${JSON.stringify({ id: m.id, name: m.name })};</script>`;
    return new HTMLRewriter()
      .on('head', { element(el) { el.append(tag, { html: true }); } })
      .transform(response);
  } catch (e) {
    return response;
  }
}

// JC-LAZO-CONSENT-1004: every HTML page gets window.LAZO_CF = {c: country, r: region code}
// at the top of <head>, before base.html's pixel gate runs. The gate asks for consent in the
// EU/EEA, the UK and California and runs opt-out everywhere else; with no hint it asks.
export function withRegion(request, response) {
  try {
    const ct = response.headers.get('content-type') || '';
    if (!ct.includes('text/html')) return response;
    const cf = request.cf || {};
    const c = String(cf.country || '').slice(0, 2).toUpperCase();
    const r = String(cf.regionCode || '').slice(0, 3).toUpperCase();
    if (!c) return response;
    const tag = `<script>window.LAZO_CF=${JSON.stringify({ c, r })};</script>`;
    return new HTMLRewriter()
      .on('head', { element(el) { el.prepend(tag, { html: true }); } })
      .transform(response);
  } catch (e) {
    return response;
  }
}
