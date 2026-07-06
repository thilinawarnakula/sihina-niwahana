// Email the search summary. Same auth rules as page.js.
//
// Env vars (Netlify site settings -> Environment variables):
//   SMTP_USER / SMTP_PASS   sender account (Gmail: use an App Password)
//   SMTP_HOST / SMTP_PORT   optional, default smtp.gmail.com:587
//   FIREBASE_API_KEY        enable auth checks
//   ALLOWED_EMAILS          optional allowlist; when set, mail can only be
//                           SENT TO these addresses too (anti-spam)

const nodemailer = require("nodemailer");

async function requireUser(event) {
  const apiKey = process.env.FIREBASE_API_KEY;
  if (!apiKey) return null;
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
  if (event.httpMethod !== "POST") return json(405, { error: "POST only" });

  try {
    await requireUser(event);
  } catch (e) {
    return json(401, { error: e.message });
  }

  const user = process.env.SMTP_USER, pass = process.env.SMTP_PASS;
  if (!user || !pass)
    return json(503, { error: "Email is not configured. Set SMTP_USER and " +
      "SMTP_PASS in Netlify site settings (for Gmail use an App Password)." });

  let body;
  try { body = JSON.parse(event.body || "{}"); } catch { body = {}; }
  const to = (body.to || "").trim();
  if (!to.includes("@")) return json(400, { error: "Enter a valid email address" });

  const allowed = (process.env.ALLOWED_EMAILS || "")
    .split(",").map((e) => e.trim().toLowerCase()).filter(Boolean);
  if (allowed.length && !allowed.includes(to.toLowerCase()))
    return json(403, { error: "Recipient not in ALLOWED_EMAILS (anti-spam guard)" });

  const subject = String(body.subject || "Property search results").slice(0, 200);
  const text = String(body.text || "").slice(0, 100_000);
  const html = String(body.html || "").slice(0, 500_000);

  try {
    const transport = nodemailer.createTransport({
      host: process.env.SMTP_HOST || "smtp.gmail.com",
      port: parseInt(process.env.SMTP_PORT || "587", 10),
      secure: false,
      auth: { user, pass },
    });
    await transport.sendMail({ from: user, to, subject, text, html: html || undefined });
    return json(200, { ok: true, sent: to });
  } catch (e) {
    return json(500, { error: `Send failed: ${e.message}` });
  }
};
