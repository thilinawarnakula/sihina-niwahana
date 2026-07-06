import { useEffect, useState } from "react";
import { User } from "firebase/auth";
import { logOut, watchUser } from "./firebase";
import { fetchPageViaProxy, getConfig, runSearch, SearchPayload } from "./api";
import { runSearchInBrowser } from "./engine";
import Login from "./components/Login";
import Chat from "./components/Chat";
import SearchForm, { emptyForm, FormState, toProfile } from "./components/SearchForm";
import Results, { Skeletons } from "./components/Results";

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ text: string; error?: boolean } | null>(null);
  const [data, setData] = useState<SearchPayload | null>(null);
  const [hasBackend, setHasBackend] = useState(true);

  useEffect(() => watchUser((u) => { setUser(u); setReady(true); }), []);
  useEffect(() => { getConfig().then((c) => setHasBackend(c !== null)); }, []);

  const search = async () => {
    if (!form.types.length || !form.areas.trim()) {
      setStatus({ text: "Pick at least one property type and one area.", error: true });
      return;
    }
    setBusy(true);
    setData(null);
    setStatus({ text: "Searching ikman.lk, LankaPropertyWeb, house.lk, LankaLand — " +
                      "sites are fetched in parallel, politely." });
    try {
      const profile = toProfile(form);
      if (hasBackend) {
        setData(await runSearch(profile));
      } else {
        // static hosting (Netlify): search runs in this browser via the
        // /api/page proxy function — same engine, same politeness
        setData(await runSearchInBrowser(profile as any, fetchPageViaProxy,
          (msg) => setStatus({ text: msg })) as SearchPayload);
      }
      setStatus(null);
    } catch (e: any) {
      setStatus({ text: "Search failed: " + e.message, error: true });
    } finally { setBusy(false); }
  };

  if (!ready) return null;
  if (!user) return <Login />;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 flex items-center gap-2 border-b
                         border-line bg-white px-5 py-2.5">
        <svg viewBox="0 0 64 64" className="h-8 w-8">
          <circle cx="32" cy="32" r="32" fill="#E4002B" />
          <path d="M32 14 L52 32 H46 V48 H36 V38 H28 V48 H18 V32 H12 Z" fill="#fff" />
        </svg>
        <span className="text-lg font-extrabold tracking-tight text-ink">Sihina Niwahana</span>
        <span className="text-xs text-mut">සිහින නිවහන</span>
        <span className="flex-1" />
        <span className="flex items-center gap-2 rounded-full border border-line
                         px-3 py-1 text-xs">
          👤 {user.email}
          <button className="text-link hover:underline" onClick={() => logOut()}>
            log out
          </button>
        </span>
      </header>

      <div className="border-b border-line bg-white px-4 pb-16 pt-9 text-center">
        <h1 className="text-3xl font-extrabold tracking-tighter text-ink">
          Find your <em className="not-italic text-brand">dream home</em> in Sri Lanka
        </h1>
        <p className="mx-auto mt-2 max-w-xl text-sm text-mut">
          Searches ikman.lk, LankaPropertyWeb, house.lk &amp; LankaLand in one go —
          de-duplicated, ranked for you, nothing stored.
        </p>
      </div>

      <main className="mx-auto -mt-10 max-w-4xl px-4 pb-20">
        <Chat form={form} setForm={setForm} onSearch={search} />
        <SearchForm form={form} setForm={setForm} onSearch={search}
                    busy={busy} status={status} />
        {busy && <Skeletons />}
        {data && <Results data={data} />}
      </main>
    </div>
  );
}
