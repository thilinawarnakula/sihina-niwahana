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

### `report` — web page with insights

```bash
python3 propertyfinder.py search --html      # search, then open an HTML report
python3 propertyfinder.py report             # re-render the latest saved results
python3 propertyfinder.py report --no-open   # write the file without opening it
```

Generates a self-contained HTML page (no internet needed to view it) next to
the results JSON in `data/results/`. It shows summary tiles (matches, within
budget, lowest/median/highest price, duplicates merged), bar charts by
source, area, property type and bedrooms, a price-distribution histogram,
best-value picks (price per bedroom), the full clickable shortlist, and the
coverage report.

## The website (`webapp.py`)

```bash
python3 webapp.py                      # open http://localhost:8765
APP_PASSWORD=secret python3 webapp.py  # same, but requires a password to log in
```

A small local web UI on the same search core. Set your preferences either
through the **guided chat** (asks one question at a time and fills the form
for you) or directly in the **form** — then hit Search. Results show summary
tiles, the clickable shortlist, coverage, and browse-yourself links.
By design the web UI stores **nothing** — no profiles, no search history.

**Email summary:** the "Send email" button emails the results (the same HTML
report the CLI makes). Configure it with environment variables before
starting the server — never put credentials in code:

```bash
export SMTP_USER="you@gmail.com"
export SMTP_PASS="your-gmail-app-password"   # Google Account -> Security ->
                                             # 2-Step Verification -> App passwords
python3 webapp.py
```

`SMTP_HOST`/`SMTP_PORT` default to Gmail (`smtp.gmail.com:587`); set them for
another provider. Without `SMTP_USER`/`SMTP_PASS` the button explains what to
set instead of failing silently.

## What you get (the outcome)

- A **ranked shortlist** in the terminal: title, price (LKR, exactly as the
  site displays it), area, property type, bedrooms, seller/agency name where
  the site provides it, source site, and a direct working link to the
  original listing. Phone numbers are click-to-reveal on the linked ad pages
  and are never scraped.
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
