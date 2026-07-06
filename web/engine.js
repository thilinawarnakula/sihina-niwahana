/* Sihina Niwahana — browser search engine (used on static hosting like
 * Netlify, where there is no Python backend).
 *
 * This is a JS port of finder/sources/*, finder/dedupe.py and finder/rank.py.
 * Pages are fetched through the /api/page proxy function (strict domain
 * allowlist, see netlify/functions/page.js) because the property sites
 * don't send CORS headers. Parsing quirks are documented in the Python
 * modules — keep the two in sync when a site changes its markup.
 *
 * Nothing is stored anywhere: the search runs in your browser tab.
 */
(function () {
  "use strict";

  // city: [district, LPW province label] — generated from finder/locations.py
  const LOCATIONS = {"colombo":["colombo","Western"],"nugegoda":["colombo","Western"],"dehiwala":["colombo","Western"],"mount lavinia":["colombo","Western"],"battaramulla":["colombo","Western"],"kottawa":["colombo","Western"],"maharagama":["colombo","Western"],"malabe":["colombo","Western"],"homagama":["colombo","Western"],"piliyandala":["colombo","Western"],"pannipitiya":["colombo","Western"],"moratuwa":["colombo","Western"],"rajagiriya":["colombo","Western"],"kotte":["colombo","Western"],"boralesgamuwa":["colombo","Western"],"athurugiriya":["colombo","Western"],"kaduwela":["colombo","Western"],"kolonnawa":["colombo","Western"],"kohuwala":["colombo","Western"],"kirulapone":["colombo","Western"],"padukka":["colombo","Western"],"avissawella":["colombo","Western"],"angoda":["colombo","Western"],"wellampitiya":["colombo","Western"],"nawinna":["colombo","Western"],"embuldeniya":["colombo","Western"],"udahamulla":["colombo","Western"],"negombo":["gampaha","Western"],"gampaha":["gampaha","Western"],"kadawatha":["gampaha","Western"],"wattala":["gampaha","Western"],"ja-ela":["gampaha","Western"],"kelaniya":["gampaha","Western"],"kiribathgoda":["gampaha","Western"],"ragama":["gampaha","Western"],"minuwangoda":["gampaha","Western"],"nittambuwa":["gampaha","Western"],"veyangoda":["gampaha","Western"],"seeduwa":["gampaha","Western"],"katunayake":["gampaha","Western"],"kalutara":["kalutara","Western"],"panadura":["kalutara","Western"],"wadduwa":["kalutara","Western"],"horana":["kalutara","Western"],"beruwala":["kalutara","Western"],"aluthgama":["kalutara","Western"],"bandaragama":["kalutara","Western"],"matugama":["kalutara","Western"],"kandy":["kandy","Central"],"peradeniya":["kandy","Central"],"katugastota":["kandy","Central"],"pilimatalawa":["kandy","Central"],"kundasale":["kandy","Central"],"matale":["matale","Central"],"dambulla":["matale","Central"],"nuwara eliya":["nuwara eliya","Central"],"hatton":["nuwara eliya","Central"],"galle":["galle","Southern"],"hikkaduwa":["galle","Southern"],"unawatuna":["galle","Southern"],"ahangama":["galle","Southern"],"ambalangoda":["galle","Southern"],"bentota":["galle","Southern"],"karapitiya":["galle","Southern"],"matara":["matara","Southern"],"weligama":["matara","Southern"],"mirissa":["matara","Southern"],"dickwella":["matara","Southern"],"hambantota":["hambantota","Southern"],"tangalle":["hambantota","Southern"],"tissamaharama":["hambantota","Southern"],"beliatta":["hambantota","Southern"],"jaffna":["jaffna","North"],"chavakachcheri":["jaffna","North"],"trincomalee":["trincomalee","Eastern"],"batticaloa":["batticaloa","Eastern"],"ampara":["ampara","Eastern"],"arugam bay":["ampara","Eastern"],"kurunegala":["kurunegala","North West"],"kuliyapitiya":["kurunegala","North West"],"narammala":["kurunegala","North West"],"puttalam":["puttalam","North West"],"chilaw":["puttalam","North West"],"wennappuwa":["puttalam","North West"],"marawila":["puttalam","North West"],"anuradhapura":["anuradhapura","North Central"],"polonnaruwa":["polonnaruwa","North Central"],"badulla":["badulla","Uva"],"bandarawela":["badulla","Uva"],"ella":["badulla","Uva"],"haputale":["badulla","Uva"],"monaragala":["monaragala","Uva"],"wellawaya":["monaragala","Uva"],"ratnapura":["ratnapura","Sabaragamuwa"],"embilipitiya":["ratnapura","Sabaragamuwa"],"balangoda":["ratnapura","Sabaragamuwa"],"kegalle":["kegalle","Sabaragamuwa"],"mawanella":["kegalle","Sabaragamuwa"]};

  const FETCH_DELAY_MS = 1200; // politeness gap between page fetches

  const slug = (s, sep = "-") =>
    s.trim().toLowerCase().replace(/[^a-z0-9]+/g, sep).replace(new RegExp(`^\\${sep}+|\\${sep}+$`, "g"), "");

  function lookup(area) {
    const a = area.trim().toLowerCase().replace(/\s+/g, " ");
    if (/^colombo\s*\d{1,2}$/.test(a))
      return { city: "colombo " + a.match(/\d+/)[0], district: "colombo", province: "Western" };
    const hit = LOCATIONS[a];
    return hit ? { city: a, district: hit[0], province: hit[1] } : null;
  }

  const nowIso = () => new Date().toISOString().replace(/\.\d+Z$/, "Z");

  /* ---------- ikman.lk ---------- */
  const IKMAN_CATEGORY = {
    "house,buy": "houses-for-sale", "house,rent": "house-rentals",
    "apartment,buy": "apartments-for-sale", "apartment,rent": "apartment-rentals",
    "land,buy": "land-for-sale", "land,rent": "land-for-rent",
  };

  function extractInitialData(html) {
    const i = html.indexOf("window.initialData");
    if (i < 0) throw new Error("window.initialData not found (layout changed?)");
    const start = html.indexOf("{", i);
    let depth = 0, inStr = false, esc = false;
    for (let j = start; j < html.length; j++) {
      const c = html[j];
      if (inStr) {
        if (esc) esc = false;
        else if (c === "\\") esc = true;
        else if (c === '"') inStr = false;
      } else if (c === '"') inStr = true;
      else if (c === "{") depth++;
      else if (c === "}" && --depth === 0)
        return JSON.parse(html.slice(start, j + 1));
    }
    throw new Error("unbalanced initialData JSON");
  }

  function parseIkman(html, ptype, purpose) {
    const data = extractInitialData(html);
    const ads = (((data.serp || {}).ads || {}).data || {}).ads || [];
    const out = [];
    for (const ad of ads) {
      if (ad.isJobAd) continue;
      const details = ad.details || "";
      const beds = /Bedrooms:\s*(\d+)/.exec(details);
      const per = /([\d.]+)\s*perch/i.exec(details);
      const perches = per ? parseFloat(per[1]) : null;
      let priceText = (ad.price || "").trim();
      const m = /Rs\s*([\d,]+)/.exec(priceText);
      let priceLKR = null;
      if (m) {
        const v = parseInt(m[1].replace(/,/g, ""), 10);
        const low = priceText.toLowerCase();
        if (low.includes("perch")) {
          if (perches) {
            priceLKR = Math.round(v * perches);
            priceText += ` (≈ Rs ${priceLKR.toLocaleString()} total for ${perches}P)`;
          }
        } else if (low.includes("month")) {
          if (purpose === "rent") priceLKR = v;
        } else priceLKR = v;
      }
      out.push({
        contact: (ad.shopName || "").trim() || null,
        title: (ad.title || "").trim(),
        priceLKR, priceText, perches,
        area: (ad.location || "").trim(),
        propertyType: ptype, source: "ikman",
        url: "https://ikman.lk/en/ad/" + (ad.slug || ""),
        bedrooms: beds ? parseInt(beds[1], 10) : null,
        details, fetchedAt: nowIso(),
      });
    }
    return out;
  }

  /* ---------- shared "Rs. 23.63M" price parser (LPW & house.lk) ---------- */
  function parseRsM(text) {
    const t = (text || "").trim();
    if (/per\s*(perch|sq)/i.test(t)) return null;
    const m = /Rs\.?\s*([\d,]+(?:\.\d+)?)\s*(m|million|k)?/i.exec(t);
    if (!m) return null;
    let v = parseFloat(m[1].replace(/,/g, ""));
    const u = (m[2] || "").toLowerCase();
    if (u === "m" || u === "million") v *= 1e6;
    else if (u === "k") v *= 1e3;
    return Math.round(v);
  }

  /* ---------- LankaPropertyWeb ---------- */
  function parseLpw(html, ptype) {
    const out = [];
    for (const chunkRaw of html.split('<article class="listing-item"').slice(1)) {
      const chunk = chunkRaw.slice(0, 6000);
      const link = /href="(\/(?:sale|rentals|land)\/property_details-\d+\.html)"/.exec(chunk);
      const title = /listing-title">\s*(?:<!--[\s\S]*?-->\s*)?<a href="[^"]+">([\s\S]*?)<\/a>/.exec(chunk);
      if (!link || !title) continue;
      const price = /class="listing-price">\s*([^<]+)/.exec(chunk);
      const loc = /class="location">([^<]*)</.exec(chunk);
      const beds = /bed icon[\s\S]*?class="count">(\d+)/.exec(chunk);
      const addr = /listing-address">[\s\S]*?<\/i>\s*([\s\S]*?)\s*<\/h5>/.exec(chunk);
      const titleText = title[1].replace(/\s+/g, " ").trim();
      const addrText = addr ? addr[1].replace(/\s+/g, " ").trim() : "";
      let priceText = price ? price[1].trim() : "";
      const perPerch = /span_psf">\s*Per\s*Perch/i.test(chunk);
      const per = /([\d.]+)\s*perch/i.exec(titleText + " " + addrText);
      const perches = per ? parseFloat(per[1]) : null;
      let priceLKR = parseRsM(priceText);
      if (perPerch && priceLKR) {
        if (perches) {
          priceLKR = Math.round(priceLKR * perches);
          priceText += ` per perch (≈ Rs ${priceLKR.toLocaleString()} total for ${perches}P)`;
        } else { priceText += " per perch"; priceLKR = null; }
      }
      const ref = /property_details-(\d+)/.exec(link[1]);
      out.push({
        refId: ref ? "lpw-" + ref[1] : null,
        title: titleText, priceLKR, priceText, perches,
        area: loc ? loc[1].trim() : addrText,
        propertyType: ptype, source: "lpw",
        url: "https://www.lankapropertyweb.com" + link[1],
        bedrooms: beds ? parseInt(beds[1], 10) : null,
        details: addrText, fetchedAt: nowIso(),
      });
    }
    return out;
  }

  /* ---------- house.lk ---------- */
  function parseHouselk(html, ptype) {
    const out = [];
    for (const chunkRaw of html.split('class="property_listing').slice(1)) {
      const chunk = chunkRaw.slice(0, 7000);
      const link = /href="(\/details\/[^"]+-(\d+)\/?)"/.exec(chunk);
      const title = /<h4>\s*<a href="[^"]+">\s*([\s\S]*?)\s*<\/a>/.exec(chunk);
      if (!link || !title) continue;
      const price = /listing_unit_price_wrapper">\s*([^<]+)/.exec(chunk);
      const loc = /action_tag_location_wrapper[^>]*>[\s\S]*?<\/span>([^<]*)</.exec(chunk);
      const titleText = title[1].replace(/\s+/g, " ").trim();
      let priceText = price ? price[1].trim() : "";
      const perPerch = /per\s*perch/i.test(chunk.slice(0, 2500));
      const per = /([\d.]+)\s*perch/i.exec(titleText);
      const perches = per ? parseFloat(per[1]) : null;
      let priceLKR = parseRsM(priceText);
      if (perPerch && priceLKR) {
        if (perches) {
          priceLKR = Math.round(priceLKR * perches);
          priceText += ` per perch (≈ Rs ${priceLKR.toLocaleString()} total for ${perches}P)`;
        } else { priceText += " per perch"; priceLKR = null; }
      }
      out.push({
        refId: "lpw-" + link[2], // house.lk shares LPW's backend/IDs
        title: titleText, priceLKR, priceText, perches,
        area: loc ? loc[1].trim() : "",
        propertyType: ptype, source: "houselk",
        url: "https://house.lk" + link[1],
        bedrooms: null, details: "", fetchedAt: nowIso(),
      });
    }
    return out;
  }

  /* ---------- LankaLand ---------- */
  function parseLankaland(html, ptype) {
    const out = [];
    for (const chunkRaw of html.split("property-item search-listing-item").slice(1)) {
      const chunk = chunkRaw.slice(0, 6000);
      const link = /href="(https:\/\/www\.lankaland\.lk\/[^"]+)" class="full-link"/.exec(chunk);
      const title = /<h3>\s*([\s\S]*?)\s*<\/h3>/.exec(chunk);
      if (!link || !title) continue;
      const price = /LKR\s*[\d,]+(?:\.\d+)?/.exec(chunk);
      const city = /item city[\s\S]*?search-results\?city=[^"]*">\s*([^<]+?)\s*<\/a>/.exec(chunk);
      const district = /item district[\s\S]*?search-results\?district=[^"]*">\s*([^<]+?)\s*<\/a>/.exec(chunk);
      const priceText = price ? price[0] : "Negotiable";
      const pm = /LKR\s*([\d,]+(?:\.\d+)?)/i.exec(priceText);
      out.push({
        title: title[1].replace(/\s+/g, " ").trim(),
        priceLKR: pm ? Math.round(parseFloat(pm[1].replace(/,/g, ""))) : null,
        priceText,
        area: city ? city[1].trim() : (district ? district[1].trim() : ""),
        propertyType: ptype, source: "lankaland",
        url: link[1], bedrooms: null, perches: null,
        details: "", fetchedAt: nowIso(),
      });
    }
    return out;
  }

  /* ---------- task builder: which URLs to fetch ---------- */
  function buildTasks(profile) {
    const tasks = [], errors = [];
    const purpose = profile.purpose || "buy";
    for (const area of profile.areas || []) {
      const loc = lookup(area);
      for (const ptype of profile.propertyTypes || []) {
        // ikman: unknown areas fall back to the all-island page server-side 404 →
        // here we just try the slug; a 404 is reported in coverage.
        tasks.push({
          source: "ikman", name: "ikman.lk", ptype,
          url: `https://ikman.lk/en/ads/${slug(area)}/${IKMAN_CATEGORY[ptype + "," + purpose]}`,
          fallbackUrl: `https://ikman.lk/en/ads/sri-lanka/${IKMAN_CATEGORY[ptype + "," + purpose]}`,
          parse: (h) => parseIkman(h, ptype, purpose),
        });
        if (!loc) {
          errors.push(`lpw/houselk/lankaland: unknown area '${area}' — not searched`);
          continue;
        }
        const lpwLoc = /^colombo(\s*\d{1,2})?$/.test(area.trim().toLowerCase())
          ? "Colombo+All_" + (area.trim().toLowerCase() === "colombo" ? "Colombo"
              : area.trim().replace(/\b\w/g, (c) => c.toUpperCase()).replace(/ /g, "+"))
          : loc.province.replace(/ /g, "+") + "_" +
            loc.city.replace(/\b\w/g, (c) => c.toUpperCase()).replace(/ /g, "+");
        const lpwUrl = ptype === "land"
          ? `https://www.lankapropertyweb.com/land/${purpose === "rent" ? "lease" : "sale"}-${lpwLoc}-all.html`
          : purpose === "rent"
            ? `https://www.lankapropertyweb.com/rentals/lease-${lpwLoc}-${{house:"House",apartment:"Apartment"}[ptype]}.html`
            : `https://www.lankapropertyweb.com/forsale-${lpwLoc}-${{house:"House",apartment:"Apartment",land:"Land"}[ptype]}.html`;
        tasks.push({ source: "lpw", name: "LankaPropertyWeb", ptype, url: lpwUrl,
                     parse: (h) => parseLpw(h, ptype) });
        tasks.push({
          source: "houselk", name: "house.lk", ptype,
          url: `https://house.lk/${purpose === "rent" ? "rent" : "sale"}/${slug(loc.district)}/${slug(loc.city)}/${ptype}/`,
          parse: (h) => parseHouselk(h, ptype),
        });
        tasks.push({
          source: "lankaland", name: "LankaLand.lk", ptype,
          url: `https://www.lankaland.lk/search-results?category=${ptype}&city=${slug(loc.city)}&status=${purpose === "rent" ? "rent" : "sale"}`,
          parse: (h) => parseLankaland(h, ptype),
        });
      }
    }
    return { tasks, errors };
  }

  /* ---------- manual links (never scraped) ---------- */
  function manualLinks(profile) {
    const purpose = profile.purpose || "buy";
    const links = [
      { label: "patpat.lk property section (robots.txt disallows crawling — browse manually)",
        url: "https://patpat.lk/en/sri-lanka/property" },
      { label: "CeylonProperty.lk (robots.txt disallows its search pages — browse manually)",
        url: "https://ceylonproperty.lk/" },
    ];
    for (const area of profile.areas || [])
      for (const ptype of profile.propertyTypes || []) {
        const q = new URLSearchParams({ query: `${ptype} ${purpose === "rent" ? "for rent" : "for sale"} ${area}` });
        const b = profile.budgetLKR || {};
        if (b.min) q.set("minPrice", b.min);
        if (b.max) q.set("maxPrice", b.max);
        links.push({
          label: `Facebook Marketplace: ${ptype} ${purpose === "rent" ? "rentals" : "sales"} in ${area} (no public API)`,
          url: "https://www.facebook.com/marketplace/colombo/search?" + q,
        });
      }
    return links;
  }

  /* ---------- dedupe (port of finder/dedupe.py) ---------- */
  const normTitle = (t) => (t || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  function sameTitle(a, b) {
    a = normTitle(a); b = normTitle(b);
    if (!a || !b) return false;
    if (a === b) return true;
    const [s, l] = a.length <= b.length ? [a, b] : [b, a];
    return s.length >= 20 && l.startsWith(s);
  }
  function samePrice(a, b) {
    if (a == null || b == null) return a === b;
    return a === b || Math.abs(a - b) / Math.max(a, b) <= 0.02;
  }
  function dedupe(listings) {
    const kept = [], seen = new Set();
    for (const l of listings) {
      if (seen.has(l.url)) continue;
      let dup = null;
      for (const k of kept) {
        if ((l.refId && k.refId === l.refId) ||
            (sameTitle(k.title, l.title) && samePrice(k.priceLKR, l.priceLKR))) { dup = k; break; }
      }
      if (dup) {
        dup.alsoOn = dup.alsoOn || [];
        if (l.source !== dup.source && !dup.alsoOn.includes(l.source)) dup.alsoOn.push(l.source);
        continue;
      }
      seen.add(l.url); kept.push(l);
    }
    return kept;
  }

  /* ---------- rank (port of finder/rank.py) ---------- */
  function scoreListing(l, p) {
    let s = 0;
    const areas = (p.areas || []).map((a) => a.toLowerCase());
    const at = (l.area || "").toLowerCase();
    if (at && areas.some((a) => at.includes(a) || a.includes(at))) s += 3;
    const b = p.budgetLKR || {};
    if (l.priceLKR != null) {
      if ((b.min == null || l.priceLKR >= b.min) && (b.max == null || l.priceLKR <= b.max))
        s += b.min || b.max ? 3 : 1;
      else if (b.max != null && l.priceLKR > b.max) s -= 2;
    }
    const text = `${l.title} ${l.details || ""} ${l.area || ""}`.toLowerCase();
    for (const w of p.mustHaves || []) if (text.includes(w.toLowerCase())) s += 1;
    for (const w of p.dealBreakers || []) if (text.includes(w.toLowerCase())) s -= 4;
    const size = p.size || {};
    if (size.bedrooms && l.bedrooms && l.bedrooms >= size.bedrooms) s += 2;
    if (size.perches && l.perches) s += l.perches >= size.perches ? 2 : -1;
    return s;
  }
  function rank(listings, p) {
    const bmax = (p.budgetLKR || {}).max;
    const kept = listings.filter((l) => !(bmax && l.priceLKR && l.priceLKR > bmax * 1.15));
    for (const l of kept) l.score = scoreListing(l, p);
    kept.sort((a, b) => b.score - a.score || (a.priceLKR || 1e15) - (b.priceLKR || 1e15));
    return kept;
  }

  /* ---------- orchestrator ---------- */
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function runSearch(profile, fetchPage, onProgress) {
    const { tasks, errors } = buildTasks(profile);
    const coverage = {}, all = [];
    const cov = (name) => (coverage[name] =
      coverage[name] || { searched: [], count: 0, errors: [] });
    for (const e of errors) cov("area lookup").errors.push(e);

    for (let i = 0; i < tasks.length; i++) {
      const t = tasks[i];
      if (onProgress) onProgress(`Searching ${t.name} (${i + 1}/${tasks.length})…`);
      let html = null, used = t.url;
      try {
        html = await fetchPage(t.url);
      } catch (e) {
        if (t.fallbackUrl) {
          try { html = await fetchPage((used = t.fallbackUrl)); }
          catch (e2) { cov(t.name).errors.push(`${t.source}: ${e2.message}`); }
        } else cov(t.name).errors.push(`${t.source}: ${e.message}`);
      }
      if (html != null) {
        try {
          const listings = t.parse(html);
          cov(t.name).searched.push(used);
          cov(t.name).count += listings.length;
          all.push(...listings);
        } catch (e) {
          cov(t.name).errors.push(`${t.source}: parse failed: ${e.message}`);
        }
      }
      if (i < tasks.length - 1) await sleep(FETCH_DELAY_MS);
    }

    cov("patpat.lk").errors.push("patpat: not searched (robots.txt disallows all crawling)");
    cov("CeylonProperty.lk").errors.push("ceylonproperty: not searched (robots.txt disallows its search pages)");
    cov("Facebook Marketplace").errors.push("facebook: not searched (no public API; scraping violates ToS)");

    return {
      savedAt: nowIso(),
      profile,
      listings: rank(dedupe(all), profile),
      coverage,
      manualLinks: manualLinks(profile),
    };
  }

  window.SihinaEngine = { runSearch, buildTasks, parseIkman, parseLpw, parseHouselk, parseLankaland, dedupe, rank };
})();
