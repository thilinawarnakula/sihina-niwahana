"""Ranking: sort merged listings by how well each matches the profile.

Scoring (higher is better):
  +3  listing area matches one of the requested areas
  +3  price is within budget (+1 if price known but budget open-ended)
  +1  per must-have keyword found in the title/details
  +2  bedroom count meets the requested minimum
  -4  per deal-breaker keyword found
  -2  price known and above budget max (kept but demoted, shown as over budget)

Listings whose price exceeds budget by more than 15% are dropped entirely.
"""


def _text(lst):
    return " ".join([lst.get("title", ""), lst.get("details", ""),
                     lst.get("area", "")]).lower()


def score(lst, profile):
    s = 0
    areas = [a.lower() for a in profile.get("areas") or []]
    area_text = (lst.get("area") or "").lower()
    if any(a in area_text or area_text in a for a in areas if area_text):
        s += 3

    budget = profile.get("budgetLKR") or {}
    price, bmin, bmax = lst.get("priceLKR"), budget.get("min"), budget.get("max")
    if price is not None:
        if (bmin is None or price >= bmin) and (bmax is None or price <= bmax):
            s += 3 if (bmin or bmax) else 1
        elif bmax is not None and price > bmax:
            s -= 2

    text = _text(lst)
    for want in profile.get("mustHaves") or []:
        if want.lower() in text:
            s += 1
    for avoid in profile.get("dealBreakers") or []:
        if avoid.lower() in text:
            s -= 4

    want_beds = (profile.get("size") or {}).get("bedrooms")
    if want_beds and lst.get("bedrooms") and lst["bedrooms"] >= want_beds:
        s += 2

    want_perches = (profile.get("size") or {}).get("perches")
    if want_perches and lst.get("perches"):
        s += 2 if lst["perches"] >= want_perches else -1
    return s


def rank(listings, profile):
    budget = profile.get("budgetLKR") or {}
    bmax = budget.get("max")
    kept = []
    for lst in listings:
        price = lst.get("priceLKR")
        if bmax and price and price > bmax * 1.15:
            continue
        lst["score"] = score(lst, profile)
        kept.append(lst)
    kept.sort(key=lambda x: (-x["score"], x["priceLKR"] or 10**15))
    return kept
