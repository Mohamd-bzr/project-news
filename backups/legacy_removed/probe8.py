#!/usr/bin/env python3
"""Probe candidate free news sources — report which RSS feeds actually work."""
import concurrent.futures as cf
import feedparser
import requests

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")}

CANDIDATES = [
    # --- crypto outlets (not yet in sources.py) ---
    ("CoinCodex",            "https://coincodex.com/feed/rss",                        "crypto"),
    ("Coinspeaker",          "https://www.coinspeaker.com/feed/",                     "crypto"),
    ("The Tokenist",         "https://tokenist.com/feed/",                            "crypto"),
    ("Crypto News Flash",    "https://www.crypto-news-flash.com/feed/",               "crypto"),
    ("ZyCrypto",             "https://zycrypto.com/feed/",                            "crypto"),
    ("NullTX",               "https://nulltx.com/feed/",                              "crypto"),
    ("CryptoNinjas",         "https://www.cryptoninjas.net/feed/",                    "crypto"),
    ("Coinfomania",          "https://coinfomania.com/feed/",                         "crypto"),
    ("Bitcoin Exchange Guide","https://bitcoinexchangeguide.com/feed/",               "crypto"),
    ("CryptoGlobe",          "https://www.cryptoglobe.com/rss/",                      "crypto"),
    ("Block Telegraph",      "https://blocktelegraph.io/feed/",                       "crypto"),
    ("The Fintech Times",    "https://thefintechtimes.com/feed/",                     "crypto"),
    ("Blockchain News",      "https://www.blockchain.news/rss",                       "crypto"),
    ("CryptoVibes",          "https://www.cryptovibes.com/feed",                      "crypto"),
    ("Block Tribune",        "https://blocktrib.com/feed/",                           "crypto"),
    ("CryptoNewsZ",          "https://www.cryptonewsz.com/feed/",                     "crypto"),
    ("The Crypto Basic",     "https://thecryptobasic.com/feed/",                      "crypto"),
    ("Crypto-News.net",      "https://crypto-news.net/feed/",                         "crypto"),
    ("TodayOnChain",         "https://www.todayonchain.com/feed",                     "crypto"),
    ("Bitcoin Linux",        "https://bitcoinlinux.com/feed/",                        "crypto"),
    # --- macro / mainstream finance ---
    ("BBC Business",         "https://feeds.bbci.co.uk/news/business/rss.xml",        "macro"),
    ("Guardian Business",    "https://www.theguardian.com/uk/business/rss",           "macro"),
    ("CNN Business",         "http://rss.cnn.com/rss/money_news_economy.rss",         "macro"),
    ("WSJ Markets",          "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",         "macro"),
    ("The Economist FnE",    "https://www.economist.com/finance-and-economics/rss.xml","macro"),
    ("AP Business",          "https://apnews.com/feed/business",                      "macro"),
    ("Fortune",              "https://fortune.com/feed/",                             "macro"),
    ("Forbes Money",         "https://www.forbes.com/money/feed/",                    "macro"),
    ("Al Jazeera",           "https://www.aljazeera.com/xml/rss/all.xml",             "macro"),
    # --- metals / commodities ---
    ("Investing News Net",   "https://investingnews.com/feed/",                       "metals"),
    ("Silver Doctors",       "https://silverdoctors.com/feed/",                       "metals"),
    ("Mining Weekly",        "https://www.miningweekly.com/article-rss",              "metals"),
    ("GoldSilver",           "https://goldsilver.com/rss/",                           "metals"),
    # --- research / on-chain ---
    ("Chainalysis Blog",     "https://www.chainalysis.com/blog/rss/",                 "research"),
    ("Delphi Digital",       "https://medium.com/feed/@delphi_digital",               "research"),
    ("ARK Invest",           "https://ark-invest.com/feed/",                          "research"),
    ("Coin Center",          "https://www.coincenter.org/feed/",                      "research"),
    ("Santiment Insights",   "https://insights.santiment.net/rss",                    "research"),
    # --- social: real free feeds from social platforms ---
    ("YT Coin Bureau",       "https://www.youtube.com/feeds/videos.xml?channel_id=UCqK_GSMbpiV8spgD3ZGloSw", "social"),
    ("YT Anthony Pompliano", "https://www.youtube.com/feeds/videos.xml?channel_id=UCREtqLJKRVe9iPH5R9Vddig", "social"),
    ("YT Into Cryptoverse",  "https://www.youtube.com/feeds/videos.xml?channel_id=UCMtJYS0PrtiUwlk6zjZDE2g", "social"),
    ("YT Bankless",          "https://www.youtube.com/feeds/videos.xml?channel_id=UCsmOa4ThPhRQ0HFTnAtBLAw", "social"),
    ("Mastodon #bitcoin",    "https://mastodon.social/tags/bitcoin.rss",              "social"),
    ("Mastodon #crypto",     "https://mastodon.social/tags/cryptocurrency.rss",       "social"),
    ("r/WallStreetSilver",   "https://www.reddit.com/r/WallStreetSilver/.rss",        "social"),
    ("r/PreciousMetals",     "https://www.reddit.com/r/PreciousMetals/.rss",          "social"),
    ("r/btc",                "https://www.reddit.com/r/btc/.rss",                     "social"),
]


def probe(item):
    name, url, kind = item
    try:
        r = requests.get(url, headers=UA, timeout=12, allow_redirects=True)
        if r.status_code != 200:
            return (name, kind, f"HTTP {r.status_code}", 0, "")
        d = feedparser.parse(r.text)
        n = len(d.entries)
        if not n:
            return (name, kind, "no entries", 0, "")
        t = d.entries[0].get("title", "")[:60]
        return (name, kind, "OK", n, t)
    except Exception as e:
        return (name, kind, f"{type(e).__name__}: {str(e)[:40]}", 0, "")


with cf.ThreadPoolExecutor(max_workers=12) as ex:
    results = list(ex.map(probe, CANDIDATES))

ok = [r for r in results if r[2] == "OK"]
bad = [r for r in results if r[2] != "OK"]
print(f"=== WORKING ({len(ok)}) ===")
for name, kind, _, n, t in sorted(ok, key=lambda x: (x[1], -x[3])):
    print(f"  [{kind:8}] {name:24} {n:3} items | {t}")
print(f"\n=== DEAD/BLOCKED ({len(bad)}) ===")
for name, kind, why, _, _ in bad:
    print(f"  [{kind:8}] {name:24} {why}")
