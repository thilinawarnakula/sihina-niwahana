# How to Run — Sihina Niwahana (Sri Lanka Property Finder)

A CLI assistant that finds **land, houses, and apartments in Sri Lanka only**.
This guide covers everything needed to run it.

## Requirements

- **Python 3** (3.8 or newer; the project is tested on 3.13)
- Nothing else — the project uses only the Python standard library.
  **No packages to install, no `.env` files, no API keys or tokens.**

## Quick start

```bash
cd /Users/thilinawarnakulasuriya/github/sihina-niwahana

# 1. Set up your search (short Q&A, one topic at a time)
python3 propertyfinder.py intake

# 2. Search all enabled sources with the saved profile
python3 propertyfinder.py search

# 3. View the currently saved profile any time
python3 propertyfinder.py show
```

"Same as last time" — just run `search` again; it reuses the saved profile
from `data/search-profile.json`.

## Commands in detail

### `intake` — collect your requirements

Interactive mode asks about: property type (land/house/apartment), buy or
rent, areas, budget in LKR, size (bedrooms/perches/sqft), furnishing,
must-haves, deal-breakers, and timeline. The first three are required, the
rest can be skipped with Enter. The profile is confirmed back to you before
saving.

Scripted mode (no prompts) — useful for repeat searches:

```bash
python3 propertyfinder.py intake \
  --type house --type apartment \
  --purpose buy \
  --area Nugegoda --area "Colombo 5" \
  --min 20m --max 45m \
  --bedrooms 3 \
  --must-have parking \
  --yes
```

| Flag | Meaning |
|---|---|
| `--type` | `land`, `house`, or `apartment` (repeat for more than one) |
| `--purpose` | `buy` or `rent` |
| `--area` | district/city/town (repeat for more than one) |
| `--min` / `--max` | budget in LKR; accepts `45000000`, `45m`, `450k` |
| `--bedrooms` | minimum bedrooms |
| `--must-have` / `--exclude` | keywords to favour / penalize (repeatable) |
| `--name` | also save as a named profile in `data/profiles/` |
| `--yes` | save without asking the remaining questions |

### `search` — run the search

```bash
python3 propertyfinder.py search                 # uses the saved profile
python3 propertyfinder.py search --profile NAME  # uses data/profiles/NAME.json
python3 propertyfinder.py search --limit 30      # print more results (default 20)
```

### `show` — print the saved profile

```bash
python3 propertyfinder.py show
```

## What you get (the outcome)

- A **ranked shortlist** in the terminal: title, price (LKR, exactly as the
  site displays it), area, property type, bedrooms, source site, and a
  direct working link to the original listing.
- Duplicates across sites are merged and marked, e.g. `(also on: houselk)`.
- A **coverage report**: which sites were searched, how many listings each
  returned, and which sites could not be searched and why.
- **Browse-yourself links** for sites that can't be searched automatically
  (Facebook Marketplace, patpat.lk, CeylonProperty.lk), pre-filled with your
  criteria where possible.
- The full result set saved to `data/results/results-<timestamp>.json`.

## Where it searches

| Source | Coverage |
|---|---|
| ikman.lk | automatic — largest classified site |
| LankaPropertyWeb | automatic — leading real-estate portal |
| house.lk | automatic — shares LPW's backend, deduped by listing ID |
| LankaLand.lk | automatic — smaller inventory |
| patpat.lk | manual link (robots.txt forbids crawling) |
| CeylonProperty.lk | manual link (robots.txt forbids its search pages) |
| Facebook Marketplace | manual link (no public API; scraping violates ToS) |

Enable, disable, or reprioritize sources in `config/sources.json`.

## Tips & troubleshooting

- **Unknown area?** If a source reports `unknown area '<name>' — not
  searched`, add the town to `finder/locations.py` (city → district map).
- **Prices**: all LKR. Listings priced "per perch" or with no stated price
  are kept but can't be budget-filtered, so they rank lower.
- **Rate limiting**: requests are spaced 1.5 s apart and cached for
  15 minutes (`data/.cache/`), so re-running a search right away is fast
  and doesn't re-hit the sites.
- **A source is down or blocked?** The search continues with the rest and
  tells you what was skipped — results never silently omit a source.
