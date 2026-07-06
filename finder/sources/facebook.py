"""Facebook Marketplace — link generator only. NEVER scraped.

Marketplace has no public read/search API and scraping it violates Facebook's
Terms of Service (see CLAUDE.md section 4). This module only builds a
ready-to-click search URL pre-filled from the profile so the user can browse
Marketplace themselves.
"""

import urllib.parse

from . import empty_result

TYPE_QUERY = {"house": "house", "apartment": "apartment", "land": "land"}


def search(profile):
    result = empty_result()
    purpose = profile.get("purpose", "buy")
    budget = profile.get("budgetLKR") or {}
    for area in profile.get("areas") or ["Sri Lanka"]:
        for ptype in profile.get("propertyTypes") or []:
            words = [TYPE_QUERY.get(ptype, ptype)]
            words.append("for rent" if purpose == "rent" else "for sale")
            words.append(area)
            params = {"query": " ".join(words)}
            if budget.get("min"):
                params["minPrice"] = str(budget["min"])
            if budget.get("max"):
                params["maxPrice"] = str(budget["max"])
            url = ("https://www.facebook.com/marketplace/colombo/search?"
                   + urllib.parse.urlencode(params))
            result["manual"].append({
                "label": f"Marketplace: {ptype} {'rentals' if purpose == 'rent' else 'sales'} in {area}",
                "url": url,
            })
    result["errors"].append(
        "facebook: not searched automatically (no public API; scraping violates "
        "ToS). Use the pre-filled Marketplace links below to browse manually.")
    return result
