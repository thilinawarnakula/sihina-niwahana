"""patpat.lk — manual-link source. NEVER crawled.

patpat.lk's robots.txt disallows ALL crawling (`User-agent: * / Disallow: /`)
and the server returns 403 to non-browser clients (checked 2026-07-06). Per
the project guardrails we respect that, so this module only points the user
at patpat's property section to browse manually. Only the base property URL
is linked because deeper paths can't be verified without a browser.
Revisit if their robots.txt ever opens up.
"""

from . import empty_result

PROPERTY_URL = "https://patpat.lk/en/sri-lanka/property"


def search(profile):
    result = empty_result()
    result["manual"].append({
        "label": "patpat.lk property section (search by area/type on the site)",
        "url": PROPERTY_URL,
    })
    result["errors"].append(
        "patpat: not searched automatically (robots.txt disallows all "
        "crawling and the site blocks non-browser clients). Browse the "
        "patpat.lk link below manually.")
    return result
