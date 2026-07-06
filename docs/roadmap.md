# Roadmap — feature ideas for later

Ideas collected as of 2026-07-06, roughly ordered by value-for-effort within
each group. Nothing here is committed work; it's a menu. Items marked ⚖️ have
a legal/ethical constraint to respect first (robots.txt / site ToS — see
CLAUDE.md section 7, which always wins).

## Quick wins (hours each)

- **Pagination** — every source currently reads only page 1 (~25–30 listings
  per page). Following "next page" links (where robots.txt allows) would
  roughly triple coverage. house.lk disallows `/*page*`, so skip it there.
- **"New since last search"** — remember previously seen listing URLs
  (a small JSON file locally / localStorage on the web) and badge or filter
  listings you haven't seen before.
- **Sort & refine controls in the web UI** — client-side re-sort (price ↑↓,
  newest, score) and quick filters (only with price, only with photos,
  per-source) without re-searching.
- **Approx. USD prices** — show "≈ $86,000" next to LKR, labelled with the
  rate and date, per the CLAUDE.md currency rule.
- **More towns in the location map** — `finder/locations.py` covers ~100
  places; extend as unknown-area errors appear in real use.
- **CI** — GitHub Action that runs `python3 -m unittest discover tests` on
  every push. The suite is offline and takes <1s, so this is nearly free.

## Search coverage (days each)

- **Developer/agency sites** — Prime Lands and Home Lands (named in
  CLAUDE.md) for new builds and land developments; each is one new module
  in `finder/sources/` + a `config/sources.json` entry.
- **Listing photos** — both ikman and LPW expose thumbnail URLs in the data
  we already parse; carry them through and show them as card images in the
  web UI and HTML report.
- **Detail-page enrichment for the top N results** — fetch the full ad page
  for, say, the top 10 to pull land size, floor area, and full description
  when the search card lacks them. Costs ~1 extra request per enriched
  listing, so keep N small and cached.
- **Sinhala support** — ikman serves Sinhala pages (`/si/ads/...`); the
  intake chat could accept Sinhala answers with a small keyword map.
- ⚖️ **patpat.lk / CeylonProperty.lk automation** — blocked today by their
  robots.txt. Re-check occasionally; if they open up, each becomes a normal
  source module. Until then they stay manual links.

## Alerts & automation (days)

- **Saved-search email alerts** — re-run a saved profile on a schedule and
  email only the new listings. Locally: `cron` + the existing CLI. On
  Netlify: a Scheduled Function + the existing mail function. Needs the
  "seen URLs" memory from the quick-wins list.
- **Telegram/WhatsApp notification** — same trigger, different channel;
  Telegram's bot API is free and simple, WhatsApp requires Meta Business
  API approval (heavier).
- **Parser health monitoring** — a scheduled run against one known-good
  page per site that alerts when a parser suddenly returns 0 listings
  (i.e. the site changed its markup). The coverage report already detects
  this per-search; this makes it proactive.

## Web app & accounts (days–weeks)

- **Saved profiles per user** — store each signed-in user's preferences in
  Firestore (the project deliberately stores nothing today; this is an
  explicit opt-in change). Enables "welcome back, run your usual search?".
- **Favourites / shortlist with notes** — star listings, add "visited,
  too close to main road" notes, compare side by side. Firestore again.
- **Map view** — plot results on a map of Colombo/Sri Lanka. Listings
  rarely carry coordinates, so this needs geocoding the area names
  (coarse but still useful).
- **Shareable result links** — encode the profile in the URL query string
  so a search can be sent to a spouse/agent; they click and re-run it.
- **PWA / mobile polish** — manifest + service worker so the Netlify site
  installs as a phone app; the UI is already responsive.

## Insights & analysis (weeks, needs data over time)

- **Price-per-perch benchmarks** — we already compute per-perch prices;
  aggregating them per suburb per search gives "Nugegoda median:
  Rs 2.9M/perch — this listing is 15% below market".
- **Price history** — persist anonymised (title-hash, price, date) rows
  from each search to see asking-price trends per area over months.
- **Mortgage / affordability calculator** — LKR loan rates, monthly payment
  next to each listing.

## Migration: React + NestJS, drop Python (planned direction, ~1 week)

Motivation: the maintainer works in JS/TS, not Python, and wants room to
scale. Feasibility is high because **the search engine already exists in
JavaScript** — `web/engine.js` is a verified 1:1 port of the Python parsers,
dedupe and rank (identical results on the same pages). The migration moves
code, it doesn't rewrite the hard part.

**Target stack**

| Today | After |
|---|---|
| `web/index.html` (vanilla JS) | React (Vite) + **Tailwind CSS** — components for chat intake, form, results |
| hand-written CSS (REA theme) | Tailwind utility classes; keep the realestate.com.au look by putting the design tokens (`#E4002B` red, charcoal `#2E3A44`, Inter font, radii, shadows) into `tailwind.config.js` `theme.extend` |
| `webapp.py` + Netlify Functions | NestJS: `SearchModule` (one service per source, ported from engine.js), `AuthModule` (Firebase Admin guard), `MailModule` (nodemailer) |
| `finder/*.py` + CLI | removed (or kept as reference until parity is proven) |
| Netlify static + functions | React stays on Netlify; NestJS runs on Render/Railway/Fly (Netlify cannot host a NestJS server) |
| `tests/test_search.py` | Jest — the assertions are language-neutral and port directly |

**Search performance: what changes and what doesn't**

- Language change alone: **no visible difference.** ~95% of a search is
  network wait + deliberate 1.2–1.5s politeness delays; parsing/ranking is
  milliseconds in any language.
- The wins come from the backend architecture the migration enables:
  1. **Parallel across sites, sequential within a site** — fetch
     ikman/LPW/house.lk/LankaLand simultaneously while staying polite
     per-host: ~60s → ~15s wall-clock.
  2. **Shared Redis cache** — one user's fetch serves every user for
     15 min; repeat searches become instant.
  3. **Job queue (BullMQ)** — pre-warm popular searches, run saved-search
     alerts off-peak.

**Scaling constraint (mandatory, not optional):** the property sites'
tolerance is per-server, not per-user. At scale, a **per-site request queue**
(one polite fetch stream per source, shared by all users) + the shared cache
is required — otherwise many users = hammering the sites = IP bans and a
CLAUDE.md guardrail violation.

**Suggested order:** NestJS backend with engine.js dropped in (1–2 days) →
React + Tailwind frontend, porting the UI and chat script 1:1 with the REA
tokens in the Tailwind theme (2–3 days) → Jest tests → per-site queue +
Redis cache → only then delete the Python tree.

## Explicitly out of scope (per CLAUDE.md)

- Scraping Facebook Marketplace (ToS violation; stays a manual link).
- Ignoring robots.txt anywhere, ever.
- Fabricating listings, prices, or URLs.
