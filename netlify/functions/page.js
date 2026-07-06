// Page-fetch proxy for the browser search engine.
//
// The property sites don't send CORS headers, so the browser can't fetch
// them directly; this function fetches on its behalf. It is NOT an open
// proxy: only the four whitelisted property sites can be fetched, and if
// Firebase auth is configured (FIREBASE_API_KEY env var set), a valid
// signed-in user is required.
//
// Env vars (set in Netlify site settings, never in code):
//   FIREBASE_API_KEY  enable auth checks (same key as web/firebase-config.js)
//   ALLOWED_EMAILS    optional comma-separated allowlist of Google accounts

const ALLOWED_HOSTS = new Set([
  "ikman.lk",
  "www.lankapropertyweb.com",
  "house.lk",
  "www.lankaland.lk",
]);

const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " +
  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36";

async function requireUser(event) {
  const apiKey = process.env.FIREBASE_API_KEY;
  if (!apiKey) return null; // auth not configured -> open
  const auth = event.headers.authorization || "";
  const idToken = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!idToken) throw new Error("Sign in first");
  const resp = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${apiKey}`,
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idToken }) });
  if (!resp.ok) throw new Error("Sign-in token rejected");
  const data = await resp.json();
  const email = (((data.users || [])[0] || {}).email || "").toLowerCase();
  if (!email) throw new Error("Sign-in token rejected");
  const allowed = (process.env.ALLOWED_EMAILS || "")
    .split(",").map((e) => e.trim().toLowerCase()).filter(Boolean);
  if (allowed.length && !allowed.includes(email))
    throw new Error(`${email} is not allowed to use this app`);
  return email;
}

exports.handler = async (event) => {
  const json = (code, obj) => ({
    statusCode: code,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(obj),
  });

  try {
    await requireUser(event);
  } catch (e) {
    return json(401, { error: e.message });
  }

  const target = (event.queryStringParameters || {}).url || "";
  let u;
  try { u = new URL(target); } catch { return json(400, { error: "bad url" }); }
  if (u.protocol !== "https:" || !ALLOWED_HOSTS.has(u.hostname))
    return json(403, { error: "host not allowed" });

  try {
    const resp = await fetch(u, { headers: { "User-Agent": UA }, redirect: "follow" });
    if (!resp.ok) return json(resp.status, { error: `HTTP ${resp.status}` });
    const body = await resp.text();
    return {
      statusCode: 200,
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        // let Netlify's CDN cache pages briefly so repeat searches
        // don't re-hit the property sites
        "Cache-Control": "public, max-age=900",
      },
      body,
    };
  } catch (e) {
    return json(502, { error: `fetch failed: ${e.message}` });
  }
};
