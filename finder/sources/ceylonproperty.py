"""CeylonProperty.lk — manual-link source. NOT crawled.

CeylonProperty's robots.txt (checked 2026-07-06) disallows every listing
search entry point: /search, /buy_property, /rent_property, /lands,
/buy-property-in-, /rent-. Only directory/blog pages are open, which don't
carry listings. Per the project guardrails we respect robots.txt, so this
module just links the site's homepage search for manual browsing.
"""

from . import empty_result

HOME = "https://ceylonproperty.lk/"


def search(profile):
    result = empty_result()
    result["manual"].append({
        "label": "CeylonProperty.lk (search by area/type on the site)",
        "url": HOME,
    })
    result["errors"].append(
        "ceylonproperty: not searched automatically (robots.txt disallows "
        "its listing-search pages). Browse the CeylonProperty link below "
        "manually.")
    return result
