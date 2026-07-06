export interface FormState {
  types: string[];
  purpose: "buy" | "rent";
  areas: string;
  bmin: string; bmax: string;
  beds: string; perches: string;
  must: string; avoid: string;
}

export const emptyForm: FormState = {
  types: [], purpose: "buy", areas: "",
  bmin: "", bmax: "", beds: "", perches: "", must: "", avoid: "",
};

export function toProfile(f: FormState) {
  const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
  const num = (s: string) => {
    const n = parseFloat(s);
    return Number.isFinite(n) ? Math.round(n) : null;
  };
  return {
    propertyTypes: f.types,
    purpose: f.purpose,
    areas: csv(f.areas),
    budgetLKR: { min: num(f.bmin), max: num(f.bmax) },
    size: { bedrooms: num(f.beds), perches: num(f.perches) },
    mustHaves: csv(f.must),
    dealBreakers: csv(f.avoid),
  };
}

const label = "mb-1 mt-4 block text-xs font-semibold text-ink first:mt-0";
const hint = "font-normal text-mut";
const input =
  "w-full rounded-lg border border-line bg-white px-3 py-2.5 " +
  "placeholder:text-mut/70 focus:border-ink focus:outline-none focus:ring-2 focus:ring-ink/10";

export default function SearchForm({ form, setForm, onSearch, busy, status }: {
  form: FormState;
  setForm: (f: FormState) => void;
  onSearch: () => void;
  busy: boolean;
  status: { text: string; error?: boolean } | null;
}) {
  const set = (k: keyof FormState) => (e: any) =>
    setForm({ ...form, [k]: e.target.value });
  const toggleType = (t: string) =>
    setForm({
      ...form,
      types: form.types.includes(t)
        ? form.types.filter((x) => x !== t) : [...form.types, t],
    });

  return (
    <div className="rounded-card border border-line bg-white p-6 shadow-card">
      {/* Buy/Rent — REA underline tabs */}
      <label className={label}>Purpose</label>
      <div className="inline-flex border-b-2 border-line">
        {(["buy", "rent"] as const).map((p) => (
          <button key={p}
            onClick={() => setForm({ ...form, purpose: p })}
            className={`-mb-0.5 border-b-[3px] px-5 py-2 font-semibold capitalize ${
              form.purpose === p
                ? "border-brand text-ink"
                : "border-transparent text-mut hover:text-ink"}`}>
            {p}
          </button>
        ))}
      </div>

      <label className={label}>Property type</label>
      <div className="flex flex-wrap gap-2">
        {["house", "apartment", "land"].map((t) => (
          <button key={t} onClick={() => toggleType(t)}
            className={`rounded-full border px-4 py-2 text-sm font-medium capitalize transition ${
              form.types.includes(t)
                ? "border-brand bg-brand-tint font-semibold text-brand"
                : "border-line bg-white text-body hover:border-ink"}`}>
            {form.types.includes(t) ? "✓ " : ""}{t}
          </button>
        ))}
      </div>

      <label className={label}>
        Areas <span className={hint}>(comma-separated — e.g. Nugegoda, Maharagama, Colombo 5)</span>
      </label>
      <input className={input} placeholder="Nugegoda, Maharagama"
             value={form.areas} onChange={set("areas")} />

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className={label}>Budget min (LKR)</label>
          <input className={input} type="number" placeholder="20000000"
                 value={form.bmin} onChange={set("bmin")} />
        </div>
        <div>
          <label className={label}>Budget max (LKR)</label>
          <input className={input} type="number" placeholder="45000000"
                 value={form.bmax} onChange={set("bmax")} />
        </div>
        <div>
          <label className={label}>
            Min bedrooms <span className={hint}>(house/apartment)</span>
          </label>
          <input className={input} type="number" placeholder="3"
                 value={form.beds} onChange={set("beds")} />
        </div>
        <div>
          <label className={label}>
            Min perches <span className={hint}>(land)</span>
          </label>
          <input className={input} type="number" placeholder="8"
                 value={form.perches} onChange={set("perches")} />
        </div>
        <div>
          <label className={label}>Must-haves</label>
          <input className={input} placeholder="parking, near main road"
                 value={form.must} onChange={set("must")} />
        </div>
        <div>
          <label className={label}>Exclude</label>
          <input className={input} placeholder="ground floor"
                 value={form.avoid} onChange={set("avoid")} />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-4">
        <button onClick={onSearch} disabled={busy}
          className="rounded-lg bg-brand px-10 py-3 text-base font-bold text-white
                     transition hover:bg-brand-dark disabled:opacity-60">
          {busy ? (
            <span className="inline-block h-4 w-4 animate-spin rounded-full
                             border-2 border-white/40 border-t-white align-[-2px]" />
          ) : "Search"}
        </button>
        {status && (
          <div className={`text-sm ${status.error ? "font-semibold text-brand" : "text-mut"}`}>
            {busy && !status.error && (
              <span className="mr-2 inline-block h-3 w-3 animate-spin rounded-full
                               border-2 border-line border-t-brand align-[-1px]" />
            )}
            {status.text}
          </div>
        )}
      </div>
    </div>
  );
}
