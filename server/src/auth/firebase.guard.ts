/* Firebase auth guard — verifies the Bearer ID token against Firebase's
 * identitytoolkit REST endpoint (no firebase-admin dependency needed).
 *
 * Env:
 *   FIREBASE_API_KEY  the web API key; unset = auth disabled (open, dev only)
 *   ALLOWED_EMAILS    optional comma-separated account allowlist */

import {
  CanActivate, ExecutionContext, Injectable, UnauthorizedException,
} from "@nestjs/common";
import * as https from "https";

function postJson(url: string, payload: unknown): Promise<{ status: number; data: any }> {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify(payload);
    const req = https.request(
      url,
      { method: "POST", timeout: 15000,
        headers: { "Content-Type": "application/json",
                   "Content-Length": Buffer.byteLength(body) } },
      (res) => {
        const chunks: Buffer[] = [];
        res.on("data", (c) => chunks.push(c));
        res.on("end", () => {
          try {
            resolve({ status: res.statusCode || 0,
                      data: JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}") });
          } catch (e) { reject(e); }
        });
      },
    );
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("timeout")));
    req.end(body);
  });
}

@Injectable()
export class FirebaseGuard implements CanActivate {
  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const apiKey = process.env.FIREBASE_API_KEY;
    if (!apiKey) return true; // auth not configured — open (local dev)

    const req = ctx.switchToHttp().getRequest();
    const auth: string = req.headers.authorization || "";
    const idToken = auth.startsWith("Bearer ") ? auth.slice(7) : "";
    if (!idToken) throw new UnauthorizedException("Sign in first");

    const { status, data } = await postJson(
      `https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${apiKey}`,
      { idToken },
    );
    const email: string =
      (((data.users || [])[0] || {}).email || "").toLowerCase();
    if (status !== 200 || !email)
      throw new UnauthorizedException("Sign-in token rejected");

    const allowed = (process.env.ALLOWED_EMAILS || "")
      .split(",").map((e) => e.trim().toLowerCase()).filter(Boolean);
    if (allowed.length && !allowed.includes(email))
      throw new UnauthorizedException(`${email} is not allowed to use this app`);

    req.user = { email };
    return true;
  }
}
