Firestore + Storage security rules for the Elizabeth Scott Firebase project (elizabeth-scott-738e5).
Kept outside es-admin because everything in that folder is published to admin.elizabethscottweddings.com.

Deploy (PowerShell):
    firebase login --reauth
    cd C:\Users\kurvh\es-firebase
    firebase deploy --only firestore:rules,storage
