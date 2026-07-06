# Sri Lanka Property Finder

A CLI assistant that finds **land, houses, and apartments in Sri Lanka only**.
It collects your requirements in a short Q&A, saves them as a reusable profile,
then searches the main Sri Lankan property sites and returns a de-duplicated,
ranked shortlist with direct links.

Pure Python 3 standard library — nothing to install.

Full usage guide: [docs/how-to-run.md](docs/how-to-run.md)

## Quick start

```bash
# 1. Tell it what you want (interactive Q&A, saved to data/search-profile.json)
python3 propertyfinder.py intake

# 2. Search all enabled sources with the saved profile
python3 propertyfinder.py search

# "Same as last time" — just run search again; it reuses the saved profile.
python3 propertyfinder.py show          # see the current profile
```

Scripted intake (no prompts):

```bash
python3 propertyfinder.py intake --type house --type apartment --purpose buy \
  --area Nugegoda --area "Colombo 5" --min 20m --max 45m --bedrooms 3 \
  --must-have parking --yes --name colombo-house-hunt

python3 propertyfinder.py search --profile colombo-house-hunt --limit 15
```

## What it searches

| Source | Status | How |
|---|---|---|
| ikman.lk | automatic | path-based search pages, listings parsed from embedded JSON |
| LankaPropertyWeb | automatic | static `/forsale-…` and `/rentals/lease-…` pages |
| house.lk | automatic | `/{sale\|rent}/{district}/{city}/{type}/` pages; shares LPW's backend, so duplicates are removed by listing ID |
| LankaLand.lk | automatic | `/search-results?category=&city=&status=` (small inventory) |
| patpat.lk | manual link only | robots.txt disallows all crawling, so we don't |
| CeylonProperty.lk | manual link only | robots.txt disallows its listing-search pages, so we don't |
| Facebook Marketplace | manual link only | no public API; scraping violates ToS, so it prints a pre-filled search URL for you to browse |

Enable/disable or reprioritize sources in `config/sources.json`.
Every result shows its source and a direct link; coverage (what was and
wasn't searched, and why) is always reported. Prices are LKR as displayed
by the site. Requests are rate-limited (1.5 s), sent with a normal
User-Agent, cached for 15 minutes, and use only robots.txt-allowed URLs.

## Layout

```
propertyfinder.py        CLI entry (intake / search / show)
finder/
  intake.py              Q&A -> data/search-profile.json
  fetch.py               polite HTTP: rate limit, UA, short disk cache
  locations.py           city -> district/province lookup for URL building
  dedupe.py              cross-site duplicate removal (by shared listing ID,
                         URL, or title+price)
  rank.py                score & sort by profile match
  output.py              shortlist printing + data/results/*.json
  sources/
    ikman.py             site parser (structure notes in module docstring)
    lpw.py               site parser
    houselk.py           site parser (LPW-backed, dedupes via listing ID)
    lankaland.py         site parser
    patpat.py            manual browse link (robots.txt forbids crawling)
    ceylonproperty.py    manual browse link (robots.txt forbids search pages)
    facebook.py          Marketplace URL generator (never scrapes)
config/sources.json      source list + per-site settings
data/                    profiles, results, cache (flat JSON, no database)
```

Adding a site = one new module in `finder/sources/` returning the normalized
listing shape (see `finder/sources/__init__.py`) plus an entry in
`config/sources.json`.
