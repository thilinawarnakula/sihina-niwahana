"""Sri Lanka Property Finder — core package.

Scope: land, houses, and apartments in Sri Lanka only.
All state lives in flat JSON files under data/ (see CLAUDE.md section 5).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PROFILES_DIR = DATA_DIR / "profiles"
RESULTS_DIR = DATA_DIR / "results"
CACHE_DIR = DATA_DIR / ".cache"
CONFIG_DIR = ROOT / "config"
PROFILE_PATH = DATA_DIR / "search-profile.json"
SOURCES_PATH = CONFIG_DIR / "sources.json"

for d in (DATA_DIR, PROFILES_DIR, RESULTS_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)
