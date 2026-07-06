import { useState } from "react";
import { fmtLKR, sendMail, SearchPayload } from "../api";

const SOURCE_NAMES: Record<string, string> = {
  ikman: "ikman.lk", lpw: "LankaPropertyWeb",
  houselk: "house.lk", lankaland: "LankaLand.lk",
};
const name = (s: string) => SOURCE_NAMES[s] || s;

function emailBody(d: SearchPayload) {
  const p = d.profile || {}, ls = d.listings || [];
  const subject = `Property search: ${ls.length} matches — ` +
    `${(p.propertyTypes || []).join("/")} in ${(p.areas || []).join(", ")}`;
  const text = ls.slice(0, 10).map((l, i) =>
    `${i + 1}. ${l.title}\n   ${l.priceText || "price not stated"} | ${l.area}\n   ${l.url}`,
  ).join("\n\n");
  const esc = (s: string) => s.replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
  const html = `<h2>${esc(subject)}</h2>` + ls.slice(0, 25).map((l, i) =>
    `<p><b>${i + 1}. <a href="${esc(l.url)}">${esc(l.title)}</a></b><br>` +
    `${esc(l.priceText || "price not stated")} · ${esc(l.area)} · ${esc(l.propertyType)}` +
    ` <small>[${esc(name(l.source))}]</small></p>`).join("") +
    `<p><small>Sihina Niwahana — prices in LKR as displayed by each source site.</small></p>`;
  return { subject, text, html };
}

export function Skeletons() {
  return (
    <div className="mt-4 space-y-3">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="h-[74px] animate-pulse rounded-card bg-line/60" />
      ))}
    </div>
  );
}

export default function Results({ data }: { data: SearchPayload }) {
  const [to, setTo] = useState("");
  const [mailMsg, setMailMsg] = useState<{ text: string; error?: boolean } | null>(null);
  const [sending, setSending] = useState(false);

  const ls = data.listings || [];
  const priced = ls.filter((l) => l.priceLKR != null).map((l) => l.priceLKR!) ;
  const median = priced.length
    ? [...priced].sort((a, b) => a - b)[Math.floor(priced.length / 2)] : null;
  const dups = ls.reduce((s, l) => s + (l.alsoOn?.length || 0), 0);

  const mail = async () => {
    setSending(true); setMailMsg(null);
    try {
      const r = await sendMail({ to: to.trim(), ...emailBody(data) });
      setMailMsg({ text: `Sent to ${r.sent} ✓` });
    } catch (e: any) {
      setMailMsg({ text: e.message, error: true });
    } finally { setSending(false); }
  };

  const card = "rounded-card border border-line bg-white p-6 shadow-card";

  return (
    <div className="mt-4 space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          [String(ls.length), "matching listings"],
          [priced.length ? fmtLKR(Math.min(...priced)) : "—", "lowest price"],
          [fmtLKR(median), "median price"],
          [String(dups), "duplicates merged"],
        ].map(([b, s]) => (
          <div key={s} className="rounded-card border border-line bg-white px-4 py-3 shadow-card">
            <div className="text-2xl font-extrabold tracking-tight text-ink">{b}</div>
            <div className="text-xs text-mut">{s}</div>
          </div>
        ))}
      </div>

      <div className={card}>
        <h2 className="mb-3 text-base font-bold text-ink">Shortlist</h2>
        {ls.length === 0 && <p>No matching listings found.</p>}
        <div className="space-y-3">
          {ls.map((l, i) => (
            <div key={l.url}
              className="rounded-card border border-line bg-white p-4 transition
                         hover:border-mut hover:shadow-lift">
              <a href={l.url} target="_blank" rel="noopener noreferrer"
                 className="font-bold tracking-tight text-ink hover:text-brand hover:underline">
                {i + 1}. {l.title}
              </a>
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-mut">
                <span className="font-extrabold text-ink">
                  {l.priceText || fmtLKR(l.priceLKR)}
                </span>
                <span>
                  · {l.area} · {l.propertyType}
                  {l.bedrooms ? ` · ${l.bedrooms} bed` : ""}
                  {l.perches ? ` · ${l.perches} perches` : ""}
                  {l.contact ? ` · seller: ${l.contact}` : ""}
                </span>
                <span className="rounded border border-line bg-page px-1.5 text-xs font-semibold">
                  {name(l.source)}
                </span>
                {(l.alsoOn?.length || 0) > 0 && (
                  <span className="rounded bg-brand-tint px-1.5 text-xs font-semibold text-brand">
                    also on: {l.alsoOn!.map(name).join(", ")}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className={card}>
        <h2 className="mb-3 text-base font-bold text-ink">Email this summary</h2>
        <div className="flex flex-wrap gap-3">
          <input
            className="min-w-[220px] flex-1 rounded-lg border border-line px-3 py-2.5
                       focus:border-ink focus:outline-none focus:ring-2 focus:ring-ink/10"
            type="email" placeholder="you@example.com"
            value={to} onChange={(e) => setTo(e.target.value)} />
          <button onClick={mail} disabled={sending}
            className="rounded-lg bg-brand px-6 py-2.5 font-bold text-white
                       hover:bg-brand-dark disabled:opacity-60">
            {sending ? "Sending…" : "Send email"}
          </button>
        </div>
        {mailMsg && (
          <div className={`mt-2 text-sm ${mailMsg.error ? "font-semibold text-brand" : "text-mut"}`}>
            {mailMsg.text}
          </div>
        )}
      </div>

      <div className={card}>
        <details>
          <summary className="cursor-pointer font-bold text-ink">
            Coverage — what was searched (and what wasn't)
          </summary>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {Object.entries(data.coverage || {}).map(([src, info]) => (
              <>
                {info.searched.length > 0 && (
                  <li key={src}>
                    <b>{src}</b>: searched {info.searched.length} page(s), {info.count} listing(s)
                  </li>
                )}
                {info.errors.map((e) => (
                  <li key={e} className="text-yellow-700">{e}</li>
                ))}
              </>
            ))}
          </ul>
        </details>
      </div>

      {(data.manualLinks?.length || 0) > 0 && (
        <div className={card}>
          <details>
            <summary className="cursor-pointer font-bold text-ink">
              Browse yourself — sites we can't search automatically
            </summary>
            <ul className="mt-2 list-disc pl-5 text-sm">
              {data.manualLinks.map((m) => (
                <li key={m.url}>
                  <a className="text-link hover:underline" href={m.url}
                     target="_blank" rel="noopener noreferrer">{m.label}</a>
                </li>
              ))}
            </ul>
          </details>
        </div>
      )}
    </div>
  );
}
