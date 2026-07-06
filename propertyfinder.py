#!/usr/bin/env python3
"""Sri Lanka Property Finder — CLI entry point.

Usage:
  python3 propertyfinder.py intake              # interactive Q&A, saves profile
  python3 propertyfinder.py intake --type house --purpose buy --area Nugegoda \
      --min 20m --max 45m --yes                 # scripted intake, no prompts
  python3 propertyfinder.py search              # search using the saved profile
  python3 propertyfinder.py search --profile myname   # use a named profile
  python3 propertyfinder.py show                # print the current profile

Sri Lanka properties only. Uses stdlib only — no packages to install.
"""

import argparse
import json
import sys

from finder import PROFILES_DIR
from finder.core import run_search
from finder.intake import load_profile, run_intake, save_profile, summarize
from finder.output import print_results, save_results
from finder.report import write_report


def _parse_lkr(raw):
    if raw is None:
        return None
    s = raw.lower().replace(",", "").strip()
    mult = 1
    if s.endswith("m"):
        mult, s = 1_000_000, s[:-1]
    elif s.endswith("k"):
        mult, s = 1_000, s[:-1]
    return int(float(s) * mult)


def cmd_intake(args):
    prefilled = {}
    if args.type:
        prefilled["propertyTypes"] = [t.lower() for t in args.type]
    if args.purpose:
        prefilled["purpose"] = args.purpose
    if args.area:
        prefilled["areas"] = args.area
    if args.min or args.max:
        prefilled["budgetLKR"] = {"min": _parse_lkr(args.min), "max": _parse_lkr(args.max)}
    if args.bedrooms:
        prefilled["size"] = {"bedrooms": args.bedrooms, "bathrooms": None,
                             "perches": None, "sqft": None}
    if args.must_have:
        prefilled["mustHaves"] = args.must_have
    if args.exclude:
        prefilled["dealBreakers"] = args.exclude

    if args.yes:
        missing = [k for k in ("propertyTypes", "purpose", "areas") if not prefilled.get(k)]
        if missing:
            sys.exit(f"--yes needs at least --type, --purpose and --area (missing: {missing})")
        prefilled.setdefault("budgetLKR", {"min": None, "max": None})
        prefilled.setdefault("size", {"bedrooms": None, "bathrooms": None,
                                      "perches": None, "sqft": None})
        prefilled.setdefault("furnishing", "any")
        prefilled.setdefault("mustHaves", [])
        prefilled.setdefault("dealBreakers", [])
        prefilled.setdefault("timeline", "")
        path = save_profile(prefilled, args.name)
        print("Profile saved to", path)
        print(summarize(prefilled))
        return

    run_intake(prefilled)


def cmd_show(_args):
    profile = load_profile()
    if not profile:
        sys.exit("No saved profile. Run: python3 propertyfinder.py intake")
    print(summarize(profile))


def cmd_search(args):
    if args.profile:
        named = PROFILES_DIR / f"{args.profile}.json"
        if not named.exists():
            sys.exit(f"No profile named '{args.profile}' in {PROFILES_DIR}")
        profile = json.loads(named.read_text(encoding="utf-8"))
    else:
        profile = load_profile()
    if not profile:
        sys.exit("No saved profile ('same as last time' needs a previous search). "
                 "Run: python3 propertyfinder.py intake")

    print("Searching with profile:\n" + summarize(profile) + "\n")

    payload = run_search(profile,
                         on_progress=lambda name: print(f"Searching {name} ..."))
    ranked, coverage = payload["listings"], payload["coverage"]
    print_results(ranked, coverage, payload["manualLinks"], limit=args.limit)
    path = save_results(ranked, profile, coverage)
    print(f"\nFull results saved to {path}")
    if args.html:
        report = write_report(path)
        print(f"HTML report: {report}")
        _open_in_browser(report)


def _open_in_browser(path):
    import subprocess
    import sys as _sys
    if _sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)


def cmd_report(args):
    try:
        report = write_report()
    except FileNotFoundError as e:
        sys.exit(str(e))
    print(f"HTML report: {report}")
    if not args.no_open:
        _open_in_browser(report)


def main():
    ap = argparse.ArgumentParser(description="Sri Lanka Property Finder")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ia = sub.add_parser("intake", help="collect search requirements")
    ia.add_argument("--type", action="append", choices=["land", "house", "apartment"])
    ia.add_argument("--purpose", choices=["buy", "rent"])
    ia.add_argument("--area", action="append")
    ia.add_argument("--min", help="budget min in LKR (e.g. 20m)")
    ia.add_argument("--max", help="budget max in LKR (e.g. 45m)")
    ia.add_argument("--bedrooms", type=int)
    ia.add_argument("--must-have", action="append")
    ia.add_argument("--exclude", action="append")
    ia.add_argument("--name", help="also save as a named profile")
    ia.add_argument("--yes", action="store_true",
                    help="non-interactive: save with given flags, skip questions")
    ia.set_defaults(func=cmd_intake)

    se = sub.add_parser("search", help="search all enabled sources")
    se.add_argument("--profile", help="use a named profile from data/profiles/")
    se.add_argument("--limit", type=int, default=20, help="max listings to print")
    se.add_argument("--html", action="store_true",
                    help="also generate an HTML report and open it")
    se.set_defaults(func=cmd_search)

    sh = sub.add_parser("show", help="print the current saved profile")
    sh.set_defaults(func=cmd_show)

    rp = sub.add_parser("report", help="render the latest search results "
                                       "as an HTML page with insights")
    rp.add_argument("--no-open", action="store_true",
                    help="just write the file, don't open the browser")
    rp.set_defaults(func=cmd_report)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
