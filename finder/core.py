"""Core search orchestration shared by the CLI and the web UI.

Runs every enabled source from config/sources.json against a profile and
returns one payload: ranked listings, per-source coverage, and manual
browse links. Saving to disk is the caller's choice (the web UI keeps
nothing, per its no-history design).
"""

import json
from datetime import datetime, timezone

from . import SOURCES_PATH
from .dedupe import dedupe
from .rank import rank
from .sources import (ikman, lpw, houselk, lankaland, patpat,
                      ceylonproperty, facebook)

SOURCE_MODULES = {
    "ikman": ikman,
    "lpw": lpw,
    "houselk": houselk,
    "lankaland": lankaland,
    "patpat": patpat,
    "ceylonproperty": ceylonproperty,
    "facebook": facebook,
}


def run_search(profile, on_progress=None):
    """Search all enabled sources. Returns a results payload dict.
    `on_progress(source_name)` is called before each source, if given."""
    sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = sorted([s for s in sources if s.get("enabled")],
                     key=lambda s: s.get("priority", 9))

    all_listings, coverage, manual_links = [], {}, []
    for src in sources:
        module = SOURCE_MODULES.get(src["id"])
        if module is None:
            coverage[src["name"]] = {"searched": [], "count": 0,
                                     "errors": [f"{src['id']}: enabled in config "
                                                f"but no parser implemented"]}
            continue
        if on_progress:
            on_progress(src["name"])
        try:
            res = module.search(profile)
        except Exception as e:  # a broken source must never kill the search
            coverage[src["name"]] = {"searched": [], "count": 0,
                                     "errors": [f"{src['id']}: unexpected error: {e}"]}
            continue
        all_listings.extend(res["listings"])
        manual_links.extend(res.get("manual") or [])
        coverage[src["name"]] = {"searched": res["searched"],
                                 "count": len(res["listings"]),
                                 "errors": res["errors"]}

    ranked = rank(dedupe(all_listings), profile)
    return {
        "savedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": profile,
        "listings": ranked,
        "coverage": coverage,
        "manualLinks": manual_links,
    }
