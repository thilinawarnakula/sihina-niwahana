/* Guided intake chat — a scripted state machine (no AI). Every answer
 * updates the shared form state, so the form below always mirrors the chat. */
import { useEffect, useRef, useState } from "react";
import { FormState } from "./SearchForm";

interface Msg { who: "bot" | "me"; text: string }
type Step = "type" | "purpose" | "areas" | "budget" | "perches" | "beds"
  | "must" | "avoid" | "done";

const parseLKR = (s: string): number | null => {
  const m = s.replace(/,/g, "").match(/([\d.]+)\s*(m|million|k|lakh|lakhs)?/i);
  if (!m) return null;
  let v = parseFloat(m[1]);
  const u = (m[2] || "").toLowerCase();
  if (u === "m" || u === "million") v *= 1e6;
  else if (u === "k") v *= 1e3;
  else if (u.startsWith("lakh")) v *= 1e5;
  return Math.round(v);
};
const skipped = (s: string) => /^(skip|no|none|nope|any|-|n\/a)$/i.test(s.trim());

export default function Chat({ form, setForm, onSearch }: {
  form: FormState;
  setForm: (f: FormState) => void;
  onSearch: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [quick, setQuick] = useState<string[]>([]);
  const [step, setStep] = useState<Step | null>(null);
  const [input, setInput] = useState("");
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight);
  }, [msgs]);

  const bot = (text: string, quicks: string[] = []) => {
    setMsgs((m) => [...m, { who: "bot", text }]);
    setQuick(quicks);
  };

  const start = () => {
    setOpen(true);
    if (step === null) {
      setStep("type");
      bot("Hi! I'll help you set up your search — a few quick questions, " +
          'one at a time. You can type "skip" for any optional one.\n\n' +
          "First: are you looking for land, a house, or an apartment? (one or more)",
          ["Land", "House", "Apartment", "House and apartment"]);
    }
  };

  const answer = (text: string) => {
    setMsgs((m) => [...m, { who: "me", text }]);
    setQuick([]);
    const low = text.toLowerCase();
    const f = { ...form };

    if (step === "type") {
      const types = ["land", "house", "apartment"].filter((t) => low.includes(t));
      if (!types.length) return bot("Please say land, house, or apartment (or a mix).");
      f.types = types; setForm(f); setStep("purpose");
      bot(`Got it: ${types.join(" + ")}. Are you buying or renting?`, ["Buy", "Rent"]);
    } else if (step === "purpose") {
      const p = /rent/.test(low) ? "rent" : /buy|purchase|sale/.test(low) ? "buy" : null;
      if (!p) return bot("Buy or rent?", ["Buy", "Rent"]);
      f.purpose = p; setForm(f); setStep("areas");
      bot("Which area(s)? District, city or town — e.g. Nugegoda, Maharagama, " +
          "Colombo 5, Kandy. Separate multiple areas with commas.");
    } else if (step === "areas") {
      const areas = text.split(/,| and /i).map((s) => s.trim()).filter(Boolean);
      if (!areas.length) return bot("Name at least one area.");
      f.areas = areas.join(", "); setForm(f); setStep("budget");
      bot('What\'s your budget in LKR? Give a range like "20m - 30m", ' +
          'a max like "under 45m", or "skip".', ["Skip"]);
    } else if (step === "budget") {
      if (!skipped(text)) {
        const nums = text.replace(/,/g, "").match(/[\d.]+\s*(?:m|million|k|lakhs?)?/gi) || [];
        if (/under|max|below|up to/.test(low) && nums.length >= 1)
          f.bmax = String(parseLKR(nums[0]) ?? "");
        else if (nums.length >= 2) {
          f.bmin = String(parseLKR(nums[0]) ?? "");
          f.bmax = String(parseLKR(nums[1]) ?? "");
        } else if (nums.length === 1) f.bmax = String(parseLKR(nums[0]) ?? "");
        setForm(f);
      }
      if (f.types.includes("land")) {
        setStep("perches");
        bot('Minimum land size in perches? (or "skip")', ["8", "10", "15", "Skip"]);
      } else nextAfterSize(f);
    } else if (step === "perches") {
      if (!skipped(text)) { const n = parseFloat(low); if (n) f.perches = String(n); setForm(f); }
      nextAfterSize(f);
    } else if (step === "beds") {
      if (!skipped(text)) { const n = parseInt(low); if (n) f.beds = String(n); setForm(f); }
      setStep("must");
      bot("Any must-haves? e.g. parking, garden, near main road, clear deed. " +
          'Comma-separated, or "skip".', ["Skip"]);
    } else if (step === "must") {
      if (!skipped(text)) { f.must = text; setForm(f); }
      setStep("avoid");
      bot('Anything to avoid — deal-breakers? (or "skip")', ["Skip"]);
    } else if (step === "avoid") {
      if (!skipped(text)) { f.avoid = text; setForm(f); }
      setStep("done");
      bot("All set! Your preferences are filled in the form below — review or " +
          "tweak anything, then hit Search. Want me to run it now?",
          ["Search now", "I'll review first"]);
    } else if (step === "done") {
      if (/search|yes|run|go/.test(low)) {
        onSearch();
        bot("Searching — results will appear below…");
      } else bot("No problem — the form below has everything. Hit Search whenever you're ready.");
    }

    function nextAfterSize(cur: FormState) {
      if (cur.types.some((t) => t === "house" || t === "apartment")) {
        setStep("beds");
        bot('Minimum bedrooms? (or "skip")', ["2", "3", "4", "Skip"]);
      } else {
        setStep("must");
        bot("Any must-haves? e.g. parking, garden, near main road, clear deed. " +
            'Comma-separated, or "skip".', ["Skip"]);
      }
    }
  };

  const send = () => {
    const v = input.trim();
    if (!v) return;
    setInput("");
    answer(v);
  };

  return (
    <div className="mb-4 rounded-card border border-line bg-white p-6 shadow-card">
      <h2 className="mb-2 text-base font-bold text-ink">💬 Guided setup</h2>
      <p className="text-sm text-mut">
        Not sure where to start?{" "}
        <button className="font-semibold text-link hover:underline"
                onClick={() => (open ? setOpen(false) : start())}>
          {open ? "hide chat" : "Chat with me"}
        </button>{" "}
        — I'll ask a few quick questions and fill the form for you. Or just use the form below.
      </p>
      {open && (
        <div className="mt-3">
          <div ref={logRef} className="max-h-80 space-y-2 overflow-y-auto py-1">
            {msgs.map((m, i) => (
              <div key={i}
                className={`max-w-[82%] whitespace-pre-line rounded-2xl px-4 py-2 text-sm ${
                  m.who === "bot"
                    ? "rounded-bl border border-line bg-page text-body"
                    : "ml-auto rounded-br bg-brand text-white"}`}>
                {m.text}
              </div>
            ))}
          </div>
          {quick.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {quick.map((q) => (
                <button key={q} onClick={() => answer(q)}
                  className="rounded-full border border-line bg-white px-3 py-1 text-sm
                             hover:border-ink">
                  {q}
                </button>
              ))}
            </div>
          )}
          <div className="mt-3 flex gap-2">
            <input
              className="flex-1 rounded-lg border border-line px-3 py-2 text-sm
                         focus:border-ink focus:outline-none focus:ring-2 focus:ring-ink/10"
              placeholder="Type your answer…" value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()} />
            <button onClick={send}
              className="rounded-lg bg-brand px-5 py-2 font-bold text-white hover:bg-brand-dark">
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
