import { useState } from "react";
import {
  emailSignIn, emailSignUp, friendly, googleSignIn, resetPassword,
} from "../firebase";

const GoogleLogo = () => (
  <svg viewBox="0 0 48 48" className="h-5 w-5">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
  </svg>
);

const Spinner = () => (
  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white align-[-2px]" />
);

const input =
  "w-full rounded-lg border border-line bg-white px-3 py-2.5 text-body " +
  "placeholder:text-mut/70 focus:border-ink focus:outline-none " +
  "focus:ring-2 focus:ring-ink/10";
const primary =
  "w-full rounded-lg bg-brand px-6 py-2.5 font-bold text-white " +
  "transition hover:bg-brand-dark disabled:opacity-60";

export default function Login() {
  const [view, setView] = useState<"signin" | "signup">("signin");
  const [msg, setMsg] = useState("");
  const [ok, setOk] = useState(false);
  const [busy, setBusy] = useState("");
  const [f, setF] = useState({ email: "", pass: "", name: "", spass: "", spass2: "" });
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });

  const run = (key: string, fn: () => Promise<unknown>) => async () => {
    setMsg(""); setOk(false); setBusy(key);
    try { await fn(); }
    catch (e) { setMsg(friendly(e)); }
    finally { setBusy(""); }
  };

  const signIn = run("signin", () => emailSignIn(f.email.trim(), f.pass));
  const google = run("google", googleSignIn);
  const signUp = run("signup", async () => {
    if (!f.email.trim()) throw { message: "Enter your email." };
    if (f.spass.length < 6) throw { code: "auth/weak-password" };
    if (f.spass !== f.spass2) throw { message: "Passwords don't match." };
    await emailSignUp(f.email.trim(), f.spass, f.name.trim() || undefined);
  });
  const reset = run("reset", async () => {
    if (!f.email.trim()) throw { message: "Type your email above first." };
    await resetPassword(f.email.trim());
    setOk(true); setMsg("Password-reset email sent to " + f.email.trim() + " ✓");
  });

  const googleBtn = (label: string) => (
    <button
      onClick={google} disabled={busy !== ""}
      className="flex w-full items-center justify-center gap-3 rounded-lg border
                 border-line bg-white px-4 py-2.5 font-semibold text-ink
                 transition hover:border-ink hover:shadow-card disabled:opacity-60">
      {busy === "google" ? <Spinner /> : <GoogleLogo />} {label}
    </button>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-page p-4">
      <div className="absolute inset-x-0 top-0 h-[38vh] bg-brand" />
      <div className="relative w-full max-w-sm rounded-2xl border border-line
                      bg-white p-9 text-center shadow-lift">
        <svg viewBox="0 0 64 64" className="mx-auto mb-4 h-16 w-16">
          <circle cx="32" cy="32" r="32" fill="#E4002B" />
          <path d="M32 14 L52 32 H46 V48 H36 V38 H28 V48 H18 V32 H12 Z" fill="#fff" />
        </svg>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink">Sihina Niwahana</h1>
        <p className="mb-6 mt-1 text-sm text-mut">Your dream home in Sri Lanka,<br />one search away.</p>

        {view === "signin" ? (
          <div className="space-y-3">
            <input className={input} type="email" placeholder="Email"
                   value={f.email} onChange={set("email")} />
            <input className={input} type="password" placeholder="Password"
                   value={f.pass} onChange={set("pass")}
                   onKeyDown={(e) => e.key === "Enter" && signIn()} />
            <button className={primary} onClick={signIn} disabled={busy !== ""}>
              {busy === "signin" ? <Spinner /> : "Sign in"}
            </button>
            <div className="text-sm text-mut">
              New here?{" "}
              <button className="font-semibold text-link hover:underline"
                      onClick={() => { setMsg(""); setView("signup"); }}>
                Create an account
              </button>{" · "}
              <button className="font-semibold text-link hover:underline"
                      onClick={reset} disabled={busy !== ""}>
                Forgot password?
              </button>
            </div>
            <div className="flex items-center gap-3 text-xs text-mut">
              <span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" />
            </div>
            {googleBtn("Sign in with Google")}
          </div>
        ) : (
          <div className="space-y-3">
            <h2 className="text-left text-base font-bold text-ink">Create your account</h2>
            <input className={input} type="text" placeholder="Full name (optional)"
                   value={f.name} onChange={set("name")} />
            <input className={input} type="email" placeholder="Email"
                   value={f.email} onChange={set("email")} />
            <input className={input} type="password" placeholder="Password (min 6 characters)"
                   value={f.spass} onChange={set("spass")} />
            <input className={input} type="password" placeholder="Confirm password"
                   value={f.spass2} onChange={set("spass2")}
                   onKeyDown={(e) => e.key === "Enter" && signUp()} />
            <button className={primary} onClick={signUp} disabled={busy !== ""}>
              {busy === "signup" ? <Spinner /> : "Create account"}
            </button>
            <div className="text-sm text-mut">
              Already have an account?{" "}
              <button className="font-semibold text-link hover:underline"
                      onClick={() => { setMsg(""); setView("signin"); }}>
                Sign in
              </button>
            </div>
            <div className="flex items-center gap-3 text-xs text-mut">
              <span className="h-px flex-1 bg-line" />or<span className="h-px flex-1 bg-line" />
            </div>
            {googleBtn("Continue with Google")}
          </div>
        )}

        {msg && (
          <div className={`mt-4 text-sm font-semibold ${ok ? "text-green-700" : "text-brand"}`}>
            {msg}
          </div>
        )}
        <div className="mt-6 text-xs text-mut">
          🔒 Private search · nothing is stored · Sri Lanka only
        </div>
      </div>
    </div>
  );
}
