"""ikman.lk — largest classified site in Sri Lanka.

Site structure (verified 2026-07-06):
  - Search pages are path-based: https://ikman.lk/en/ads/{location-slug}/{category-slug}
    e.g. https://ikman.lk/en/ads/nugegoda/houses-for-sale
  - robots.txt disallows query-string filters (?sort=, ?query=, ?filters=,
    money.price params behave like filters), so we request the plain path and
    apply the budget filter client-side.
  - The page embeds all data as JSON in a `window.initialData = {...}` script;
    listings live at serp.ads.data.ads. Each ad has: slug, title, price
    ("Rs 80,000,000"), location ("Nugegoda"), details ("Bedrooms: 5, ...").
  - Listing URL: https://ikman.lk/en/ad/{slug}
  - Unknown location slugs 404; we then fall back to the all-island page and
    filter by area text client-side.
"""

import json
import re

from ..fetch import fetch, FetchError
from . import empty_result, now_iso

BASE = "https://ikman.lk/en/ads"

CATEGORY = {
    ("house", "buy"): "houses-for-sale",
    ("house", "rent"): "house-rentals",
    ("apartment", "buy"): "apartments-for-sale",
    ("apartment", "rent"): "apartment-rentals",
    ("land", "buy"): "land-for-sale",
    ("land", "rent"): "land-for-rent",
}


def _slug(area):
    return re.sub(r"[^a-z0-9]+", "-", area.lower()).strip("-")


def _parse_price(text, purpose):
    """'Rs 80,000,000' -> 80000000; rentals show 'Rs 700,000 /month', where the
    monthly figure IS the comparable price. Returns None for per-perch prices
    (a unit price can't be compared to a total budget)."""
    low = (text or "").lower()
    m = re.search(r"Rs\s*([\d,]+)", text or "")
    if not m or "perch" in low:
        return None
    if "month" in low and purpose != "rent":
        return None
    return int(m.group(1).replace(",", ""))


def _extract_ads(html):
    i = html.find("window.initialData")
    if i == -1:
        raise ValueError("window.initialData not found (page layout changed?)")
    start = html.index("{", i)
    data, _ = json.JSONDecoder().raw_decode(html[start:])
    return (((data.get("serp") or {}).get("ads") or {}).get("data") or {}).get("ads") or []


def search(profile):
    result = empty_result()
    types = profile.get("propertyTypes") or []
    purpose = profile.get("purpose", "buy")
    areas = profile.get("areas") or ["sri-lanka"]

    for ptype in types:
        category = CATEGORY.get((ptype, purpose))
        if not category:
            result["errors"].append(f"ikman: no category for {ptype}/{purpose}")
            continue
        for area in areas:
            url = f"{BASE}/{_slug(area)}/{category}"
            try:
                html = fetch(url)
            except FetchError as e:
                if e.status == 404:
                    # unknown location slug — fall back to all-island search
                    url = f"{BASE}/sri-lanka/{category}"
                    try:
                        html = fetch(url)
                    except FetchError as e2:
                        result["errors"].append(f"ikman: {e2}")
                        continue
                else:
                    result["errors"].append(f"ikman: {e}")
                    continue
            result["searched"].append(url)
            try:
                ads = _extract_ads(html)
            except ValueError as e:
                result["errors"].append(f"ikman: {url}: {e}")
                continue
            for ad in ads:
                if ad.get("isJobAd"):
                    continue
                details = ad.get("details") or ""
                beds = re.search(r"Bedrooms:\s*(\d+)", details)
                result["listings"].append({
                    # seller/agency name from the ad JSON; phone numbers are
                    # click-to-reveal on the ad page and never scraped
                    "contact": (ad.get("shopName") or "").strip() or None,
                    "title": (ad.get("title") or "").strip(),
                    "priceLKR": _parse_price(ad.get("price"), purpose),
                    "priceText": (ad.get("price") or "").strip(),
                    "area": (ad.get("location") or "").strip(),
                    "propertyType": ptype,
                    "source": "ikman",
                    "url": f"https://ikman.lk/en/ad/{ad.get('slug', '')}",
                    "bedrooms": int(beds.group(1)) if beds else None,
                    "details": details,
                    "fetchedAt": now_iso(),
                })
    return result
