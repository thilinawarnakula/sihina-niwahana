#!/usr/bin/env python3
"""Sihina Niwahana — small local website on top of the same search core.

Run:  python3 webapp.py            then open http://localhost:8765
Port: WEB_PORT env var (default 8765).

Login: optional. Set the APP_PASSWORD environment variable to require a
password; leave it unset for open local use. Sessions are a signed cookie —
nothing is stored server-side.

Email: the "Email me this summary" button needs SMTP_USER / SMTP_PASS
(see finder/emailer.py). Without them it explains what to set.

No history by design: web searches are kept in memory for the current
session only and are never written to data/.
"""

import hashlib
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from finder.core import run_search
from finder.emailer import send_summary, EmailNotConfigured

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "web" / "index.html"
PORT = int(os.environ.get("WEB_PORT", "8765"))
APP_PASSWORD = os.environ.get("APP_PASSWORD")  # unset = no login required

# last search result per session token, in memory only (no history on disk)
_last_results = {}


def _session_token():
    if not APP_PASSWORD:
        return "open"
    return hmac.new(APP_PASSWORD.encode(), b"sihina-session-v1",
                    hashlib.sha256).hexdigest()


class Handler(BaseHTTPRequestHandler):
    server_version = "SihinaNiwahana/1.0"

    # -- helpers ----------------------------------------------------------
    def _json(self, status, obj, headers=None):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 2_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            return {}

    def _authed(self):
        if not APP_PASSWORD:
            return True
        cookies = self.headers.get("Cookie") or ""
        return f"session={_session_token()}" in cookies.replace(" ", "")

    def log_message(self, fmt, *args):  # quieter logs
        print(f"[web] {self.address_string()} {fmt % args}")

    # -- routes -----------------------------------------------------------
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/config":
            self._json(200, {"loginRequired": bool(APP_PASSWORD),
                             "authed": self._authed(),
                             "emailConfigured": bool(os.environ.get("SMTP_USER"))})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/login":
            data = self._body()
            if APP_PASSWORD and data.get("password") == APP_PASSWORD:
                self._json(200, {"ok": True}, headers={
                    "Set-Cookie": f"session={_session_token()}; HttpOnly; "
                                  f"SameSite=Strict; Path=/"})
            else:
                self._json(401, {"error": "Wrong password"})
            return

        if not self._authed():
            self._json(401, {"error": "Login required"})
            return

        if self.path == "/api/search":
            profile = self._validate_profile(self._body())
            if isinstance(profile, str):
                self._json(400, {"error": profile})
                return
            payload = run_search(profile)
            _last_results[_session_token()] = payload
            self._json(200, payload)
        elif self.path == "/api/email":
            data = self._body()
            to = (data.get("to") or "").strip()
            if "@" not in to:
                self._json(400, {"error": "Enter a valid email address"})
                return
            payload = _last_results.get(_session_token())
            if not payload:
                self._json(400, {"error": "Run a search first"})
                return
            try:
                send_summary(to, payload)
                self._json(200, {"ok": True, "sent": to})
            except EmailNotConfigured as e:
                self._json(503, {"error": str(e)})
            except Exception as e:
                self._json(500, {"error": f"Send failed: {e}"})
        else:
            self._json(404, {"error": "not found"})

    @staticmethod
    def _validate_profile(data):
        types = [t for t in (data.get("propertyTypes") or [])
                 if t in ("land", "house", "apartment")]
        purpose = data.get("purpose")
        areas = [a.strip() for a in (data.get("areas") or []) if a.strip()][:8]
        if not types or purpose not in ("buy", "rent") or not areas:
            return "Property type, purpose and at least one area are required"

        def num(v):
            try:
                return int(float(v)) if v not in (None, "") else None
            except (TypeError, ValueError):
                return None
        budget = data.get("budgetLKR") or {}
        size = data.get("size") or {}
        return {
            "propertyTypes": types,
            "purpose": purpose,
            "areas": areas,
            "budgetLKR": {"min": num(budget.get("min")), "max": num(budget.get("max"))},
            "size": {"bedrooms": num(size.get("bedrooms")),
                     "bathrooms": None,
                     "perches": num(size.get("perches")), "sqft": None},
            "furnishing": "any",
            "mustHaves": [m.strip() for m in (data.get("mustHaves") or []) if m.strip()][:10],
            "dealBreakers": [d.strip() for d in (data.get("dealBreakers") or []) if d.strip()][:10],
            "timeline": "",
        }


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    login = "password login ON" if APP_PASSWORD else "no login (set APP_PASSWORD to enable)"
    print(f"Sihina Niwahana web UI: http://localhost:{PORT}  ({login})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
