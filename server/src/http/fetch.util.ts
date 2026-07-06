/* Polite HTTPS fetching for Node 16 (no global fetch): normal browser UA,
 * redirect following, and an in-memory 15-minute cache so repeated searches
 * never re-hit the property sites. */

import * as https from "https";
import { URL } from "url";

const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " +
  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36";

const CACHE_TTL_MS = 15 * 60 * 1000;
const cache = new Map<string, { body: string; at: number }>();

export class FetchError extends Error {
  constructor(public url: string, message: string, public status?: number) {
    super(`${url}: ${message}`);
  }
}

function get(url: string, redirects = 5): Promise<string> {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    if (u.protocol !== "https:")
      return reject(new FetchError(url, "https only"));
    const req = https.get(
      u,
      { headers: { "User-Agent": UA, Accept: "text/html,*/*" }, timeout: 25000 },
      (res) => {
        const status = res.statusCode || 0;
        if (status >= 300 && status < 400 && res.headers.location) {
          res.resume();
          if (redirects <= 0)
            return reject(new FetchError(url, "too many redirects"));
          return resolve(get(new URL(res.headers.location, u).toString(), redirects - 1));
        }
        if (status !== 200) {
          res.resume();
          return reject(new FetchError(url, `HTTP ${status}`, status));
        }
        const chunks: Buffer[] = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
      },
    );
    req.on("timeout", () => req.destroy(new Error("timeout")));
    req.on("error", (e) => reject(new FetchError(url, e.message)));
  });
}

/** Fetch with cache. Returns { body, cached } so callers can skip the
 *  politeness delay on cache hits. */
export async function fetchPage(url: string): Promise<{ body: string; cached: boolean }> {
  const hit = cache.get(url);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS)
    return { body: hit.body, cached: true };
  const body = await get(url);
  cache.set(url, { body, at: Date.now() });
  return { body, cached: false };
}
