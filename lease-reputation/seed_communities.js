// seed_communities.js — LeaseReputation community seeder (firebase-admin v13)
//
// Usage:
//   node seed_communities.js "apartment communities in Scottsdale AZ" [more queries...]

const { initializeApp, cert } = require('firebase-admin/app');
const { getFirestore, FieldValue, GeoPoint } = require('firebase-admin/firestore');
const serviceAccount = require('./serviceAccountKey.json');

const _fs = require('fs'), _path = require('path');
function _env(name) {
  let v = process.env[name];
  if (!v) { const p = _path.join(__dirname, '.env');
    if (_fs.existsSync(p)) for (const line of _fs.readFileSync(p, 'utf8').split(String.fromCharCode(10)))
      if (line.trim().startsWith(name + '=')) v = line.slice(name.length + 1).trim(); }
  if (!v) { console.error(name + ' is not set (put it in .env next to this script)'); process.exit(1); }
  return v;
}
const PLACES_KEY = _env('PLACES_KEY_JS');
initializeApp({ credential: cert(serviceAccount) });
const db = getFirestore();

async function searchPage(query, pageToken) {
  const res = await fetch('https://places.googleapis.com/v1/places:searchText', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Goog-Api-Key': PLACES_KEY,
      'X-Goog-FieldMask':
        'places.id,places.displayName,places.formattedAddress,places.location,places.photos,nextPageToken',
    },
    body: JSON.stringify({
      textQuery: query,
      pageSize: 20,
      ...(pageToken ? { pageToken } : {}),
    }),
  });
  if (!res.ok) {
    throw new Error(`Places API ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

async function seed(query) {
  let pageToken;
  let found = 0;
  let added = 0;
  let skipped = 0;
  do {
    const data = await searchPage(query, pageToken);
    const places = data.places ?? [];
    for (const p of places) {
      found++;
      const docRef = db.collection('communities').doc(p.id);
      const snap = await docRef.get();
      if (snap.exists) {
        skipped++;
        continue; // already in the directory — never overwrite (protects scores)
      }
      const name = (p.displayName && p.displayName.text) || 'Unnamed community';
      await docRef.set({
        name,
        nameLower: name.toLowerCase(), // REQUIRED: app directory orders by this
        address: p.formattedAddress || '',
        placeId: p.id,
        location: p.location
          ? new GeoPoint(p.location.latitude, p.location.longitude)
          : null,
        photoRef: (p.photos && p.photos[0] && p.photos[0].name) || '',
        reviewCount: 0,
        createdAt: FieldValue.serverTimestamp(),
        source: 'places-seed',
      });
      added++;
      console.log(`  + ${name} — ${p.formattedAddress || 'no address'}`);
    }
    pageToken = data.nextPageToken;
    // Places requires a short pause before a nextPageToken becomes valid.
    if (pageToken) await new Promise((r) => setTimeout(r, 2000));
  } while (pageToken); // Text Search returns up to 60 results (3 pages)
  console.log(
    `\n"${query}": ${added} added, ${skipped} already existed, ${found} found total.\n`
  );
}

(async () => {
  const queries = process.argv.slice(2);
  if (queries.length === 0) {
    console.log(
      'Usage: node seed_communities.js "apartment communities in Scottsdale AZ" [more queries...]'
    );
    process.exit(1);
  }
  for (const q of queries) {
    console.log(`Searching: ${q}`);
    await seed(q);
  }
  process.exit(0);
})();