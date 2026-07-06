"""Tests for the two core behaviours of the search:

  1. DIFFERENT preferences -> different pages fetched and different results.
  2. SAME preferences      -> identical (deterministic) results.

Everything runs offline: network fetches are replaced with canned pages.

Run:  python3 -m unittest discover tests -v
"""

import unittest
from unittest import mock

from finder.rank import rank
from finder.dedupe import dedupe
from finder.sources import ikman, lpw, houselk


# ---------------------------------------------------------------- fixtures

def ikman_page(ads):
    """Minimal ikman page: listings embedded as window.initialData JSON."""
    import json
    data = {"serp": {"ads": {"data": {"ads": ads}}}}
    return f"<html><script>window.initialData = {json.dumps(data)};</script></html>"


def ikman_ad(title, price, location, details="", slug="x"):
    return {"title": title, "price": price, "location": location,
            "details": details, "slug": slug, "shopName": ""}


def listing(title, price_lkr, area, ptype="land", perches=None,
            bedrooms=None, source="ikman", url=None, ref_id=None):
    return {"title": title, "priceLKR": price_lkr, "priceText": "",
            "area": area, "propertyType": ptype, "perches": perches,
            "bedrooms": bedrooms, "source": source, "details": "",
            "url": url or f"https://example.lk/{title.replace(' ', '-')}",
            "refId": ref_id, "fetchedAt": "2026-07-06T00:00:00Z"}


LAND_PROFILE = {
    "propertyTypes": ["land"], "purpose": "buy",
    "areas": ["Nugegoda", "Maharagama"],
    "budgetLKR": {"min": 20_000_000, "max": 30_000_000},
    "size": {"bedrooms": None, "bathrooms": None, "perches": 8, "sqft": None},
    "mustHaves": [], "dealBreakers": [],
}

RENT_PROFILE = {
    "propertyTypes": ["apartment"], "purpose": "rent",
    "areas": ["Colombo 5"],
    "budgetLKR": {"min": None, "max": 300_000},
    "size": {"bedrooms": 2, "bathrooms": None, "perches": None, "sqft": None},
    "mustHaves": ["furnished"], "dealBreakers": [],
}


# ------------------------------------------------- case 1: different prefs

class DifferentPreferencesFetchDifferentPages(unittest.TestCase):
    """Preferences decide WHICH site pages are downloaded."""

    def fetched_urls(self, module, profile):
        urls = []

        def fake_fetch(url):
            urls.append(url)
            return ikman_page([])  # empty page; we only care about the URLs

        with mock.patch.object(module, "fetch", fake_fetch):
            module.search(profile)
        return urls

    def test_ikman_urls_differ_by_preference(self):
        land_urls = self.fetched_urls(ikman, LAND_PROFILE)
        rent_urls = self.fetched_urls(ikman, RENT_PROFILE)

        self.assertIn("https://ikman.lk/en/ads/nugegoda/land-for-sale", land_urls)
        self.assertIn("https://ikman.lk/en/ads/maharagama/land-for-sale", land_urls)
        self.assertIn("https://ikman.lk/en/ads/colombo-5/apartment-rentals", rent_urls)
        # not a single page overlaps between the two searches
        self.assertFalse(set(land_urls) & set(rent_urls))

    def test_lpw_urls_differ_by_preference(self):
        def urls_for(profile):
            urls = []
            with mock.patch.object(lpw, "fetch", lambda u: (urls.append(u), "<html></html>")[1]):
                lpw.search(profile)
            return urls

        land_urls = urls_for(LAND_PROFILE)
        rent_urls = urls_for(RENT_PROFILE)
        self.assertIn("https://www.lankapropertyweb.com/land/sale-Western_Nugegoda-all.html",
                      land_urls)
        self.assertIn("https://www.lankapropertyweb.com/rentals/lease-Colombo+All_Colombo+5"
                      "-Apartment.html", rent_urls)
        self.assertFalse(set(land_urls) & set(rent_urls))

    def test_houselk_unknown_area_is_reported_not_guessed(self):
        profile = dict(LAND_PROFILE, areas=["Atlantis"])
        with mock.patch.object(houselk, "fetch", lambda u: "<html></html>"):
            res = houselk.search(profile)
        self.assertEqual(res["searched"], [])
        self.assertTrue(any("unknown area" in e for e in res["errors"]))


class DifferentPreferencesRankDifferently(unittest.TestCase):
    """From the SAME pool of listings, different preferences pick and order
    different results (budget filter, perch/bedroom scoring)."""

    POOL = [
        listing("8P land Embuldeniya", 23_200_000, "Nugegoda", perches=8),
        listing("10P land Maharagama", 24_500_000, "Maharagama", perches=10),
        listing("5P land Nugegoda", 15_000_000, "Nugegoda", perches=5),
        listing("Luxury 20P land Colombo 7", 160_000_000, "Colombo 7", perches=20),
        listing("2 bed apartment Colombo 5", 230_000, "Colombo 5",
                ptype="apartment", bedrooms=2),
    ]

    def test_budget_filter_changes_what_survives(self):
        results = rank([dict(l) for l in self.POOL], LAND_PROFILE)
        titles = [l["title"] for l in results]
        # 160M listing is >15% over the 30M budget -> dropped entirely
        self.assertNotIn("Luxury 20P land Colombo 7", titles)
        # in-budget, in-area, >=8 perches listings win
        self.assertEqual(titles[0], "8P land Embuldeniya")

    def test_different_profiles_different_top_result(self):
        land_top = rank([dict(l) for l in self.POOL], LAND_PROFILE)[0]["title"]
        rent_top = rank([dict(l) for l in self.POOL], RENT_PROFILE)[0]["title"]
        self.assertNotEqual(land_top, rent_top)
        self.assertEqual(rent_top, "2 bed apartment Colombo 5")

    def test_perch_minimum_demotes_small_plots(self):
        results = rank([dict(l) for l in self.POOL], LAND_PROFILE)
        titles = [l["title"] for l in results]
        # the 5-perch plot is below the 8-perch minimum -> ranks below both
        # plots that meet it
        self.assertGreater(titles.index("5P land Nugegoda"),
                           titles.index("10P land Maharagama"))


# ---------------------------------------------------- case 2: same prefs

class SamePreferencesSameResults(unittest.TestCase):
    """Identical input -> identical output, every time (no randomness)."""

    def test_rank_is_deterministic(self):
        pool = DifferentPreferencesRankDifferently.POOL
        run1 = rank([dict(l) for l in pool], LAND_PROFILE)
        run2 = rank([dict(l) for l in pool], LAND_PROFILE)
        self.assertEqual([l["title"] for l in run1], [l["title"] for l in run2])
        self.assertEqual([l["score"] for l in run1], [l["score"] for l in run2])

    def test_full_source_run_is_deterministic(self):
        page = ikman_page([
            ikman_ad("Land A", "Rs 2,900,000 per perch", "Nugegoda", "8.0 perches", "a"),
            ikman_ad("Land B", "Rs 25,000,000", "Nugegoda", "10.0 perches", "b"),
        ])
        with mock.patch.object(ikman, "fetch", lambda u: page):
            run1 = ikman.search(LAND_PROFILE)
            run2 = ikman.search(LAND_PROFILE)
        strip = lambda res: [{k: v for k, v in l.items() if k != "fetchedAt"}
                             for l in res["listings"]]
        self.assertEqual(strip(run1), strip(run2))
        # and the per-perch price was converted to a comparable total
        self.assertEqual(run1["listings"][0]["priceLKR"], 23_200_000)


# ------------------------------------------------------- supporting logic

class DedupeBehaviour(unittest.TestCase):
    def test_same_backend_id_is_merged(self):
        a = listing("Nice house", 21_000_000, "Nugegoda", source="lpw",
                    url="https://lpw.example/1", ref_id="lpw-123")
        b = listing("Nice house for sale", 21_000_000, "Nugegoda", source="houselk",
                    url="https://houselk.example/1", ref_id="lpw-123")
        merged = dedupe([a, b])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["alsoOn"], ["houselk"])

    def test_truncated_title_same_price_is_merged(self):
        a = listing("(NAR676) Fully Furnished Apartment for Rent in Kirulapone",
                    230_000, "Colombo 5", source="ikman")
        b = listing("(NAR676) Fully Furnished Apartment for Rent i...",
                    230_000, "Colombo 5", source="lpw")
        self.assertEqual(len(dedupe([a, b])), 1)

    def test_different_listings_are_kept(self):
        a = listing("8P land Embuldeniya", 23_200_000, "Nugegoda")
        b = listing("10P land Maharagama", 24_500_000, "Maharagama")
        self.assertEqual(len(dedupe([a, b])), 2)


if __name__ == "__main__":
    unittest.main()
