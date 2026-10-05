#!/usr/bin/env python3
"""
One-shot smoke test for the whole pipeline (no server needed).
Checks: source breadth → 72h freshness → Persian translation → market data
→ charts → bilingual reports with credibility-ranked Persian citations.
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from collections import Counter

from sources import SOURCES, ASSETS, MAX_AGE_HOURS, REPORT_MIN_CREDIBILITY
from scraper import scrape_all
from market_data import fetch_market_data
from report_generator import build_all_reports
from indicators import chart_payload
from fa_format import fa_datetime
from translate import cache_stats

print(f"Sources: {len(SOURCES)} | Assets: {len(ASSETS)} | news window: {MAX_AGE_HOURS}h "
      f"| report credibility floor: {REPORT_MIN_CREDIBILITY}")
kinds = Counter(s.get("kind") for s in SOURCES.values())
print("source kinds:", dict(kinds))

news = scrape_all()
st = news["stats"]
print(f"\narticles: {st['total']} | scored out: {st['rejected']} "
      f"(stale {st['stale_rejected']}) | off-topic skipped: {st['irrelevant']} "
      f"| feeds ok: {st['feeds_ok']}/{st['feeds_total']}")

ages = [a["age_hours"] for a in news["articles"] if a["age_hours"] is not None]
if ages:
    print(f"age check -> max {max(ages):.1f}h (must be <= {MAX_AGE_HOURS}h) "
          f"{'OK' if max(ages) <= MAX_AGE_HOURS else 'FAIL'}")

fa = sum(1 for a in news["articles"] if a["title_fa"])
print(f"Persian titles: {fa}/{len(news['articles'])}")
print("topics:", dict(Counter(a["topic"] for a in news["articles"])))
print("assets:", dict(Counter(x for a in news["articles"] for x in a["assets"])))
print("translation cache:", cache_stats())

md = fetch_market_data()
print(f"\nmarket assets: {len(md)}")
for k, v in sorted(md.items()):
    print(f"  {k:5s} price={v.get('price')} closes={len(v.get('closes') or [])} "
          f"dates={len(v.get('timestamps') or [])} stale={bool(v.get('stale'))}")

# chart series
chart = chart_payload(md.get("BTC", {}), "BTC", {"name": "Bitcoin", "fa": "بیت‌کوین"})
print(f"\nchart BTC: points={len(chart.get('closes') or [])} "
      f"ema={len(chart.get('ema20') or [])} rsi_last={chart.get('rsi', [None])[-1]} "
      f"support={chart.get('support')} resistance={chart.get('resistance')}")

# reports
reps = build_all_reports(md, news["articles"], ["BTC", "XAU"])
for sym, rep in reps.items():
    if rep.get("error"):
        print(f"{sym} REPORT ERROR: {rep['error']}")
        continue
    heads = [v["en"] for k, v in rep["sections"] if k == "h"]
    ta = next((v["en"] for k, v in rep["sections"]
               if k == "p" and "Trend structure" in v.get("en", "")), "")
    paras = len([p for p in ta.split("\n\n") if p.strip()])
    cites = [v for k, v in rep["sections"] if k == "cites"]
    flat = [it for c in cites for it in c["items"]]
    # each block must be ranked most-credible-first (then newest)
    ordered = all(
        all(c["items"][i]["credibility"] >= c["items"][i + 1]["credibility"]
            for i in range(len(c["items"]) - 1))
        for c in cites if len(c["items"]) > 1)
    fresh = all((it.get("age_fa") or "") for it in flat)
    print(f"\n{sym} ({rep['fa_name']}): sections={len(heads)} TA paragraphs={paras} "
          f"(need >= 4) {'OK' if paras >= 4 else 'FAIL'}")
    print(f"  citation blocks={len(cites)} items={len(flat)} "
          f"credibility-ordered={'OK' if ordered else 'FAIL'} "
          f"with-Persian-dates={'OK' if fresh else 'FAIL'}")
    print(f"  headers: {[v['fa'] for k, v in rep['sections'] if k == 'h'][:4]}")
    if flat:
        it = flat[0]
        print(f"  top cite: {it['source']} | {it['title_fa'][:52]} | "
              f"{it['date_fa']} {it['time_fa']} | {it['credibility_fa']}")
btc = reps.get('BTC', {})
if btc and not btc.get('error'):
    print("\nreport generated at:", fa_datetime(btc["generated_at"]),
          "| asof_fa:", btc.get('sections', [])[0][1].get('asof_fa', 'N/A') if btc.get('sections') else 'N/A')
