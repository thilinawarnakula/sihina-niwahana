import { auth } from "./firebase";

export interface Listing {
  title: string; priceLKR: number | null; priceText: string;
  area: string; propertyType: string; source: string; url: string;
  bedrooms: number | null; perches?: number | null;
  contact?: string | null; alsoOn?: string[];
}
export interface SearchPayload {
  listings: Listing[];
  coverage: Record<string, { searched: string[]; count: number; errors: string[] }>;
  manualLinks: { label: string; url: string }[];
  profile: any;
}

async function authHeaders(): Promise<Record<string, string>> {
  const u = auth.currentUser;
  return u ? { Authorization: "Bearer " + (await u.getIdToken()) } : {};
}

async function call<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data?.message || data?.error || res.statusText);
  return data as T;
}

/** Backend detection: the NestJS API answers /api/config; on static hosting
 *  (Netlify) it 404s and the search runs in the browser instead. */
export const getConfig = async () => {
  try {
    return await call<{ loginMode: string; emailConfigured: boolean }>("/api/config");
  } catch {
    return null;
  }
};
export const runSearch = (profile: unknown) =>
  call<SearchPayload>("/api/search", profile);
/** Static-mode page fetch through the Netlify proxy function */
export const fetchPageViaProxy = async (url: string): Promise<string> => {
  const res = await fetch("/api/page?url=" + encodeURIComponent(url),
    { headers: await authHeaders() });
  if (!res.ok) {
    let msg = "HTTP " + res.status;
    try { msg = (await res.json()).error || msg; } catch {}
    throw new Error(msg);
  }
  return res.text();
};
export const sendMail = (payload: { to: string; subject: string; text: string; html: string }) =>
  call<{ ok: boolean; sent: string }>("/api/mail", payload);

export const fmtLKR = (n: number | null | undefined) =>
  n == null ? "—" :
  n >= 1e6 ? "Rs " + (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + "M" :
  "Rs " + n.toLocaleString();
