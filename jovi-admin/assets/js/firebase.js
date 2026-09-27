// Firebase bootstrap for the Jovi staff app (project kurv-health).
// Same Firestore the member app writes to; the EHR must keep the app's field names.
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import { getAuth, setPersistence, browserLocalPersistence } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';
import { getFirestore, serverTimestamp, Timestamp, FieldValue, deleteField, arrayUnion, arrayRemove, increment } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js';
import { getStorage } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-storage.js';
import { getFunctions } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-functions.js';

export const firebaseConfig = {
  apiKey: 'AIzaSyDCMwzNdUGWSXucLubmTaBWeCOjpbeONw0',
  authDomain: 'kurv-health.firebaseapp.com',
  projectId: 'kurv-health',
  storageBucket: 'kurv-health.firebasestorage.app',
  messagingSenderId: '818875245808',
  appId: '1:818875245808:web:fa1f6eada68674b5b94e35',
  measurementId: 'G-BCV8L19CRZ',
};

export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
setPersistence(auth, browserLocalPersistence).catch(() => {});
export const db = getFirestore(app);
export const storage = getStorage(app);
export const functions = getFunctions(app, 'us-central1');
export { serverTimestamp, Timestamp, FieldValue, deleteField, arrayUnion, arrayRemove, increment };

// Re-export the Firestore query API so pages import from one place.
export {
  collection, collectionGroup, doc, getDoc, getDocs, setDoc, addDoc, updateDoc, deleteDoc,
  query, where, orderBy, limit, limitToLast, startAfter, endBefore, onSnapshot, writeBatch, runTransaction,
  documentId,
} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js';
export { ref as storageRef, uploadBytes, getDownloadURL, listAll, deleteObject } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-storage.js';
export { httpsCallable } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-functions.js';
export {
  signInWithEmailAndPassword, signOut, onAuthStateChanged, sendPasswordResetEmail,
  createUserWithEmailAndPassword, updateProfile,
} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';
