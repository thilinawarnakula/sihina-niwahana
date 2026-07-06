// Firebase web config — paste yours between the braces below.
//
// Where to get it: console.firebase.google.com -> your project ->
// Project settings (gear icon) -> General -> Your apps -> Web app (</>) ->
// "SDK setup and configuration" -> Config.
//
// Note: this config is PUBLIC by design (it identifies the project, it is
// not a secret) — committing it is fine. Access control comes from Firebase
// Authentication itself plus the optional ALLOWED_EMAILS env var.
//
// While this is null, the site falls back to APP_PASSWORD login (or open
// access if that env var is unset).

window.FIREBASE_CONFIG = null;

// Example of what it should look like:
// window.FIREBASE_CONFIG = {
//   apiKey: "AIzaSy....",
//   authDomain: "sihina-niwahana.firebaseapp.com",
//   projectId: "sihina-niwahana",
//   storageBucket: "sihina-niwahana.appspot.com",
//   messagingSenderId: "1234567890",
//   appId: "1:1234567890:web:abcdef123456"
// };
