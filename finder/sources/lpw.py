"""LankaPropertyWeb (lankapropertyweb.com) — leading dedicated real-estate portal.

Site structure (verified 2026-07-06):
  - Static, robots-allowed search pages:
      sale:  /forsale-{Province}_{City}-{Type}.html   e.g. /forsale-Western_Nugegoda-House.html
      rent:  /rentals/lease-{Province}_{City}-{Type}.html
      land:  /land/sale-{Province}_{City}-all.html (and /land/lease-... for rent);
             land cards price per perch (a span_psf "Per Perch" span) with the
             plot size stated in the title, so totals are computed client-side
    Spaces in names become "+" (Mount+Lavinia). Colombo 1-15 use the pseudo
    province "Colombo All": /forsale-Colombo+All_Colombo+6-Apartment.html
    Query-string search URLs (?location=, ?property-type=, ?search=1) are
    disallowed by robots.txt — never use them.
  - Result cards: <article class="listing-item" data-ad-id="...">, containing
    .listing-price ("Rs. 23.63M"), .listing-title <a href="/sale/property_details-NNN.html">,
    .listing-address, <span class="location">, bed count near bed.svg icon,
    <span class="type">House</span>.
  - Unknown city/type combinations return a 404 page.
"""

import re

from ..fetch import fetch, FetchError
from ..locations import lookup
from . import empty_result, now_iso

BASE = "https://www.lankapropertyweb.com"

TYPE = {"house": "House", "apartment": "Apartment", "land": "Land"}


def _location_slug(area):
    """'Nugegoda' -> 'Western_Nugegoda'; 'Colombo 5' -> 'Colombo+All_Colombo+5'."""
    a = area.strip().lower()
    if re.fullmatch(r"colombo(\s*\d{1,2})?", a):
        city = "Colombo" if a == "colombo" else area.strip().title()
        return "Colombo+All_" + city.replace(" ", "+")
    loc = lookup(area)
    if loc is None:
        return None
    city, _district, province = loc
    return f"{province.replace(' ', '+')}_{city.title().replace(' ', '+')}"


def _parse_price(text, purpose):
    """'Rs. 23.63M' -> 23630000, 'Rs. 150,000' -> 150000. None if unparseable
    or a unit price (per perch/sqft) that can't be compared to a total budget."""
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
    for chunk in re.split(r'<article class="listing-item"', html)[1:]:
        chunk = chunk[:6000]
        link = re.search(r'href="(/(?:sale|rentals|land)/property_details-\d+\.html)"', chunk)
        title = re.search(r'listing-title">\s*(?:<!--.*?-->\s*)?<a href="[^"]+">(.*?)</a>', chunk, re.S)
        price = re.search(r'class="listing-price">\s*([^<]+)', chunk)
        loc = re.search(r'class="location">([^<]*)<', chunk)
        beds = re.search(r'bed icon.*?class="count">(\d+)', chunk, re.S)
        addr = re.search(r'listing-address">.*?</i>\s*(.*?)\s*</h5>', chunk, re.S)
        if not link or not title:
            continue
        price_text = (price.group(1).strip() if price else "")
        title_text = re.sub(r"\s+", " ", title.group(1)).strip()
        addr_text = re.sub(r"\s+", " ", addr.group(1)).strip() if addr else ""
        # land cards price per perch (a "Per Perch" span follows the amount)
        # and state the plot size in the title, e.g. "Prime 61.5 Perch Land"
        per_perch = bool(re.search(r'span_psf">\s*Per\s*Perch', chunk, re.I))
        pm = re.search(r"([\d.]+)\s*perch", title_text + " " + addr_text, re.I)
        perches = float(pm.group(1)) if pm else None
        price_lkr = _parse_price(price_text, purpose)
        if per_perch and price_lkr:
            if perches:
                price_lkr = int(price_lkr * perches)
                price_text += f" per perch (≈ Rs {price_lkr:,} total for {perches:g}P)"
            else:
                price_text += " per perch"
                price_lkr = None
        ref = re.search(r"property_details-(\d+)", link.group(1))
        listings.append({
            # house.lk shares LPW's backend and listing IDs; refId lets
            # dedupe match the same property across the two sites exactly
            "refId": f"lpw-{ref.group(1)}" if ref else None,
            "title": title_text,
            "priceLKR": price_lkr,
            "priceText": price_text,
            "perches": perches,
            "area": (loc.group(1).strip() if loc else addr_text),
            "propertyType": ptype,
            "source": "lpw",
            "url": BASE + link.group(1),
            "bedrooms": int(beds.group(1)) if beds else None,
            "details": addr_text,
            "fetchedAt": now_iso(),
        })
    return listings


def search(profile):
    result = empty_result()
    purpose = profile.get("purpose", "buy")
    areas = profile.get("areas") or []
    types = profile.get("propertyTypes") or []

    for area in areas:
        loc = _location_slug(area)
        if not loc:
            result["errors"].append(
                f"lpw: no province mapping for '{area}' — not searched "
                f"(add it to PROVINCE in finder/sources/lpw.py)")
            continue
        for ptype in types:
            type_label = TYPE.get(ptype)
            if ptype == "land":
                # land lives in its own section with -all pages
                action = "lease" if purpose == "rent" else "sale"
                url = f"{BASE}/land/{action}-{loc}-all.html"
            elif purpose == "rent":
                url = f"{BASE}/rentals/lease-{loc}-{type_label}.html"
            else:
                url = f"{BASE}/forsale-{loc}-{type_label}.html"
            try:
                html = fetch(url)
            except FetchError as e:
                result["errors"].append(f"lpw: {e}")
                continue
            if "- 404" in html[:2000] or ">404<" in html:
                result["errors"].append(f"lpw: no search page for {area}/{ptype} ({url})")
                continue
            result["searched"].append(url)
            result["listings"].extend(_parse_cards(html, ptype, purpose))
    return result
