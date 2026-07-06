// Firebase web config — public by design (identifies the project only).
// Access control = Firebase Authentication + server-side ALLOWED_EMAILS.
import { initializeApp } from "firebase/app";
import {
  getAuth, GoogleAuthProvider, signInWithPopup,
  signInWithEmailAndPassword, createUserWithEmailAndPassword,
  sendPasswordResetEmail, updateProfile, signOut, onAuthStateChanged,
  User,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: "AIzaSyCu_U6fkyGHsgB2oSCkZpIUKkGvr1jyJWQ",
  authDomain: "sihina-niwahana-web.firebaseapp.com",
  projectId: "sihina-niwahana-web",
  storageBucket: "sihina-niwahana-web.firebasestorage.app",
  messagingSenderId: "923740314398",
  appId: "1:923740314398:web:45b72fe3c112f5ac5e470f",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

export const watchUser = (cb: (u: User | null) => void) =>
  onAuthStateChanged(auth, cb);

export const googleSignIn = () =>
  signInWithPopup(auth, new GoogleAuthProvider());
export const emailSignIn = (email: string, pass: string) =>
  signInWithEmailAndPassword(auth, email, pass);
export const emailSignUp = async (email: string, pass: string, name?: string) => {
  const cred = await createUserWithEmailAndPassword(auth, email, pass);
  if (name) await updateProfile(cred.user, { displayName: name });
  return cred;
};
export const resetPassword = (email: string) =>
  sendPasswordResetEmail(auth, email);
export const logOut = () => signOut(auth);

/** Human messages for Firebase error codes */
export function friendly(e: any): string {
  const map: Record<string, string> = {
    "auth/invalid-credential": "Wrong email or password.",
    "auth/wrong-password": "Wrong email or password.",
    "auth/user-not-found": 'No account with that email — use "Create an account".',
    "auth/invalid-email": "That doesn't look like an email address.",
    "auth/missing-password": "Enter your password.",
    "auth/weak-password": "Password must be at least 6 characters.",
    "auth/email-already-in-use": "That email already has an account — just sign in.",
    "auth/too-many-requests": "Too many attempts — wait a bit and try again.",
    "auth/popup-closed-by-user": "Sign-in popup was closed.",
    "auth/operation-not-allowed":
      "This sign-in method isn't enabled in Firebase console (Authentication → Sign-in method).",
  };
  return map[e?.code] || e?.message || String(e);
}
