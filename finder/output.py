"""Output: print the ranked shortlist and save results to data/results/.

Every listing line shows source, price (LKR, as the site displayed it),
area, and the direct link. Coverage (what was and wasn't searched) is
always reported.
"""

import json
from datetime import datetime, timezone

from . import RESULTS_DIR


def _fmt_price(lst):
    if lst.get("priceText"):
        return lst["priceText"]
    if lst.get("priceLKR"):
        return f"Rs {lst['priceLKR']:,}"
    return "price not stated"


def print_results(listings, coverage, manual_links, limit=20):
    if not listings:
        print("\nNo matching listings found.")
    else:
        print(f"\n=== Shortlist ({min(len(listings), limit)} of {len(listings)} matches) ===\n")
        for i, lst in enumerate(listings[:limit], 1):
            beds = f" | {lst['bedrooms']} bed" if lst.get("bedrooms") else ""
            also = f" (also on: {', '.join(lst['alsoOn'])})" if lst.get("alsoOn") else ""
            contact = f" | seller: {lst['contact']}" if lst.get("contact") else ""
            print(f"{i:2}. {lst['title']}")
            print(f"    {_fmt_price(lst)} | {lst['area']} | {lst['propertyType']}{beds}{contact}")
            print(f"    [{lst['source']}]{also} {lst['url']}\n")

    print("=== Coverage ===")
    for src, info in coverage.items():
        if info["searched"]:
            print(f"  {src}: searched {len(info['searched'])} page(s), "
                  f"{info['count']} listing(s) found")
        for err in info["errors"]:
            print(f"  ! {err}")

    if manual_links:
        print("\n=== Browse yourself (not searched automatically) ===")
        for link in manual_links:
            print(f"  {link['label']}\n    {link['url']}")


def save_results(listings, profile, coverage):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = RESULTS_DIR / f"results-{stamp}.json"
    payload = {
        "savedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": profile,
        "coverage": {k: {"searched": v["searched"], "errors": v["errors"]}
                     for k, v in coverage.items()},
        "listings": listings,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
