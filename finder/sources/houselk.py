"""house.lk (formerly Lamudi.lk) — secondary source.

Site structure (verified 2026-07-06):
  - Path-based search pages: https://house.lk/{sale|rent}/{district}/{city}/{type}/
    e.g. /sale/colombo/nugegoda/house/ — types: house, apartment, land
    (also commercial/bungalow/villa, unused here). "Colombo 5" -> colombo-5.
  - robots.txt disallows pagination (/*page*) and various punctuation
    patterns; the plain first page used here is allowed.
  - Result cards: <div class="property_listing">, with the listing link
    /details/{slug}-{id}/, title in <h4><a>, price in
    .listing_unit_price_wrapper ("Rs. 54M"), location in
    .action_tag_location_wrapper after the marker <span>.
  - house.lk shares LankaPropertyWeb's backend: images come from
    lankapropertyweb.com/pics and the numeric listing IDs match LPW's
    property_details IDs, so refId ("lpw-{id}") dedupes across the two.
"""

import re

from ..fetch import fetch, FetchError
from ..locations import lookup, slug
from . import empty_result, now_iso

BASE = "https://house.lk"

TYPE = {"house": "house", "apartment": "apartment", "land": "land"}


def _parse_price(text, purpose):
    """'Rs. 54M' -> 54000000; 'Rs. 150,000' -> 150000 (same style as LPW)."""
    t = (text or "").strip()
    low = t.lower()
    if "per perch" in low or "per sqft" in low or "per sq" in low:
        return None
    m = re.search(r"Rs\.?\s*([\d,]+(?:\.\d+)?)\s*(m|million|k)?", t, re.I)
    if not m:
        return None
    value = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit in ("m", "million"):
        value *= 1_000_000
    elif unit == "k":
        value *= 1_000
    return int(value)


def _parse_cards(html, ptype, purpose):
    listings = []
    for chunk in re.split(r'class="property_listing', html)[1:]:
        chunk = chunk[:7000]
        link = re.search(r'href="(/details/[^"]+-(\d+)/?)"', chunk)
        title = re.search(r"<h4>\s*<a href=\"[^\"]+\">\s*(.*?)\s*</a>", chunk, re.S)
        price = re.search(r'listing_unit_price_wrapper">\s*([^<]+)', chunk)
        loc = re.search(r'action_tag_location_wrapper[^>]*>.*?</span>([^<]*)<', chunk, re.S)
        if not link or not title:
            continue
        price_text = (price.group(1).strip() if price else "")
        title_text = re.sub(r"\s+", " ", title.group(1)).strip()
        # land cards price per perch with the plot size stated in the title
        per_perch = bool(re.search(r"per\s*perch", chunk[:2500], re.I))
        pm = re.search(r"([\d.]+)\s*perch", title_text, re.I)
        perches = float(pm.group(1)) if pm else None
        price_lkr = _parse_price(price_text, purpose)
        if per_perch and price_lkr:
            if perches:
                price_lkr = int(price_lkr * perches)
                price_text += f" per perch (≈ Rs {price_lkr:,} total for {perches:g}P)"
            else:
                price_text += " per perch"
                price_lkr = None
        listings.append({
            "refId": f"lpw-{link.group(2)}",  # shared backend with LPW
            "title": title_text,
            "priceLKR": price_lkr,
            "priceText": price_text,
            "perches": perches,
            "area": (loc.group(1).strip() if loc else ""),
            "propertyType": ptype,
            "source": "houselk",
            "url": BASE + link.group(1),
            "bedrooms": None,
            "details": "",
            "fetchedAt": now_iso(),
        })
    return listings


def search(profile):
    result = empty_result()
    purpose = profile.get("purpose", "buy")
    action = "rent" if purpose == "rent" else "sale"

    for area in profile.get("areas") or []:
        loc = lookup(area)
        if loc is None:
            result["errors"].append(
                f"houselk: unknown area '{area}' — not searched "
                f"(add it to finder/locations.py)")
            continue
        city, district, _province = loc
        for ptype in profile.get("propertyTypes") or []:
            url = f"{BASE}/{action}/{slug(district)}/{slug(city)}/{TYPE[ptype]}/"
            try:
                html = fetch(url)
            except FetchError as e:
                result["errors"].append(f"houselk: {e}")
                continue
            result["searched"].append(url)
            result["listings"].extend(_parse_cards(html, ptype, purpose))
    return result
