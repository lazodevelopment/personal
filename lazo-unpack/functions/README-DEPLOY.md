# Lazo AI Claim Verification — Deploy

## One-time setup (PowerShell, from a new folder e.g. C:\Users\kurvh\lazo-functions)
1. npm install -g firebase-tools        (if not installed)
2. firebase login                        (use the account that owns lazo-513ec)
3. firebase init functions               (choose EXISTING project: lazo-513ec, JavaScript, no ESLint, skip npm install)
   - This creates a functions/ folder. REPLACE its package.json and index.js
     with the two files in this zip.
4. cd functions && npm install
5. Set the API key secret (get one at console.anthropic.com):
   firebase functions:secrets:set ANTHROPIC_API_KEY
   (paste the key when prompted)
6. Deploy:
   firebase deploy --only functions

## How it behaves
- New claimRequests doc -> function wakes -> loads vendor listing -> downloads
  the proof photo -> computes hard signals (email domain vs website, phone vs
  listing) -> asks Claude to evaluate the document image + facts.
- AUTO-APPROVE only when: Claude says APPROVE, confidence >= 85, AND at least
  one deterministic signal matched. Then it links vendors.claimedBy +
  users.vendorId in one batch — the vendor's app flips to the live dashboard
  within seconds.
- EVERYTHING ELSE -> status 'needs_review' with aiNotes explaining why.
  Your human queue: Firestore console -> claimRequests -> filter status ==
  'needs_review'. Approve manually with the usual two link fields.
- Disputes (already-claimed vendors) and pipeline errors ALWAYS escalate.
  The AI can never reject and can never approve on weak evidence.

## Cost
One Sonnet call per claim (~a cent). At 1,000 claims/month: pocket change
for instant vendor onboarding.
