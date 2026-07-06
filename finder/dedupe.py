"""De-duplication.

The same property is often posted on multiple sites and by multiple agents.
Two listings are considered duplicates when they share a refId (sites that
share a backend, e.g. house.lk mirrors LankaPropertyWeb's listing IDs), when
their URLs match, or when their normalized titles match and prices are within
2% of each other. Titles are compared by prefix (min 20 chars) because some
sites truncate titles with "...".
The listing from the higher-priority (first-seen) source is kept and the
duplicate's source is recorded in `alsoOn`.
"""

import re


def _norm_title(title):
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _same_title(a, b):
    a, b = _norm_title(a), _norm_title(b)
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return len(shorter) >= 20 and longer.startswith(shorter)


def _same_price(a, b):
    if a is None or b is None:
        return a == b
    if a == b:
        return True
    return abs(a - b) / max(a, b) <= 0.02


def dedupe(listings):
    kept = []
    seen_urls = set()
    for lst in listings:
        if lst["url"] in seen_urls:
            continue
        dup = None
        for k in kept:
            if lst.get("refId") and k.get("refId") == lst["refId"]:
                dup = k
                break
            if _same_title(k["title"], lst["title"]) and \
                    _same_price(k["priceLKR"], lst["priceLKR"]):
                dup = k
                break
        if dup is not None:
            also = dup.setdefault("alsoOn", [])
            if lst["source"] not in also and lst["source"] != dup["source"]:
                also.append(lst["source"])
            continue
        seen_urls.add(lst["url"])
        kept.append(lst)
    return kept
