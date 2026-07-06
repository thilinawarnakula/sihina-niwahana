"""LankaLand.lk — secondary source (WordPress site, robots.txt allows crawling).

Site structure (verified 2026-07-06):
  - Search endpoint: https://www.lankaland.lk/search-results?category={cat}&city={city}&status={sale|rent}
    Categories: house, apartment, land. City/district slugs are lowercase-hyphen.
    Pagination exists (/search-results/page/2/...) but only page 1 is fetched.
  - Result cards: <div class="property-item search-listing-item"> with
    <h3> title, an <a ... class="full-link"> listing URL, "LKR 37,500,000"
    (or "Negotiable") in the price block, and District/City meta links.
  - Smaller inventory than the primary sources; prices are often missing
    ("Negotiable"), which leaves priceLKR as None.
"""

import re
import urllib.parse

from ..fetch import fetch, FetchError
from ..locations import lookup, slug
from . import empty_result, now_iso

BASE = "https://www.lankaland.lk"

CATEGORY = {"house": "house", "apartment": "apartment", "land": "land"}


def _parse_price(text):
    m = re.search(r"LKR\s*([\d,]+(?:\.\d+)?)", text or "", re.I)
    if not m:
        return None
    return int(float(m.group(1).replace(",", "")))


def _parse_cards(html, ptype):
    listings = []
    for chunk in re.split(r'property-item search-listing-item', html)[1:]:
        chunk = chunk[:6000]
        link = re.search(r'href="(https://www\.lankaland\.lk/[^"]+)" class="full-link"', chunk)
        title = re.search(r"<h3>\s*(.*?)\s*</h3>", chunk, re.S)
        price = re.search(r"LKR\s*[\d,]+(?:\.\d+)?", chunk)
        city = re.search(r'item city.*?search-results\?city=[^"]*">\s*([^<]+?)\s*</a>', chunk, re.S)
        district = re.search(r'item district.*?search-results\?district=[^"]*">\s*([^<]+?)\s*</a>', chunk, re.S)
        if not link or not title:
            continue
        price_text = price.group(0) if price else "Negotiable"
        area = (city.group(1).strip() if city else
                (district.group(1).strip() if district else ""))
        listings.append({
            "title": re.sub(r"\s+", " ", title.group(1)).strip(),
            "priceLKR": _parse_price(price_text),
            "priceText": price_text,
            "area": area,
            "propertyType": ptype,
            "source": "lankaland",
            "url": link.group(1),
            "bedrooms": None,
            "details": "",
            "fetchedAt": now_iso(),
        })
    return listings


def search(profile):
    result = empty_result()
    purpose = profile.get("purpose", "buy")
    status = "rent" if purpose == "rent" else "sale"

    for area in profile.get("areas") or []:
        loc = lookup(area)
        if loc is None:
            result["errors"].append(
                f"lankaland: unknown area '{area}' — not searched "
                f"(add it to finder/locations.py)")
            continue
        city, _district, _province = loc
        for ptype in profile.get("propertyTypes") or []:
            params = urllib.parse.urlencode({
                "category": CATEGORY[ptype],
                "city": slug(city),
                "status": status,
            })
            url = f"{BASE}/search-results?{params}"
            try:
                html = fetch(url)
            except FetchError as e:
                result["errors"].append(f"lankaland: {e}")
                continue
            result["searched"].append(url)
            result["listings"].extend(_parse_cards(html, ptype))
    return result
