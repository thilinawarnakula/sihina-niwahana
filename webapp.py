#!/usr/bin/env python3
"""Sihina Niwahana — small local website on top of the same search core.

Run:  python3 webapp.py            then open http://localhost:8765
Port: WEB_PORT env var (default 8765).

Login (three modes, picked automatically):
  1. Firebase  — paste your Firebase web config into web/firebase-config.js
     and the site shows "Sign in with Google". The ID token is verified
     server-side against Firebase's REST API (no packages needed). Restrict
     who may log in with ALLOWED_EMAILS="a@x.com,b@y.com" (optional).
  2. Password  — no Firebase config, but APP_PASSWORD env var set.
  3. Open      — neither configured; no login (fine for local use).

Email: the "Email me this summary" button needs SMTP_USER / SMTP_PASS
(see finder/emailer.py). Without them it explains what to set.

No history by design: web searches are kept in memory for the current
session only and are never written to data/.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from finder.core import run_search
from finder.emailer import send_summary, EmailNotConfigured

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"
INDEX = WEB_DIR / "index.html"
FB_CONFIG = WEB_DIR / "firebase-config.js"
PORT = int(os.environ.get("WEB_PORT", "8765"))
APP_PASSWORD = os.environ.get("APP_PASSWORD")
ALLOWED_EMAILS = {e.strip().lower()
                  for e in os.environ.get("ALLOWED_EMAILS", "").split(",")
                  if e.strip()}


def _firebase_api_key():
    """The web apiKey from firebase-config.js, or None if not configured.
    (The web config is public by design; the apiKey is not a secret.)"""
    try:
        txt = FB_CONFIG.read_text(encoding="utf-8")
    except OSError:
        return None
    live = "\n".join(l for l in txt.splitlines() if not l.lstrip().startswith("//"))
    m = re.search(r'apiKey\s*:\s*["\']([A-Za-z0-9_\-]+)["\']', live)
    return m.group(1) if m else None


FIREBASE_API_KEY = _firebase_api_key()
LOGIN_MODE = ("firebase" if FIREBASE_API_KEY
              else "password" if APP_PASSWORD else "none")

# in-memory state only — dies with the server, nothing on disk
_sessions = {}      # session token -> email (or "password-user")
_last_results = {}  # session token -> last search payload


def _password_token():
    return hmac.new(APP_PASSWORD.encode(), b"sihina-session-v1",
                    hashlib.sha256).hexdigest()


def _verify_firebase_token(id_token):
    """Ask Firebase whether this ID token is valid. Returns the user's email
    or raises ValueError. Uses the public identitytoolkit REST endpoint."""
    url = ("https://identitytoolkit.googleapis.com/v1/accounts:lookup"
           f"?key={FIREBASE_API_KEY}")
    req = urllib.request.Request(
        url, data=json.dumps({"idToken": id_token}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise ValueError("Firebase rejected the sign-in token") from e
    users = data.get("users") or []
    if not users:
        raise ValueError("Invalid sign-in token")
    email = (users[0].get("email") or "").lower()
    if not email:
        raise ValueError("Account has no email address")
    if ALLOWED_EMAILS and email not in ALLOWED_EMAILS:
        raise ValueError(f"{email} is not allowed to use this app")
    return email


class Handler(BaseHTTPRequestHandler):
    server_version = "SihinaNiwahana/1.1"

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

    def _file(self, path, ctype):
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
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

    def _cookie_token(self):
        cookies = (self.headers.get("Cookie") or "").replace(" ", "")
        for part in cookies.split(";"):
            if part.startswith("session="):
                return part[len("session="):]
        return None

    def _session_key(self):
        """Key for per-session state; also the auth check."""
        tok = self._cookie_token()
        if LOGIN_MODE == "none":
            return "open"
        if LOGIN_MODE == "password":
            return tok if tok == _password_token() else None
        return tok if tok in _sessions else None

    def log_message(self, fmt, *args):
        print(f"[web] {self.address_string()} {fmt % args}")

    # -- routes -----------------------------------------------------------
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._file(INDEX, "text/html; charset=utf-8")
        elif self.path == "/firebase-config.js":
            self._file(FB_CONFIG, "application/javascript; charset=utf-8")
        elif self.path == "/api/config":
            key = self._session_key()
            self._json(200, {
                "loginMode": LOGIN_MODE,
                "authed": key is not None,
                "user": _sessions.get(key),
                "emailConfigured": bool(os.environ.get("SMTP_USER")),
            })
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/api/login":
            self._login()
            return
        if self.path == "/api/logout":
            tok = self._cookie_token()
            _sessions.pop(tok, None)
            _last_results.pop(tok, None)
            self._json(200, {"ok": True}, headers={
                "Set-Cookie": "session=; Max-Age=0; Path=/"})
            return

        key = self._session_key()
        if key is None:
            self._json(401, {"error": "Login required"})
            return

        if self.path == "/api/search":
            profile = self._validate_profile(self._body())
            if isinstance(profile, str):
                self._json(400, {"error": profile})
                return
            payload = run_search(profile)
            _last_results[key] = payload
            self._json(200, payload)
        elif self.path == "/api/email":
            data = self._body()
            to = (data.get("to") or "").strip()
            if "@" not in to:
                self._json(400, {"error": "Enter a valid email address"})
                return
            payload = _last_results.get(key)
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

    def _login(self):
        data = self._body()
        if LOGIN_MODE == "firebase":
            try:
                email = _verify_firebase_token(data.get("idToken") or "")
            except ValueError as e:
                self._json(401, {"error": str(e)})
                return
            token = secrets.token_hex(32)
            _sessions[token] = email
            self._json(200, {"ok": True, "user": email}, headers={
                "Set-Cookie": f"session={token}; HttpOnly; "
                              f"SameSite=Strict; Path=/"})
        elif LOGIN_MODE == "password":
            if data.get("password") == APP_PASSWORD:
                self._json(200, {"ok": True}, headers={
                    "Set-Cookie": f"session={_password_token()}; HttpOnly; "
                                  f"SameSite=Strict; Path=/"})
            else:
                self._json(401, {"error": "Wrong password"})
        else:
            self._json(400, {"error": "No login configured"})

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
    mode = {"firebase": "Firebase Google sign-in",
            "password": "password login (APP_PASSWORD)",
            "none": "no login — set APP_PASSWORD or add web/firebase-config.js"}
    print(f"Sihina Niwahana web UI: http://localhost:{PORT}  [{mode[LOGIN_MODE]}]")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
