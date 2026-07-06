"""Site-specific search modules.

Every module exposes `search(profile) -> dict` with keys:
  listings: list of normalized listing dicts (see below)
  searched: list of URLs actually fetched
  errors:   list of human-readable strings for anything that failed/was skipped
  manual:   optional list of {"label", "url"} links for the user to browse
            themselves (used by sources we must not scrape, e.g. Facebook)

Normalized listing shape (same for every source):
  {
    "title": str,
    "priceLKR": int | None,     # parsed numeric price in LKR, None if unclear
    "priceText": str,           # price exactly as shown on the site
    "area": str,
    "propertyType": "house" | "apartment" | "land" | "",
    "source": "<site id>",
    "url": str,                 # direct link to the original listing
    "bedrooms": int | None,
    "details": str,
    "fetchedAt": str,           # ISO-8601 UTC
  }
"""

from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_result():
    return {"listings": [], "searched": [], "errors": [], "manual": []}
