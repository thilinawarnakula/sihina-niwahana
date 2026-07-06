"""Intake: short conversation to build the search profile (CLAUDE.md section 3).

Questions are asked one topic at a time; anything already provided (via CLI
flags or an existing profile) is skipped. The collected profile is confirmed
back to the user before saving to data/search-profile.json.
"""

import json
from datetime import datetime, timezone

from . import PROFILE_PATH, PROFILES_DIR

VALID_TYPES = ("land", "house", "apartment")


def _ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or (default or "")


def _ask_list(prompt, default=None):
    raw = _ask(prompt + " (comma-separated, blank to skip)", default)
    return [x.strip() for x in raw.split(",") if x.strip()]


def _ask_int(prompt):
    while True:
        raw = _ask(prompt + " (blank to skip)")
        if not raw:
            return None
        digits = raw.lower().replace(",", "").replace("lkr", "").replace("rs", "").strip()
        try:
            if digits.endswith("m"):
                return int(float(digits[:-1]) * 1_000_000)
            if digits.endswith("k"):
                return int(float(digits[:-1]) * 1_000)
            return int(float(digits))
        except ValueError:
            print("  Please enter a number (e.g. 45000000 or 45m).")


def load_profile(path=PROFILE_PATH):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_profile(profile, name=None):
    profile["createdAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = json.dumps(profile, indent=2, ensure_ascii=False)
    PROFILE_PATH.write_text(text, encoding="utf-8")
    if name:
        (PROFILES_DIR / f"{name}.json").write_text(text, encoding="utf-8")
    return PROFILE_PATH


def summarize(profile):
    budget = profile.get("budgetLKR") or {}
    size = profile.get("size") or {}
    lines = [
        f"  Property type(s): {', '.join(profile.get('propertyTypes') or [])}",
        f"  Purpose:          {profile.get('purpose', '')}",
        f"  Area(s):          {', '.join(profile.get('areas') or [])}",
    ]
    if budget.get("min") or budget.get("max"):
        lines.append(f"  Budget (LKR):     {budget.get('min') or 'any'} - {budget.get('max') or 'any'}")
    parts = [f"{v} {k}" for k, v in size.items() if v]
    if parts:
        lines.append(f"  Size:             {', '.join(parts)}")
    for key, label in (("furnishing", "Furnishing"), ("mustHaves", "Must-haves"),
                       ("dealBreakers", "Deal-breakers"), ("timeline", "Timeline")):
        val = profile.get(key)
        if val:
            lines.append(f"  {label + ':':<17} {', '.join(val) if isinstance(val, list) else val}")
    return "\n".join(lines)


def run_intake(prefilled=None):
    """Interactive intake. `prefilled` holds answers already given (skipped)."""
    p = dict(prefilled or {})
    print("Sri Lanka Property Finder — let's set up your search.\n"
          "(Press Enter to skip any optional question.)\n")

    while not p.get("propertyTypes"):
        types = _ask_list("1. What are you looking for — land, house, apartment? "
                          "(one or more)")
        types = [t.lower() for t in types if t.lower() in VALID_TYPES]
        if types:
            p["propertyTypes"] = types
        else:
            print("  Please answer with land, house, and/or apartment.")

    while p.get("purpose") not in ("buy", "rent"):
        p["purpose"] = _ask("2. Buy or rent?").lower()

    while not p.get("areas"):
        p["areas"] = _ask_list("3. Which area(s)? (district, city or town, "
                               "e.g. Nugegoda, Colombo 5, Kandy)")

    if "budgetLKR" not in p:
        print("4. Budget in LKR?")
        p["budgetLKR"] = {"min": _ask_int("   minimum"), "max": _ask_int("   maximum")}

    if "size" not in p:
        print("5. Size requirements?")
        size = {"bedrooms": None, "bathrooms": None, "perches": None, "sqft": None}
        if set(p["propertyTypes"]) & {"house", "apartment"}:
            size["bedrooms"] = _ask_int("   bedrooms (min)")
            size["bathrooms"] = _ask_int("   bathrooms (min)")
            size["sqft"] = _ask_int("   floor area sqft (min)")
        if "land" in p["propertyTypes"]:
            size["perches"] = _ask_int("   land size in perches (min)")
        p["size"] = size

    if "furnishing" not in p and set(p["propertyTypes"]) & {"house", "apartment"}:
        p["furnishing"] = _ask("6. Furnishing — furnished / semi-furnished / "
                               "unfurnished", "any").lower()

    if "mustHaves" not in p:
        p["mustHaves"] = _ask_list("7. Must-haves? (e.g. parking, garden, sea view, "
                                   "near main road)")
    if "dealBreakers" not in p:
        p["dealBreakers"] = _ask_list("8. Anything to exclude (deal-breakers)?")
    if "timeline" not in p:
        p["timeline"] = _ask("9. How soon do you want to move/buy? (blank to skip)")

    print("\nHere's what I've got:\n" + summarize(p) + "\n")
    if _ask("Save this profile and use it for searching? (y/n)", "y").lower().startswith("y"):
        name = _ask("Optional: name this profile for reuse (blank to skip)")
        path = save_profile(p, name or None)
        print(f"Saved to {path}")
        return p
    print("Not saved. Run intake again to start over.")
    return None
