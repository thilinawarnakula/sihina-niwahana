"""Polite HTTP fetching: normal User-Agent, rate limiting, short-lived disk cache.

Guardrails (CLAUDE.md section 7): only fetch public, robots.txt-allowed URLs,
wait between requests, cache pages briefly so one search session never hits
the same URL twice.
"""

import hashlib
import time
import urllib.error
import urllib.request

from . import CACHE_DIR

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
REQUEST_DELAY_SECONDS = 1.5
CACHE_TTL_SECONDS = 15 * 60
TIMEOUT_SECONDS = 25

_last_request_at = 0.0


class FetchError(Exception):
    """Raised when a URL cannot be fetched (site down, blocked, 404...)."""

    def __init__(self, url, reason, status=None):
        super().__init__(f"{url}: {reason}")
        self.url = url
        self.reason = reason
        self.status = status


def _cache_path(url):
    return CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest() + ".html")


def fetch(url):
    """Return the page body for `url` as text, using cache when fresh."""
    cached = _cache_path(url)
    if cached.exists() and time.time() - cached.stat().st_mtime < CACHE_TTL_SECONDS:
        return cached.read_text(encoding="utf-8", errors="replace")

    global _last_request_at
    wait = REQUEST_DELAY_SECONDS - (time.time() - _last_request_at)
    if wait > 0:
        time.sleep(wait)

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        _last_request_at = time.time()
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise FetchError(url, f"HTTP {e.code}", status=e.code) from e
    except Exception as e:  # URLError, timeout, decode issues
        raise FetchError(url, str(e)) from e

    cached.write_text(body, encoding="utf-8")
    return body
