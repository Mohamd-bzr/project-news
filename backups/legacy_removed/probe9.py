#!/usr/bin/env python3
"""Probe the keyless RSS candidates from the user's news_sources_report.html."""
import concurrent.futures as cf
import feedparser
import requests

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")}

_GN = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

CANDIDATES = [
    # --- tier-1 wires: official RSS ---
    ("Bloomberg news",        "https://feeds.bloomberg.com/news.rss"),
    ("Bloomberg markets",     "https://www.bloomberg.com/feeds/markets/news.rss"),
    ("Bloomberg business",    "https://www.bloomberg.com/feeds/business/news.rss"),
    ("Reuters all",           "https://www.reuters.com/arc/outboundfeeds/v3/all/rss.xml"),
    ("Reuters business(old)", "https://www.reuters.com/rssFeed/businessNews"),
    ("Reuters markets(old)",  "https://www.reuters.com/rssFeed/marketsNews"),
    ("WSJ markets",           "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("WSJ business",          "https://www.wsj.com/xml/rss/3_7085.xml"),
    ("WSJ world",             "https://www.wsj.com/xml/rss/3_7014.xml"),
    ("WSJ tech",              "https://www.wsj.com/xml/rss/3_7015.xml"),
    ("FT home",               "https://www.ft.com/rss/home"),
    ("FT markets(have)",      "https://www.ft.com/markets?format=rss"),
    # --- fast aggregators ---
    ("Benzinga",              "https://www.benzinga.com/feed"),
    ("ForexLive",             "https://www.forexlive.com/feed"),
    ("ForexLive news",        "https://www.forexlive.com/feed/news"),
    ("FXStreet news",         "https://www.fxstreet.com/rss/news"),
    ("FXStreet crypto",       "https://www.fxstreet.com/rss/crypto"),
    ("CNBC top",              "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"),
    ("CNBC finance",          "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147"),
    ("CNBC tech",             "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135"),
    ("MarketWatch pulse",     "https://feeds.marketwatch.com/marketwatch/marketpulse/"),
    # --- Google News site: filters (wire headlines without paywalls) ---
    ("GN site:bloomberg",     _GN.format(q="when:48h+site:bloomberg.com")),
    ("GN site:reuters",       _GN.format(q="when:48h+site:reuters.com")),
    ("GN site:wsj",           _GN.format(q="when:48h+site:wsj.com")),
    ("GN site:ft",            _GN.format(q="when:48h+site:ft.com")),
]


def probe(item):
    name, url = item
    try:
        r = requests.get(url, headers=UA, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            return (name, f"HTTP {r.status_code}", 0, "")
        d = feedparser.parse(r.text)
        n = len(d.entries)
        if not n:
            return (name, "no entries", 0, "")
        t = d.entries[0].get("title", "")[:70]
        return (name, "OK", n, t)
    except Exception as e:
        return (name, f"{type(e).__name__}: {str(e)[:45]}", 0, "")


with cf.ThreadPoolExecutor(max_workers=10) as ex:
    results = list(ex.map(probe, CANDIDATES))

ok = [r for r in results if r[1] == "OK"]
bad = [r for r in results if r[1] != "OK"]
print(f"=== WORKING ({len(ok)}) ===")
for name, _, n, t in sorted(ok, key=lambda x: -x[2]):
    print(f"  {name:22} {n:4} items | {t}")
print(f"\n=== DEAD/BLOCKED ({len(bad)}) ===")
for name, why, _, _ in bad:
    print(f"  {name:22} {why}")
