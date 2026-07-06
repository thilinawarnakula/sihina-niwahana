"""HTML report: turn a saved search result into a single-file web page.

Reads a results JSON from data/results/ and writes a self-contained HTML
page (inline CSS, no external assets, works offline) with the ranked
shortlist plus insights: price statistics, budget fit, breakdowns by
source/area/type, a price histogram, and best-value picks.
"""

import html
import json
import statistics

from . import RESULTS_DIR, SOURCES_PATH


def _source_names():
    """Map source id -> display name from config/sources.json."""
    try:
        return {s["id"]: s["name"]
                for s in json.loads(SOURCES_PATH.read_text(encoding="utf-8"))}
    except Exception:
        return {}


def _fmt_lkr(n):
    if n is None:
        return "—"
    if n >= 1_000_000:
        m = n / 1_000_000
        return f"Rs {m:,.1f}M".replace(".0M", "M")
    return f"Rs {n:,}"


def _esc(s):
    return html.escape(str(s or ""))


def _bar_rows(counter, total, color="#2f6f4f"):
    rows = []
    for label, count in sorted(counter.items(), key=lambda x: -x[1]):
        pct = 100 * count / max(total, 1)
        rows.append(
            f'<div class="bar-row"><span class="bar-label">{_esc(label)}</span>'
            f'<span class="bar-track"><span class="bar-fill" '
            f'style="width:{pct:.0f}%;background:{color}"></span></span>'
            f'<span class="bar-count">{count}</span></div>')
    return "\n".join(rows)


def _insights(listings, profile):
    prices = [l["priceLKR"] for l in listings if l.get("priceLKR")]
    budget = profile.get("budgetLKR") or {}
    bmin, bmax = budget.get("min"), budget.get("max")

    by_source, by_area, by_type, by_beds = {}, {}, {}, {}
    dup_count = 0
    for l in listings:
        by_source[l["source"]] = by_source.get(l["source"], 0) + 1
        if l.get("area"):
            by_area[l["area"]] = by_area.get(l["area"], 0) + 1
        by_type[l["propertyType"] or "?"] = by_type.get(l["propertyType"] or "?", 0) + 1
        if l.get("bedrooms"):
            key = f"{l['bedrooms']} bed"
            by_beds[key] = by_beds.get(key, 0) + 1
        dup_count += len(l.get("alsoOn") or [])

    in_budget = sum(1 for p in prices
                    if (bmin is None or p >= bmin) and (bmax is None or p <= bmax))

    # histogram over 6 buckets between min and max price
    hist = {}
    if len(prices) >= 2 and min(prices) < max(prices):
        lo, hi = min(prices), max(prices)
        step = (hi - lo) / 6
        for p in prices:
            i = min(int((p - lo) / step), 5)
            label = f"{_fmt_lkr(int(lo + i * step))}–{_fmt_lkr(int(lo + (i + 1) * step))}"
            hist[(i, label)] = hist.get((i, label), 0) + 1
        hist = {label: c for (_i, label), c in sorted(hist.items())}

    # best value: lowest price per bedroom (houses/apartments with both known)
    value = sorted((l for l in listings if l.get("priceLKR") and l.get("bedrooms")),
                   key=lambda l: l["priceLKR"] / l["bedrooms"])[:3]

    return {
        "count": len(listings),
        "priced": len(prices),
        "min": min(prices) if prices else None,
        "median": int(statistics.median(prices)) if prices else None,
        "max": max(prices) if prices else None,
        "in_budget": in_budget,
        "dup_count": dup_count,
        "by_source": by_source, "by_area": by_area,
        "by_type": by_type, "by_beds": by_beds,
        "hist": hist, "value": value,
    }


CSS = """
:root { --ink:#1c2b24; --mut:#5c6f66; --line:#dfe7e2; --bg:#f6f8f7;
        --card:#ffffff; --green:#2f6f4f; --amber:#a8721d; }
* { box-sizing:border-box; margin:0; }
body { font:15px/1.55 -apple-system,'Segoe UI',Roboto,sans-serif;
       color:var(--ink); background:var(--bg); padding:2rem 1rem; }
.wrap { max-width:960px; margin:0 auto; }
h1 { font-size:1.5rem; margin-bottom:.25rem; }
h2 { font-size:1.05rem; margin:2rem 0 .75rem; border-bottom:1px solid var(--line);
     padding-bottom:.4rem; }
.sub { color:var(--mut); margin-bottom:1.5rem; }
.tiles { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
         gap:.75rem; }
.tile { background:var(--card); border:1px solid var(--line); border-radius:10px;
        padding:.9rem 1rem; }
.tile b { display:block; font-size:1.35rem; }
.tile span { color:var(--mut); font-size:.82rem; }
.cols { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
        gap:1.5rem; }
.bar-row { display:flex; align-items:center; gap:.5rem; margin:.3rem 0; }
.bar-label { flex:0 0 40%; font-size:.85rem; overflow:hidden;
             text-overflow:ellipsis; white-space:nowrap; }
.bar-track { flex:1; background:var(--line); border-radius:4px; height:14px;
             overflow:hidden; }
.bar-fill { display:block; height:100%; border-radius:4px; }
.bar-count { flex:0 0 2.2em; text-align:right; font-size:.85rem;
             color:var(--mut); }
.listing { background:var(--card); border:1px solid var(--line);
           border-radius:10px; padding:.9rem 1.1rem; margin:.6rem 0; }
.listing .t { font-weight:600; }
.listing .t a { color:var(--ink); text-decoration:none; }
.listing .t a:hover { text-decoration:underline; }
.meta { color:var(--mut); font-size:.88rem; margin-top:.15rem; }
.price { color:var(--green); font-weight:700; }
.src { display:inline-block; background:var(--bg); border:1px solid var(--line);
       border-radius:5px; padding:0 .45em; font-size:.78rem; color:var(--mut); }
.badge { display:inline-block; background:#eaf3ee; color:var(--green);
         border-radius:5px; padding:0 .45em; font-size:.78rem; }
.cov li { margin:.25rem 0; } .cov .err { color:var(--amber); }
ul { padding-left:1.2rem; }
a { color:var(--green); }
.overflow { overflow-x:auto; }
footer { margin-top:2.5rem; color:var(--mut); font-size:.82rem; }
"""


def render(payload):
    profile = payload.get("profile") or {}
    listings = payload.get("listings") or []
    coverage = payload.get("coverage") or {}
    ins = _insights(listings, profile)
    budget = profile.get("budgetLKR") or {}

    title = (f"{'/'.join(profile.get('propertyTypes') or [])} to "
             f"{profile.get('purpose', '?')} in "
             f"{', '.join(profile.get('areas') or [])}")

    tiles = f"""
    <div class="tiles">
      <div class="tile"><b>{ins['count']}</b><span>matching listings</span></div>
      <div class="tile"><b>{ins['in_budget']}</b><span>within budget</span></div>
      <div class="tile"><b>{_fmt_lkr(ins['min'])}</b><span>lowest price</span></div>
      <div class="tile"><b>{_fmt_lkr(ins['median'])}</b><span>median price</span></div>
      <div class="tile"><b>{_fmt_lkr(ins['max'])}</b><span>highest price</span></div>
      <div class="tile"><b>{ins['dup_count']}</b><span>cross-site duplicates merged</span></div>
    </div>"""

    names = _source_names()
    by_source_named = {names.get(k, k): v for k, v in ins["by_source"].items()}

    charts = ['<div class="cols">']
    charts.append('<div><h2>By source</h2>' +
                  _bar_rows(by_source_named, ins["count"]) + '</div>')
    if ins["by_area"]:
        charts.append('<div><h2>By area</h2>' +
                      _bar_rows(ins["by_area"], ins["count"], "#4a7fa5") + '</div>')
    if len(ins["by_type"]) > 1:
        charts.append('<div><h2>By property type</h2>' +
                      _bar_rows(ins["by_type"], ins["count"], "#8a6bb0") + '</div>')
    if ins["by_beds"]:
        charts.append('<div><h2>By bedrooms</h2>' +
                      _bar_rows(ins["by_beds"], ins["count"], "#a8721d") + '</div>')
    if ins["hist"]:
        charts.append('<div><h2>Price distribution</h2>' +
                      _bar_rows(ins["hist"], max(ins["hist"].values()), "#2f6f4f")
                      + '</div>')
    charts.append('</div>')

    value_html = ""
    if ins["value"]:
        rows = "".join(
            f'<li><a href="{_esc(l["url"])}">{_esc(l["title"])}</a> — '
            f'{_esc(l["priceText"] or _fmt_lkr(l["priceLKR"]))}, '
            f'{l["bedrooms"]} bed → <b>{_fmt_lkr(int(l["priceLKR"]/l["bedrooms"]))} '
            f'per bedroom</b></li>' for l in ins["value"])
        value_html = f'<h2>Best value (price per bedroom)</h2><ul>{rows}</ul>'

    cards = []
    for i, l in enumerate(listings, 1):
        beds = f" · {l['bedrooms']} bed" if l.get("bedrooms") else ""
        contact = f" · seller: {_esc(l['contact'])}" if l.get("contact") else ""
        also = (f' <span class="badge">also on: '
                f'{_esc(", ".join(names.get(s, s) for s in l["alsoOn"]))}</span>'
                if l.get("alsoOn") else "")
        cards.append(f"""
      <div class="listing">
        <div class="t">{i}. <a href="{_esc(l['url'])}">{_esc(l['title'])}</a></div>
        <div class="meta"><span class="price">{_esc(l.get('priceText') or _fmt_lkr(l.get('priceLKR')))}</span>
          · {_esc(l.get('area'))} · {_esc(l.get('propertyType'))}{beds}{contact}
          <span class="src">{_esc(names.get(l['source'], l['source']))}</span>{also}</div>
      </div>""")

    cov = []
    for src, info in coverage.items():
        n = len(info.get("searched") or [])
        if n:
            cov.append(f"<li><b>{_esc(src)}</b>: searched {n} page(s)</li>")
        for err in info.get("errors") or []:
            cov.append(f'<li class="err">{_esc(err)}</li>')

    budget_str = ""
    if budget.get("min") or budget.get("max"):
        budget_str = (f" · budget {_fmt_lkr(budget.get('min')) if budget.get('min') else 'any'}"
                      f" – {_fmt_lkr(budget.get('max')) if budget.get('max') else 'any'}")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Property search — {_esc(title)}</title>
<style>{CSS}</style></head><body><div class="wrap">
  <h1>Sihina Niwahana — search report</h1>
  <div class="sub">{_esc(title)}{budget_str} · saved {_esc(payload.get('savedAt', ''))}</div>
  {tiles}
  {''.join(charts)}
  {value_html}
  <h2>Shortlist ({ins['count']})</h2>
  {''.join(cards) or '<p>No matching listings.</p>'}
  <h2>Coverage</h2><ul class="cov">{''.join(cov)}</ul>
  <footer>Prices in LKR as displayed by each source site. Every listing links
  to its original ad — nothing is generated. Sri Lanka properties only.</footer>
</div></body></html>"""


def write_report(results_path=None):
    """Render the given (or latest) results JSON to an HTML file next to it."""
    if results_path is None:
        candidates = sorted(RESULTS_DIR.glob("results-*.json"))
        if not candidates:
            raise FileNotFoundError(
                "no saved results in data/results/ — run a search first")
        results_path = candidates[-1]
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    out = results_path.with_suffix(".html")
    out.write_text(render(payload), encoding="utf-8")
    return out
