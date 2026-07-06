# CLAUDE.md — Sri Lanka Property Finder

Instructions for Claude Code (or any coding agent) working on this project.
Read this file fully before writing any code or answering property queries.

---

## 1. What this project is

A property-search assistant that helps a user find **land, houses, and apartments in Sri Lanka only**.

The assistant does two jobs:

1. **Intake** — have a short conversation to learn what the user wants (area, budget, property type, and a few more details), and save that to a file so it can be reused.
2. **Search** — use the saved profile to look for matching listings across the main Sri Lankan property websites and return a clean, ranked shortlist with direct links.

This can be built as a CLI agent, a skill, or a small website. Start simple (a script + JSON profile) and grow from there.

---

## 2. How the assistant should behave

### Intake conversation
When the user starts a new search, ask the questions in **Section 3** one topic at a time — do not dump all questions at once. Skip any question the user has already answered. Confirm the collected profile back to the user before searching.

If the user says "same as last time" or similar, load the most recent saved profile instead of re-asking.

### Rules
- **Sri Lanka only.** Never return or suggest listings outside Sri Lanka. If a source returns a non-SL result, drop it.
- **Always show the source and a working link** for every listing. Never invent a listing, price, or URL.
- **Prices are in LKR** unless the user explicitly asks for another currency. Show LKR and note if an approximate USD is added.
- **Be honest about coverage.** If a source couldn't be searched (e.g. blocked, no results, site down), say so rather than pretending it returned nothing.
- Keep results **de-duplicated** — the same property is often posted on multiple sites and by multiple agents.

---

## 3. Questions to collect (the search profile)

Ask these during intake. The first three are required; the rest are optional but improve results.

**Required**
1. **Property type** — land / house / apartment (allow more than one).
2. **Purpose** — buy or rent.
3. **Area** — district, city, or town (e.g. Colombo 5, Nugegoda, Kandy, Galle). Allow multiple areas.

**Recommended**
4. **Budget** — min and max in LKR.
5. **Size** — perches (land), square feet (house/apartment), or number of bedrooms/bathrooms.
6. **Furnishing** — furnished / semi-furnished / unfurnished (for houses & apartments).
7. **Must-haves** — parking, garden, sea view, gated community, near a main road, near school/hospital, etc.
8. **Deal-breakers** — anything to exclude.
9. **Timeline** — how soon they want to move / buy.
10. **Contact preference** — how they want to be shown results (just links, or a summary table).

Store the answers in `data/search-profile.json` (schema in Section 5).

---

## 4. Where to search (Sri Lankan sources)

None of these offer a public search API, so treat them as **web sources**: fetch/search the public pages, parse listings, and always keep the original listing URL. Respect each site's `robots.txt` and rate limits (see Section 7).

**Primary (search these first — highest listing volume)**
- **ikman.lk** — `https://ikman.lk/en/ads/sri-lanka/property` — largest classified site in Sri Lanka; huge volume of houses, land, and apartments; supports Sinhala and English. Best single source.
- **LankaPropertyWeb (LPW)** — `https://www.lankapropertyweb.com/` — the leading dedicated real-estate portal (since 2007); strong for apartments and houses, includes floor plans on many listings.

**Secondary (search for extra coverage)**
- **house.lk** — `https://house.lk/` (formerly Lamudi.lk).
- **patpat.lk** — `https://patpat.lk/en/sri-lanka/property`.
- **CeylonProperty.lk** — `https://ceylonproperty.lk/`.
- **LankaLand.lk** — `https://lankaland.lk/`.

**Developer / agency sites (for new builds & land developments)**
- **Prime Lands** — `https://www.primelands.lk/`
- **Home Lands Holdings** — `https://www.homelands.lk/`

Add new sources to `config/sources.json` (Section 5) rather than hard-coding URLs in logic.

### Facebook Marketplace — important
There is **no public API and no API keys** available for *searching or reading* Marketplace listings.
- Marketplace is deliberately excluded from Meta's Graph API; Meta does not open this data to third parties.
- The "Marketplace Partner" APIs that exist are for **approved sellers to list items**, not for buyers to search — they will not help here and require Meta partner approval.
- The only ways to get Marketplace data are (a) a person browsing manually, or (b) scraping public listings, which **violates Facebook's Terms of Service**, breaks frequently when the UI changes, and can get IPs/accounts blocked.

**Default behaviour:** do **not** scrape Facebook. Instead, if the user wants Marketplace results, generate a ready-to-click Marketplace search URL pre-filled with their area, budget, and property type, and let the user browse it themselves. Only revisit automated Facebook access if the user explicitly accepts the ToS and reliability risks — and document that decision.

---

## 5. Data files

Keep all state in flat files (JSON) so nothing depends on a database. Suggested layout:

```
/data
  search-profile.json     # the current user's requirements
  /profiles               # optional: named/saved profiles for reuse
  /results                # saved search outputs, timestamped
/config
  sources.json            # the list of sites to search + per-site settings
```

**`data/search-profile.json`**
```json
{
  "propertyTypes": ["house", "apartment"],
  "purpose": "buy",
  "areas": ["Nugegoda", "Colombo 5"],
  "budgetLKR": { "min": 20000000, "max": 45000000 },
  "size": { "bedrooms": 3, "bathrooms": 2, "perches": null, "sqft": null },
  "furnishing": "any",
  "mustHaves": ["parking", "near main road"],
  "dealBreakers": ["ground floor"],
  "timeline": "3 months",
  "createdAt": "2026-07-06T00:00:00Z"
}
```

**`config/sources.json`**
```json
[
  {
    "id": "ikman",
    "name": "ikman.lk",
    "baseUrl": "https://ikman.lk/en/ads/sri-lanka/property",
    "priority": 1,
    "enabled": true,
    "notes": "Largest classified site. Filter by category and location in the URL."
  },
  {
    "id": "lpw",
    "name": "LankaPropertyWeb",
    "baseUrl": "https://www.lankapropertyweb.com/",
    "priority": 1,
    "enabled": true,
    "notes": "Dedicated real-estate portal. Good for apartments."
  },
  {
    "id": "facebook",
    "name": "Facebook Marketplace",
    "baseUrl": "https://www.facebook.com/marketplace/",
    "priority": 5,
    "enabled": false,
    "notes": "No public API. Do not scrape. Generate a pre-filled search URL for the user instead."
  }
]
```

Each result saved to `/data/results` should record: title, price (LKR), area, property type, source id, listing URL, and the timestamp it was fetched.

---

## 6. Suggested build order

1. **Profile intake** — script that asks the Section 3 questions and writes `search-profile.json`.
2. **One source end-to-end** — get ikman.lk working: build a search URL from the profile, fetch, parse listings, print a shortlist with links. Prove the whole loop on one site before adding more.
3. **Add LPW**, then the secondary sources, one at a time.
4. **De-duplication + ranking** — merge results, drop duplicates, sort by how well each matches the profile (area match, within budget, must-haves present).
5. **Output** — a clean summary (table or list) with source, price, area, and link. Optionally a small website UI on top of the same core logic.

Keep the core search logic separate from any UI so it works the same whether run as a CLI, a skill, or behind a website.

---

## 7. Technical & ethical guardrails

- **Respect `robots.txt`** and each site's Terms of Service. When in doubt, prefer official/public search URLs over scraping.
- **Rate-limit** requests (e.g. a short delay between fetches) and set a normal User-Agent. Do not hammer any site.
- **Cache** fetched pages briefly to avoid repeat requests during one search session.
- **Fail gracefully** — if a source errors or blocks, log it, skip it, and tell the user which sources were and weren't searched.
- **Never fabricate** listings, prices, or URLs. Only report what was actually fetched.
- **Store no secrets in code.** If any source ever needs credentials, read them from environment variables, never commit them.
- **Currency:** treat all Sri Lankan prices as LKR. If converting to USD, label it "approx." and note the rate/date.

---

## 8. Coding conventions

- Prefer a single language for the project (Python or Node are both fine); pick one and stay consistent.
- Small, focused modules: `intake`, `sources/<siteId>`, `dedupe`, `rank`, `output`.
- All site-specific logic lives under `sources/` so adding a site is a self-contained change.
- Write functions that take the profile object as input and return normalized listing objects, so every source produces the same shape of data.
- Add a short comment at the top of each source module noting the site's structure and any parsing quirks, since these sites change their markup over time.

---

*Scope reminder: Sri Lanka properties only. Be accurate, cite the source and link for every listing, and be upfront about what could and couldn't be searched.*
