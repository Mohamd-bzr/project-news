#!/usr/bin/env python3
"""
News Engine — Sources, Assets, Taxonomy & Credibility
=====================================================
Everything here is **free and key-less**. Three complementary layers give
each tracked asset dense daily coverage:

  1. specialist outlets (crypto wires, metals desks, macro desks)
  2. per-asset Google News queries — free, enormous reach, and they index
     social posts / video / blogs as well as newspapers
  3. Reddit RSS (social sentiment) with lower trust weighting

Freshness rule: nothing older than MAX_AGE_HOURS (72h) enters the pipeline —
stale items are dropped outright, as requested.
"""

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

# ---------------------------------------------------------------------------
# PIPELINE RULES
# ---------------------------------------------------------------------------
MAX_AGE_HOURS = 72          # hard cutoff — older news is discarded entirely
MAX_ARTICLES_PER_FEED = 22
MIN_CREDIBILITY = 0.30      # below this an article is dropped
REPORT_MIN_CREDIBILITY = 0.55   # reports only cite reasonably credible items

# ---------------------------------------------------------------------------
# TOPIC TAXONOMY
# ---------------------------------------------------------------------------
TOPICS = {
    "regulation":    {"fa": "مقررات",   "icon": "⚖️"},
    "institutional": {"fa": "نهادی",    "icon": "🏛"},
    "etf":           {"fa": "ETF",      "icon": "📊"},
    "macro":         {"fa": "کلان",     "icon": "🌍"},
    "security":      {"fa": "امنیت",    "icon": "🛡"},
    "analysis":      {"fa": "تحلیل",    "icon": "📈"},
    "defi":          {"fa": "دی‌فای",   "icon": "🔗"},
    "market":        {"fa": "بازار",    "icon": "💱"},
    "tech":          {"fa": "فناوری",   "icon": "⚙️"},
    "general":       {"fa": "عمومی",    "icon": "📰"},
}
TOPIC_ORDER = list(TOPICS.keys())

_TOPIC_KEYWORDS = {
    "security": r"\bhack(?:ed|ers?|ing)?\b|\bexploit\w*\b|\bbreach\w*\b|\bstolen\b|\bsteal(?:ing|s)?\b|\bscam\w*\b|\bphishing\b|\bransom\w*\b|\bvulnerab\w*\b|\bmal(?:w|f)are\b|\bdrain(?:ed|ing)?\b|\bseiz\w*\b|\blaunder\w*\b",
    "regulation": r"\bregulat\w*\b|\bSEC\b|\bCFTC\b|\bMiCA\b|\blegislat\w*\b|\bbill\b|\bsenate\b|\bcongress\w*\b|\blaw(?:s|maker)?\b|\bban(?:s|ned|ning)?\b|\blegal\w*\b|\bcompliance\b|\benforcement\b|\bcourt\b|\bDOJ\b|\bprosecut\w*\b|\bOCC\b|\btax\w*\b|\bclarity act\b|\bpolicy\b",
    "institutional": r"\bblackrock\b|\bgrayscale\b|\bfidelity\b|\bark invest\b|\bmicrostrategy\b|\bstrategy\b|\bcorporate\b|\binstitution\w*\b|\bbank\w*|\bstrive\b|\bbitmine\b|\bwall street\b|\bjpmorgan\b|\bgoldman\b|\bmorgan stanley\b|\bstandard chartered\b|\bbank of america\b|\bsovereign\b|\bpension\b",
    "etf": r"\betf\w*\b|\binflow\w*\b|\boutflow\w*\b|\bfund flow\w*\b|\bspot (?:bitcoin|ether|eth|btc|solana|xrp|gold|silver) etf\b|\bibit\b|\bethe\b|\bgld\b|\bslv\b",
    "macro": r"\bfed\b|\bfomc\b|\bfederal reserve\b|\binterest rate\w*\b|\brate (?:cut|hike)\w*\b|\binflation\b|\bcpi\b|\bpce\b|\bppi\b|\bgdp\b|\bunemploy\w*\b|\brecession\b|\byield\w*\b|\btreasury (?:yield|bond|note)s?\b|\bdollar (?:index|strength)\b|\bdxy\b|\bliquidity\b|\bmacro\b|\bopec\b|\boil price\w*\b|\btrade war\b|\btariff\w*\b|\bcentral bank\w*\b|\bpowell\b|\bwarsh\b",
    "analysis": r"\bforecast\b|\bpredict\w*\b|\bprice (?:target|analysis|prediction)\w*\b|\btechnical\w*\b|\bsupport\b|\bresistance\b|\brsi\b|\bmacd\b|\bchart\w*\b|\bbullish\b|\bbearish\b|\brally\b|\bcorrection\b|\bconsolidat\w*\b|\bbreakout\b|\bbreakdown\b|\bgolden cross\b|\bdeath cross\b|\bfibonacci\b|\bdivergence\b",
    "defi": r"\bdefi\b|\bliquidity pool\w*\b|\bstaking\b|\blending\b|\bvault\w*\b|\bamm\b|\bairdrop\w*\b|\bgovernance\b|\bdao\b|\brestaking\b|\btokeniz\w*\b",
    "market": r"\bwhale\w*\b|\bliquidation\w*\b|\bfunding rate\w*\b|\bopen interest\b|\bderivatives?\b|\bfutures?\b|\boptions?\b|\btrading volume\b|\bmarket cap\b|\bdump\w*\b|\bpump\w*\b|\bsurge\w*\b|\bplunge\w*\b|\bcrash\w*\b|\bspike\w*\b|\bslide\w*\b|\bsell-?off\b|\bprice\b",
    "tech": r"\bupgrade\w*\b|\bmainnet\b|\btestnet\b|\bfork\b|\beip-?\d+\b|\bbip-?\d+\b|\bprotocol\b|\bblockchain (?:update|release)\b|\bintegrat\w*\b|\bpartnership\b|\bsdk\b|\bapi\b",
}
_TOPIC_COMPILED = {k: re.compile(v, re.I) for k, v in _TOPIC_KEYWORDS.items()}

# ---------------------------------------------------------------------------
# ASSET DETECTION — anchored regexes to avoid false positives
# ---------------------------------------------------------------------------
_ASSET_PATTERNS = {
    "BTC":  r"\b(?:bitcoin|btc|sats?|satoshis?)\b",
    "ETH":  r"\b(?:ethereum|ether|eth|vitalik)\b",
    "SOL":  r"\b(?:solana|sol)\b",
    "XRP":  r"\b(?:xrp|ripple)\b",
    "ADA":  r"\b(?:cardano|ada)\b",
    "BNB":  r"\b(?:bnb|binance coin|binance smart chain|bsc)\b",
    "DOGE": r"\b(?:dogecoin|doge)\b",
    "XAU":  r"\b(?:gold|xau(?:usd)?|bullion|ounce of gold)\b",
    "XAG":  r"\b(?:silver|xag(?:usd)?|white metal)\b",
    "WTI":  r"\b(?:oil|wti|crude|brent|opec|petroleum|barrel)\b",
    "DXY":  r"\b(?:dxy|dollar index|usd index|greenback|us dollar)\b",
    "SPX":  r"\b(?:s&p|spx|s&p 500|stock market|equities|wall street)\b",
    "VIX":  r"\b(?:vix|volatility index|implied volatility)\b",
}

# ---------------------------------------------------------------------------
# TRACKED ASSETS (default coverage — users can add their own)
# ---------------------------------------------------------------------------
ASSETS = {
    "BTC":  {"fa": "Bitcoin",    "icon": "₿",  "name": "Bitcoin",  "yahoo": "BTC-USD", "coingecko": "bitcoin"},
    "ETH":  {"fa": "Ethereum",   "icon": "Ξ",  "name": "Ethereum", "yahoo": "ETH-USD", "coingecko": "ethereum"},
    "SOL":  {"fa": "Solana",     "icon": "◎",  "name": "Solana",   "yahoo": "SOL-USD", "coingecko": "solana"},
    "XRP":  {"fa": "XRP",        "icon": "✕",  "name": "XRP",      "yahoo": "XRP-USD", "coingecko": "ripple"},
    "XAU":  {"fa": "Gold",       "icon": "🥇", "name": "Gold",     "yahoo": "GC=F",    "coingecko": None},
    "ADA":  {"fa": "Cardano",    "icon": "₳",  "name": "Cardano",  "yahoo": "ADA-USD", "coingecko": "cardano"},
    "BNB":  {"fa": "BNB",        "icon": "🔶", "name": "BNB",      "yahoo": "BNB-USD", "coingecko": "binancecoin"},
    "DOGE": {"fa": "Dogecoin",   "icon": "Ð",  "name": "Dogecoin", "yahoo": "DOGE-USD", "coingecko": "dogecoin"},
    "XAG":  {"fa": "Silver",     "icon": "🥈", "name": "Silver",   "yahoo": "SI=F",    "coingecko": None},
    # macro assets — full citizens: price card, news tag, clickable, report
    "WTI":  {"fa": "نفت WTI",     "icon": "🛢", "name": "WTI Crude Oil", "yahoo": "CL=F",     "coingecko": None},
    "DXY":  {"fa": "دلار DXY",    "icon": "💵", "name": "US Dollar Index", "yahoo": "DX-Y.NYB", "coingecko": None},
    "SPX":  {"fa": "اس‌اند‌پی ۵۰۰", "icon": "🏛", "name": "S&P 500",     "yahoo": "^GSPC",     "coingecko": None},
    "VIX":  {"fa": "شاخص ترس VIX", "icon": "😰", "name": "CBOE Volatility Index", "yahoo": "^VIX", "coingecko": None},
}

# ---------------------------------------------------------------------------
# SOURCES
# ---------------------------------------------------------------------------
# kind: crypto | metals | macro | research | search | social
SOURCES = {
    # ── Tier 1 crypto wires ─────────────────────────────────────────────
    "coindesk":       {"name": "CoinDesk",        "rss": "https://www.coindesk.com/arc/outboundfeeds/rss/", "trust": 0.95, "tier": 1, "kind": "crypto"},
    "cointelegraph":  {"name": "CoinTelegraph",   "rss": "https://cointelegraph.com/rss",                   "trust": 0.86, "tier": 1, "kind": "crypto"},
    "theblock":       {"name": "The Block",       "rss": "https://www.theblock.co/rss.xml",                 "trust": 0.90, "tier": 1, "kind": "crypto"},
    "decrypt":        {"name": "Decrypt",         "rss": "https://decrypt.co/feed",                         "trust": 0.85, "tier": 1, "kind": "crypto"},
    "blockworks":     {"name": "Blockworks",      "rss": "https://blockworks.co/feed",                      "trust": 0.85, "tier": 1, "kind": "crypto"},
    "bitcoinmagazine":{"name": "Bitcoin Magazine","rss": "https://bitcoinmagazine.com/.rss/full/",          "trust": 0.82, "tier": 1, "kind": "crypto"},
    "bitcoincom":     {"name": "Bitcoin.com News","rss": "https://news.bitcoin.com/feed/",                  "trust": 0.76, "tier": 2, "kind": "crypto"},
    "protos":         {"name": "Protos",          "rss": "https://protos.com/feed/",                        "trust": 0.80, "tier": 2, "kind": "crypto"},
    "cryptobriefing": {"name": "Crypto Briefing", "rss": "https://cryptobriefing.com/feed/",                "trust": 0.78, "tier": 2, "kind": "crypto"},
    "dlnews":         {"name": "DL News",         "rss": "https://www.dlnews.com/arc/outboundfeeds/rss/",   "trust": 0.80, "tier": 2, "kind": "crypto"},

    # ── Tier 2 crypto newsrooms ─────────────────────────────────────────
    "cryptoslate":    {"name": "CryptoSlate",     "rss": "https://cryptoslate.com/feed/",                  "trust": 0.75, "tier": 2, "kind": "crypto"},
    "ambcrypto":      {"name": "AMBCrypto",       "rss": "https://ambcrypto.com/feed/",                    "trust": 0.75, "tier": 2, "kind": "crypto"},
    "beincrypto":     {"name": "BeInCrypto",      "rss": "https://beincrypto.com/feed/",                   "trust": 0.75, "tier": 2, "kind": "crypto"},
    "cryptonews":     {"name": "Cryptonews",      "rss": "https://cryptonews.com/news/feed/",              "trust": 0.72, "tier": 2, "kind": "crypto"},
    "cryptopotato":   {"name": "CryptoPotato",    "rss": "https://cryptopotato.com/feed/",                 "trust": 0.72, "tier": 2, "kind": "crypto"},
    "bitcoinist":     {"name": "Bitcoinist",      "rss": "https://bitcoinist.com/feed/",                   "trust": 0.70, "tier": 2, "kind": "crypto"},
    "newsbtc":        {"name": "NewsBTC",         "rss": "https://www.newsbtc.com/feed/",                  "trust": 0.74, "tier": 2, "kind": "crypto"},
    "dailyhodl":      {"name": "The Daily Hodl",  "rss": "https://dailyhodl.com/feed/",                    "trust": 0.70, "tier": 2, "kind": "crypto"},
    "coingape":       {"name": "CoinGape",        "rss": "https://coingape.com/feed/",                     "trust": 0.66, "tier": 2, "kind": "crypto"},
    "coinjournal":    {"name": "CoinJournal",     "rss": "https://coinjournal.net/feed/",                  "trust": 0.72, "tier": 2, "kind": "crypto"},
    "watcherguru":    {"name": "Watcher Guru",    "rss": "https://watcher.guru/feed",                      "trust": 0.68, "tier": 2, "kind": "crypto"},
    "thedefiant":     {"name": "The Defiant",     "rss": "https://thedefiant.io/feed",                     "trust": 0.80, "tier": 2, "kind": "crypto"},
    "coincu":         {"name": "CoinCu",          "rss": "https://coincu.com/feed/",                       "trust": 0.66, "tier": 2, "kind": "crypto"},
    "cryptodaily":    {"name": "Crypto Daily",    "rss": "https://cryptodaily.co.uk/feed",                 "trust": 0.66, "tier": 2, "kind": "crypto"},
    "coinrepublic":   {"name": "The Coin Republic","rss": "https://www.thecoinrepublic.com/feed/",         "trust": 0.64, "tier": 3, "kind": "crypto"},
    "trustnodes":     {"name": "TrustNodes",      "rss": "https://trustnodes.com/feed",                    "trust": 0.70, "tier": 3, "kind": "crypto"},
    "bitcoinworld":   {"name": "BitcoinWorld",    "rss": "https://bitcoinworld.co.in/feed/",               "trust": 0.62, "tier": 3, "kind": "crypto"},
    "finbold":        {"name": "Finbold",         "rss": "https://finbold.com/feed",                       "trust": 0.70, "tier": 3, "kind": "crypto"},
    "coinpedia":      {"name": "CoinPedia",       "rss": "https://coinpedia.org/feed/",                    "trust": 0.62, "tier": 3, "kind": "crypto"},
    "utoday":         {"name": "U.Today",         "rss": "https://u.today/rss",                            "trust": 0.62, "tier": 3, "kind": "crypto"},
    "ethnews":        {"name": "ETH World News",  "rss": "https://ethereumworldnews.com/feed/",            "trust": 0.65, "tier": 3, "kind": "crypto"},

    # ── Tier 2/3 crypto wires (added 2026-09 — user-approved batch) ────
    "cryptonewsflash": {"name": "Crypto News Flash", "rss": "https://www.crypto-news-flash.com/feed/",     "trust": 0.66, "tier": 2, "kind": "crypto"},
    "zycrypto":       {"name": "ZyCrypto",         "rss": "https://zycrypto.com/feed/",                     "trust": 0.66, "tier": 2, "kind": "crypto"},
    "coinspeaker":    {"name": "Coinspeaker",      "rss": "https://www.coinspeaker.com/feed/",              "trust": 0.72, "tier": 2, "kind": "crypto"},
    "thetokenist":    {"name": "The Tokenist",     "rss": "https://tokenist.com/feed/",                     "trust": 0.72, "tier": 2, "kind": "crypto"},
    "cryptoninjas":   {"name": "CryptoNinjas",     "rss": "https://www.cryptoninjas.net/feed/",             "trust": 0.64, "tier": 3, "kind": "crypto"},
    "coinfomania":    {"name": "Coinfomania",      "rss": "https://coinfomania.com/feed/",                  "trust": 0.62, "tier": 3, "kind": "crypto"},
    "cryptonewsz":    {"name": "CryptoNewsZ",      "rss": "https://www.cryptonewsz.com/feed/",              "trust": 0.62, "tier": 3, "kind": "crypto"},
    "thecryptobasic": {"name": "The Crypto Basic", "rss": "https://thecryptobasic.com/feed/",               "trust": 0.60, "tier": 3, "kind": "crypto"},
    "cryptonewsnet":  {"name": "Crypto-News.net",  "rss": "https://crypto-news.net/feed/",                  "trust": 0.64, "tier": 3, "kind": "crypto"},
    "blocktelegraph": {"name": "Block Telegraph",  "rss": "https://blocktelegraph.io/feed/",                "trust": 0.62, "tier": 3, "kind": "crypto"},
    "fintechtimes":   {"name": "The Fintech Times", "rss": "https://thefintechtimes.com/feed/",             "trust": 0.66, "tier": 2, "kind": "crypto"},
    "nulltx":         {"name": "NullTX",           "rss": "https://nulltx.com/feed/",                       "trust": 0.60, "tier": 3, "kind": "crypto"},

    # ── Metals / commodities ────────────────────────────────────────────
    "kitco":          {"name": "Kitco Metals",    "rss": "https://www.kitco.com/rss/KitcoNewsRSS.xml",     "trust": 0.80, "tier": 2, "kind": "metals"},
    "fxempire":       {"name": "FXEmpire",        "rss": "https://www.fxempire.com/api/v1/en/articles/rss/news", "trust": 0.82, "tier": 2, "kind": "macro"},
    "fxempire-crypto": {"name": "FXEmpire Crypto", "rss": "https://www.fxempire.com/api/v1/en/articles/rss/news?category=Cryptocurrencies", "trust": 0.82, "tier": 2, "kind": "crypto"},
    "fxempire-currencies": {"name": "FXEmpire Currencies", "rss": "https://www.fxempire.com/api/v1/en/articles/rss/news?category=Currencies", "trust": 0.82, "tier": 2, "kind": "macro"},
    "fxempire-commodities": {"name": "FXEmpire Commodities", "rss": "https://www.fxempire.com/api/v1/en/articles/rss/news?category=Commodities", "trust": 0.82, "tier": 2, "kind": "metals"},
    "fxempire-stocks": {"name": "FXEmpire Stocks", "rss": "https://www.fxempire.com/api/v1/en/articles/rss/news?category=Stock-Indices", "trust": 0.80, "tier": 2, "kind": "macro"},
    "investing-com":  {"name": "Investing.com",   "rss": "https://www.investing.com/rss/news_285.rss",     "trust": 0.80, "tier": 2, "kind": "metals"},
    "investing-news": {"name": "Investing.com Mkts","rss": "https://www.investing.com/rss/news.rss",       "trust": 0.80, "tier": 2, "kind": "macro"},
    "oilprice":       {"name": "OilPrice",        "rss": "https://oilprice.com/rss/main",                  "trust": 0.74, "tier": 3, "kind": "metals"},
    "miningcom":      {"name": "Mining.com",      "rss": "https://www.mining.com/feed/",                   "trust": 0.78, "tier": 2, "kind": "metals"},

    # ── Precious metals expansion 2026-09-28 (verified live) ───────────────
    # Native bullion-dealer RSS is largely dead (403/404/empty). Google News
    # topic feeds returned real editorial content on every one of 49 tested.
    # gl+ceid are REQUIRED on the Google URLs or topic queries return 0 entries.
    "gold-price":      {"name": "Gold Price", "rss": "https://news.google.com/rss/search?q=%22gold+price%22+OR+%22gold+prices%22+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.85, "tier": 2, "kind": "metals"},
    "gold-record":     {"name": "Gold Record High", "rss": "https://news.google.com/rss/search?q=%22gold%22+%22record+high%22+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.80, "tier": 2, "kind": "metals"},
    "silver-price":    {"name": "Silver Price", "rss": "https://news.google.com/rss/search?q=%22silver+price%22+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.85, "tier": 2, "kind": "metals"},
    "pgm":             {"name": "Platinum Palladium PGM", "rss": "https://news.google.com/rss/search?q=platinum+palladium+rhodium+%28price+OR+supply+OR+mine%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.80, "tier": 2, "kind": "metals"},
    "safe-haven":      {"name": "Safe Haven Flows", "rss": "https://news.google.com/rss/search?q=%22safe+haven%22+%28gold+OR+silver+OR+%22precious+metal%22%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.80, "tier": 2, "kind": "metals"},
    "comex":           {"name": "COMEX Futures", "rss": "https://news.google.com/rss/search?q=%28COMEX+OR+futures+OR+%22open+interest%22%29+%28gold+OR+silver%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.80, "tier": 2, "kind": "metals"},
    "cftc":            {"name": "CFTC Positioning", "rss": "https://news.google.com/rss/search?q=%28CFTC+OR+positioning+OR+commitments%29+%28gold+OR+silver+OR+copper%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.80, "tier": 2, "kind": "metals"},
    "gold-etf":        {"name": "Gold Silver ETF Flows", "rss": "https://news.google.com/rss/search?q=%28gold+OR+silver%29+%28ETF+OR+%22fund+flows%22+OR+%22inflows%22+OR+%22outflows%22%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.80, "tier": 2, "kind": "metals"},
    "cb-gold-buy":     {"name": "Central Bank Gold", "rss": "https://news.google.com/rss/search?q=%22central+bank%22+%28gold+OR+%22gold+buying%22+OR+reserves%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.85, "tier": 2, "kind": "metals"},
    "fed-gold":        {"name": "Fed Rate Gold", "rss": "https://news.google.com/rss/search?q=%28Fed+OR+%22Federal+Reserve%22+OR+rate+cut%29+gold+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.80, "tier": 2, "kind": "metals"},
    "inflation-gold":  {"name": "Inflation Metals", "rss": "https://news.google.com/rss/search?q=inflation+%28gold+OR+%22precious+metals%22+OR+%22safe+haven%22%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.78, "tier": 2, "kind": "metals"},
    "gold-mine":       {"name": "Gold Mining", "rss": "https://news.google.com/rss/search?q=%28%22gold+mine%22+OR+%22gold+mining%22+OR+miner%29+%28production+OR+AISC+OR+%22cost+curve%22%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.78, "tier": 2, "kind": "metals"},
    "silver-mine":     {"name": "Silver Mining", "rss": "https://news.google.com/rss/search?q=%28%22silver+mine%22+OR+%22silver+mining%22%29+when%3A5d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.75, "tier": 2, "kind": "metals"},
    "silver-squeeze":  {"name": "Silver Squeeze", "rss": "https://news.google.com/rss/search?q=%22silver%22+%28squeeze+OR+%22physical+demand%22+OR+premiu%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.78, "tier": 2, "kind": "metals"},
    "gold-supply":     {"name": "Gold Supply Demand", "rss": "https://news.google.com/rss/search?q=%28gold+OR+silver%29+%28mine+OR+supply+OR+%22mine+supply%22+OR+%22jewellery+demand%22%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.76, "tier": 2, "kind": "metals"},
    "gold-etf-countr": {"name": "China India Gold", "rss": "https://news.google.com/rss/search?q=%28India+OR+China+OR+Turkey+OR+Russia%29+%28gold+OR+silver%29+%28buying+OR+imports+OR+%22central+bank%22%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "metals"},
    "gold-jewellery":  {"name": "Gold Jewellery Demand", "rss": "https://news.google.com/rss/search?q=%28%22jewellery%22+OR+jewelry%29+%28gold+OR+%22gold+demand%22%29+%28India+OR+China+OR+Turkey%29+when%3A5d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.75, "tier": 2, "kind": "metals"},
    "gold-coins":      {"name": "Gold Coins Bullion", "rss": "https://news.google.com/rss/search?q=%28%22gold+coin%22+OR+%22gold+bar%22+OR+bullion%29+%28sales+OR+demand+OR+buyback%29+when%3A5d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.72, "tier": 2, "kind": "metals"},
    "gold-refinery":   {"name": "Gold Refinery Mint", "rss": "https://news.google.com/rss/search?q=%28refinery+OR+refining+OR+%22gold+bar%22+OR+mint%29+%28gold+OR+silver%29+when%3A5d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.70, "tier": 2, "kind": "metals"},
    "geopolitics-gold":{"name": "Geopolitics Gold", "rss": "https://news.google.com/rss/search?q=%28geopolit*+OR+%22trade+war%22+OR+sanctions%29+%28gold+OR+silver%29+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.78, "tier": 2, "kind": "metals"},
    "dollar-gold":     {"name": "Dollar Gold", "rss": "https://news.google.com/rss/search?q=%28%22dollar+index%22+OR+%22dollar+strength%22%29+gold+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.72, "tier": 2, "kind": "metals"},

    # Publisher-scoped via Google — free path to the Bloomberg/Reuters/CNBC wire.
    "gn-reuters-gold":    {"name": "Reuters Metals", "rss": "https://news.google.com/rss/search?q=source%3AReuters+%28gold+OR+silver+OR+metals%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.88, "tier": 2, "kind": "metals"},
    "gn-bloomberg":       {"name": "Bloomberg Metals", "rss": "https://news.google.com/rss/search?q=source%3ABloomberg+%28gold+OR+silver+OR+%22precious+metals%22%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.86, "tier": 2, "kind": "metals"},
    "gn-cnbc":            {"name": "CNBC Commodities", "rss": "https://news.google.com/rss/search?q=source%3ACNBC+%28gold+OR+silver+OR+commodities%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "metals"},
    "gn-investing":       {"name": "Investing Metals", "rss": "https://news.google.com/rss/search?q=site%3Ainvesting.com+%28gold+OR+silver%29+%28price+OR+forecast+OR+analysis%29+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.78, "tier": 2, "kind": "metals"},
    "gn-fxempire":        {"name": "FXEmpire",        "rss": "https://news.google.com/rss/search?q=site%3Afxempire.com+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "search"},
    "fxstreet":           {"name": "FXStreet",        "rss": "https://news.google.com/rss/search?q=site%3Afxstreet.com+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "macro"},
    "fxstreet-news":      {"name": "FXStreet News",   "rss": "https://news.google.com/rss/search?q=site%3Afxstreet.com%2Fnews+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "macro"},
    "fxstreet-crypto":    {"name": "FXStreet Crypto", "rss": "https://news.google.com/rss/search?q=site%3Afxstreet.com+%28crypto+OR+bitcoin+OR+ethereum+OR+xrp+OR+solana%29+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "crypto"},
    "fxstreet-forex":     {"name": "FXStreet Forex",  "rss": "https://news.google.com/rss/search?q=site%3Afxstreet.com+%28forex+OR+dollar+OR+eur+OR+currency%29+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "macro"},
    "fxstreet-metals":    {"name": "FXStreet Metals", "rss": "https://news.google.com/rss/search?q=site%3Afxstreet.com+%28gold+OR+silver+OR+oil+OR+metals%29+when%3A2d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "metals"},
    "gn-fxstreet":        {"name": "FXStreet",        "rss": "https://news.google.com/rss/search?q=site%3Afxstreet.com+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.82, "tier": 2, "kind": "metals"},
    "gn-kitco":           {"name": "Kitco News", "rss": "https://news.google.com/rss/search?q=site%3Akitco.com+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.84, "tier": 2, "kind": "metals"},
    "gn-goldseek":        {"name": "GoldSeek Feed", "rss": "https://news.google.com/rss/search?q=site%3Agoldseek.com+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.76, "tier": 2, "kind": "metals"},
    "gn-silverseek":      {"name": "SilverSeek Feed", "rss": "https://news.google.com/rss/search?q=site%3Asilverseek.com+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.76, "tier": 2, "kind": "metals"},
    "gn-mining":          {"name": "Mining.com Feed", "rss": "https://news.google.com/rss/search?q=site%3Amining.com+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.78, "tier": 2, "kind": "metals"},
    "gn-bullionvault":    {"name": "BullionVault News", "rss": "https://news.google.com/rss/search?q=site%3Abullionvault.com+when%3A7d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.84, "tier": 2, "kind": "metals"},
    "gn-moneymetals":     {"name": "MoneyMetals News", "rss": "https://news.google.com/rss/search?q=site%3Amoneymetals.com+when%3A7d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.80, "tier": 2, "kind": "metals"},
    "gn-goldorg":         {"name": "World Gold Council", "rss": "https://news.google.com/rss/search?q=site%3Agold.org+when%3A7d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.90, "tier": 2, "kind": "metals"},
    "gn-zerocopy":        {"name": "SeekingAlpha Precious", "rss": "https://news.google.com/rss/search?q=site%3Aseekingalpha.com+%28gold+OR+silver%29+when%3A3d&hl=en-US&gl=US&ceid=US:EN", "trust": 0.74, "tier": 2, "kind": "metals"},

    # Native RSS confirmed working through the recovery ladder.
    "wgc-native":              {"name": "World Gold Council RSS", "rss": "https://www.gold.org/rss/news", "trust": 0.90, "tier": 2, "kind": "metals"},
    "lbma-native":             {"name": "LBMA", "rss": "https://www.lbma.org.uk/rss/news", "trust": 0.86, "tier": 2, "kind": "metals"},
    "metalsfocus-native":      {"name": "MetalsFocus", "rss": "https://www.metalsfocus.com/feed/", "trust": 0.82, "tier": 2, "kind": "metals"},
    "bullionstar-native":      {"name": "BullionStar", "rss": "https://www.bullionstar.com/blogs/feed/", "trust": 0.74, "tier": 2, "kind": "metals"},
    "northern-miner-native":   {"name": "Northern Miner", "rss": "https://www.northernminer.com/feed/", "trust": 0.76, "tier": 2, "kind": "metals"},
    "forexlive-native":        {"name": "ForexLive", "rss": "https://forexlive.com/feed", "trust": 0.74, "tier": 2, "kind": "metals"},
    "wolfstreet-metals-native":{"name": "WolfStreet Metals", "rss": "https://wolfstreet.com/category/precious-metals/feed/", "trust": 0.78, "tier": 2, "kind": "metals"},
    "doomberg-native":         {"name": "Doomberg", "rss": "https://doomberg.com/feed/", "trust": 0.68, "tier": 2, "kind": "metals"},
    "silverinst-native":       {"name": "Silver Institute", "rss": "https://silverinstitute.org/feed/", "trust": 0.84, "tier": 2, "kind": "metals"},
    "prnewswire-metals-native":{"name": "PRNewswire Metals", "rss": "https://www.prnewswire.com/rss/precious-metals-list.rss", "trust": 0.66, "tier": 2, "kind": "metals"},

    # ── FX (forex) ─────────────────────────────────────────────────────

    # ── Macro / traditional finance ─────────────────────────────────────
    "marketwatch":    {"name": "MarketWatch",     "rss": "https://feeds.content.dowjones.io/public/rss/mw_topstories", "trust": 0.85, "tier": 2, "kind": "macro"},
    "ft-markets":     {"name": "Financial Times Markets", "rss": "https://www.ft.com/markets?format=rss",   "trust": 0.90, "tier": 1, "kind": "macro"},
    "ft-news":        {"name": "Financial Times News", "rss": "https://www.ft.com/news-feed?format=rss",    "trust": 0.90, "tier": 1, "kind": "macro"},
    "cnbc-econ":      {"name": "CNBC Economy",    "rss": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258", "trust": 0.85, "tier": 2, "kind": "macro"},
    "cnbc-top":       {"name": "CNBC Top News",   "rss": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", "trust": 0.85, "tier": 2, "kind": "macro"},
    "cnbc-finance":   {"name": "CNBC Finance",    "rss": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147", "trust": 0.85, "tier": 2, "kind": "macro"},
    "cnbc-tech":      {"name": "CNBC Tech",       "rss": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910", "trust": 0.80, "tier": 3, "kind": "macro"},
    "fed-press":      {"name": "Federal Reserve",  "rss": "https://www.federalreserve.gov/feeds/press_all.xml", "trust": 0.97, "tier": 1, "kind": "macro"},
    "yahoo-finance":  {"name": "Yahoo Finance",   "rss": "https://finance.yahoo.com/news/rssindex",        "trust": 0.78, "tier": 2, "kind": "macro"},
    "zerohedge":      {"name": "ZeroHedge",       "rss": "https://feeds.feedburner.com/zerohedge/feed",    "trust": 0.60, "tier": 3, "kind": "macro"},

    # ── Research / deep analysis ────────────────────────────────────────
    "messari":        {"name": "Messari",         "rss": "https://messari.io/rss",                         "trust": 0.82, "tier": 2, "kind": "research"},
    "bitmexresearch": {"name": "BitMEX Research", "rss": "https://blog.bitmex.com/feed/",                  "trust": 0.85, "tier": 1, "kind": "research"},
    "rekt":           {"name": "Rekt News",       "rss": "https://rekt.news/feed/",                        "trust": 0.78, "tier": 2, "kind": "research"},
    "seekingalpha":   {"name": "Seeking Alpha",   "rss": "https://seekingalpha.com/market_currents.xml",   "trust": 0.68, "tier": 3, "kind": "research"},
    "coinmetrics":    {"name": "Coin Metrics",    "rss": "https://coinmetrics.io/feed/",                   "trust": 0.85, "tier": 1, "kind": "research"},
    "glassnode":      {"name": "Glassnode",       "rss": "https://insights.glassnode.com/rss/",            "trust": 0.85, "tier": 1, "kind": "research"},

    # ── Tier-1 wire headlines (official publisher RSS — free, key-less).
    #    Headline + summary only, but exactly what wire coverage needs. ────
    "bloomberg":      {"name": "Bloomberg",         "rss": "https://feeds.bloomberg.com/news.rss",           "trust": 0.95, "tier": 1, "kind": "macro"},
    "bloomberg-mkts": {"name": "Bloomberg Markets", "rss": "https://www.bloomberg.com/feeds/markets/news.rss", "trust": 0.95, "tier": 1, "kind": "macro"},
    "bloomberg-biz":  {"name": "Bloomberg Business", "rss": "https://www.bloomberg.com/feeds/business/news.rss", "trust": 0.95, "tier": 1, "kind": "macro"},
    "wsj-markets":    {"name": "WSJ Markets",       "rss": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",  "trust": 0.90, "tier": 1, "kind": "macro"},
    "wsj-business":   {"name": "WSJ Business",      "rss": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", "trust": 0.90, "tier": 1, "kind": "macro"},
    "marketwatch-pulse": {"name": "MarketWatch Pulse", "rss": "https://feeds.marketwatch.com/marketwatch/marketpulse/", "trust": 0.85, "tier": 2, "kind": "macro"},
    "forexlive":      {"name": "ForexLive",         "rss": "https://www.forexlive.com/feed/news",            "trust": 0.74, "tier": 2, "kind": "macro"},
    "benzinga":       {"name": "Benzinga",          "rss": "https://www.benzinga.com/feed",                  "trust": 0.70, "tier": 3, "kind": "macro"},

    # ── Barchart (free RSS — commodities, metals, energy, crypto, FX, rates)

    # ── ECB (European Central Bank) ─────────────────────────────────────
    "ecb-press":          {"name": "ECB Press Releases",   "rss": "https://www.ecb.europa.eu/rss/press.html", "trust": 0.95, "tier": 1, "kind": "macro"},

    # ── Additional wire / macro feeds ───────────────────────────────────
    "bloomberg-wealth":   {"name": "Bloomberg Wealth",     "rss": "https://feeds.bloomberg.com/wealth/news.rss", "trust": 0.92, "tier": 1, "kind": "macro"},
    "ft-crypto":          {"name": "FT Crypto",            "rss": "https://www.ft.com/crypto?format=rss", "trust": 0.90, "tier": 1, "kind": "crypto"},
    "nyt-economy":        {"name": "NYT Economy",          "rss": "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml", "trust": 0.85, "tier": 2, "kind": "macro"},
    "fool-investing":     {"name": "Motley Fool Investing","rss": "https://www.fool.com/feeds/index.aspx", "trust": 0.62, "tier": 3, "kind": "research"},
    # ── Additional working feeds ────────────────────────────────────────
    "bbc-business":     {"name": "BBC Business",      "rss": "https://feeds.bbci.co.uk/news/business/rss.xml", "trust": 0.82, "tier": 2, "kind": "macro"},
    "investing-crypto": {"name": "Investing.com Crypto","rss": "https://www.investing.com/rss/news_301.rss",    "trust": 0.78, "tier": 2, "kind": "crypto"},
    "ct-defi":          {"name": "CoinTelegraph DeFi", "rss": "https://cointelegraph.com/rss/tag/defi",         "trust": 0.84, "tier": 2, "kind": "crypto"},

    # ── FXEmpire's own outbound sources (2026-09 — user-supplied list; the
    #    six that were missing from the roster above). Feeds discovered and
    #    verified live: every one answers 200 with items. ───────────────────
    "cointribune":      {"name": "Coin Tribune",   "rss": "https://www.cointribune.com/feed/",               "trust": 0.66, "tier": 2, "kind": "crypto"},
    "invezz":           {"name": "Invezz",         "rss": "https://www.invezz.com/feed/",                    "trust": 0.68, "tier": 2, "kind": "crypto"},
    "unchained":        {"name": "Unchained",      "rss": "https://unchainedcrypto.com/feed/",               "trust": 0.70, "tier": 2, "kind": "crypto"},
    "dailycoin":        {"name": "DailyCoin",      "rss": "https://dailycoin.com/feed/",                    "trust": 0.64, "tier": 3, "kind": "crypto"},    "coinpaper":      {"name": "Coinpaper",      "rss": "https://coinpaper.com/feed",                     "trust": 0.62, "tier": 3, "kind": "crypto"},
    "cryip":          {"name": "Cryip",          "rss": "https://cryip.co/rss",                           "trust": 0.62, "tier": 3, "kind": "crypto"},

    # ── English-language republishers of Bloomberg / Reuters / FT / WSJ
    #    content (screened 2026-09-27). Criteria: English, free, market-
    #    focused, live RSS verified, and their output passes
    #    is_relevant()/validate_article() once SPORTS_NOISE is applied.
    #    Section feeds are used where the site exposes one (Dawn Business,
    #    Euronews Business, ET/LiveMint/Business-Standard markets desks) so
    #    general-news noise never enters the pipeline. ───────────────────
    "et-markets":       {"name": "Economic Times Markets", "rss": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "trust": 0.72, "tier": 2, "kind": "macro"},
    "business-standard": {"name": "Business Standard Markets", "rss": "https://www.business-standard.com/rss/markets-106.rss",   "trust": 0.72, "tier": 2, "kind": "macro"},
    "livemint":         {"name": "LiveMint Markets",      "rss": "https://www.livemint.com/rss/markets",                        "trust": 0.72, "tier": 2, "kind": "macro"},
    "businessline":     {"name": "Hindu BusinessLine",    "rss": "https://www.thehindubusinessline.com/feeder/default.rss",    "trust": 0.70, "tier": 2, "kind": "macro"},
    "dawn-business":    {"name": "Dawn Business",         "rss": "https://www.dawn.com/feeds/business",                          "trust": 0.74, "tier": 2, "kind": "macro"},
    "euronews-biz":     {"name": "Euronews Business",     "rss": "https://www.euronews.com/rss?level=vertical&name=business",   "trust": 0.72, "tier": 2, "kind": "macro"},
    "finwire":          {"name": "Finwire",               "rss": "https://finwire.io/rss.xml",                                    "trust": 0.70, "tier": 2, "kind": "macro"},
    "marketnews":       {"name": "Market.News",            "rss": "https://market.news/rss.xml",                                   "trust": 0.66, "tier": 3, "kind": "macro"},
    "thestreet":        {"name": "TheStreet",             "rss": "https://www.thestreet.com/.rss/full/",                          "trust": 0.70, "tier": 3, "kind": "macro"},
    "ibd":              {"name": "Investor's Business Daily", "rss": "https://investors.com/feed/",                                "trust": 0.66, "tier": 3, "kind": "research"},
    "gulfnews":         {"name": "Gulf News",              "rss": "https://gulfnews.com/feed/",                                     "trust": 0.66, "tier": 3, "kind": "macro"},
    "hurriyet-dn":      {"name": "Hurriyet Daily News",   "rss": "https://hurriyetdailynews.com/rss/news",                         "trust": 0.64, "tier": 3, "kind": "macro"},
    # Screened OUT of this batch (2026-09-27): Yonhap / Korea Herald /
    # Korea Times — general wires whose medal tables are now filtered but
    # whose remaining output is politics + chip-industry news outside the
    # tracked assets (measured yield: 0 articles / 60 raw). Business Insider
    # (no markets feed) and Business Day NG (stale) likewise yielded nothing
    # useful. Moneycontrol, NDTV Profit, CNBC-TV18, Business Recorder, The
    # News and Gulf News' section feeds expose no parseable RSS at all.

    # ── MASTER-file screen (2026-09-28): candidates from the user's
    #    crypto_sources_MASTER.md plus own web research. Every feed below
    #    was probed live: HTTP 200, parseable RSS, items in the last 72h,
    #    and ≥50% is_relevant() pass-rate on sampled titles. Rejected from
    #    the same file: wublock.com/feed (timeouts), wublockprint (dead
    #    host), weekinethereumnews (SSL error), milkroad + delphidigital +
    #    galaxy.com/research + goldtelegraph (200 but zero entries),
    #    binance-research (HTTP 202, no body), coinbase blog + goldsilver
    #    (403), paradigm / mechanism / defireports / gold.org / bullionvault
    #    / miningweekly (404), azcoinnews (503), crypto-news.land +
    #    coinpath.io (timeouts). Newsletters (substacks) are live but their
    #    72h output is thin; kept only the asset-focused ones. ──────────
    "nftevening":      {"name": "NFT Evening",       "rss": "https://nftevening.com/feed/",               "trust": 0.62, "tier": 3, "kind": "crypto"},
    "bankless":        {"name": "Bankless",          "rss": "https://bankless.com/feed",                  "trust": 0.74, "tier": 2, "kind": "crypto"},
    "a16zcrypto":      {"name": "a16z Crypto",      "rss": "https://a16zcrypto.com/feed/",               "trust": 0.82, "tier": 2, "kind": "research"},
    "blockchainrep":   {"name": "Blockchain Reporter", "rss": "https://blockchainreporter.net/feed/",      "trust": 0.64, "tier": 3, "kind": "crypto"},
    "bitcoinke":       {"name": "BitcoinKE",         "rss": "https://bitcoinke.io/feed/",                 "trust": 0.64, "tier": 3, "kind": "crypto"},
    "kingworldnews":   {"name": "King World News",   "rss": "https://kingworldnews.com/feed",             "trust": 0.62, "tier": 3, "kind": "metals"},
    "goldseek":        {"name": "GoldSeek",          "rss": "https://news.goldseek.com/newsRSS.xml",      "trust": 0.70, "tier": 2, "kind": "metals"},
    "financemagnates": {"name": "Finance Magnates",   "rss": "https://www.financemagnates.com/feed/",      "trust": 0.70, "tier": 2, "kind": "macro"},
    "actionforex":     {"name": "Action Forex",       "rss": "https://www.actionforex.com/feed/",           "trust": 0.66, "tier": 3, "kind": "macro"},

    # ── Newsletters (MASTER file, probed live, asset-focused picks) ────
    "rektcapital":     {"name": "Rekt Capital",      "rss": "https://rektcapital.substack.com/feed",      "trust": 0.72, "tier": 3, "kind": "research"},
    "pomp":            {"name": "The Pomp Letter",    "rss": "https://pomp.substack.com/feed",             "trust": 0.70, "tier": 3, "kind": "research"},
    "cobie":           {"name": "Cobie",             "rss": "https://cobie.substack.com/feed",            "trust": 0.72, "tier": 3, "kind": "research"},
    "tokenunlocks":    {"name": "Token Unlocks",      "rss": "https://tokenunlocks.substack.com/feed",     "trust": 0.68, "tier": 3, "kind": "research"},

    # ── Expansion 2026-10-06 (each URL verified live: HTTP 200 + items) ──
    "fed-press":       {"name": "Federal Reserve Press", "rss": "https://www.federalreserve.gov/feeds/press_all.xml", "trust": 0.95, "tier": 1, "kind": "macro"},
    "ecb-press":       {"name": "ECB Press",        "rss": "https://www.ecb.europa.eu/rss/press.html",   "trust": 0.95, "tier": 1, "kind": "macro"},
    "wsj-markets":     {"name": "WSJ Markets",      "rss": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", "trust": 0.92, "tier": 1, "kind": "macro"},
    "cryptopolitan":   {"name": "Cryptopolitan",    "rss": "https://www.cryptopolitan.com/feed/",        "trust": 0.74, "tier": 3, "kind": "crypto"},
    # Persian wires — native Persian skips the translator (see translate guard)
    "donya-eqtesad":   {"name": "دنیای اقتصاد",      "rss": "https://donya-e-eqtesad.com/rss",            "trust": 0.80, "tier": 3, "kind": "macro"},
    "eghtesadonline":  {"name": "اقتصاد آنلاین",     "rss": "https://www.eghtesadonline.com/rss",         "trust": 0.78, "tier": 3, "kind": "macro"},
    "isna":            {"name": "ایسنا",             "rss": "https://www.isna.ir/rss",                    "trust": 0.82, "tier": 3, "kind": "macro"},
    "mehrnews":        {"name": "خبرگزاری مهر",      "rss": "https://www.mehrnews.com/rss",               "trust": 0.78, "tier": 3, "kind": "macro"},
    "tejaratnews":     {"name": "تجارت نیوز",        "rss": "https://tejaratnews.com/rss",                "trust": 0.72, "tier": 3, "kind": "macro"},
    "arzdigital":      {"name": "ارز دیجیتال",       "rss": "https://arzdigital.com/feed/",               "trust": 0.72, "tier": 3, "kind": "crypto"},

    # ── Reddit subs (MASTER file, probed: r/DeFi yields real discussion
    #    within 72h; r/CryptoTechnology throttles 429; r/altcoin is pinned
    #    posts only). r/CryptoCurrency + r/Bitcoin already in the roster. ──
    "reddit-defi":     {"name": "r/DeFi (شبکه اجتماعی)", "rss": "https://www.reddit.com/r/DeFi/.rss", "trust": 0.50, "tier": 4, "kind": "social", "sequential": True},
}

# ── Per-asset Google News queries (free, key-less, very wide reach) ─────
_GNEWS_TMPL = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
_GNEWS_QUERIES = [
    ("BTC",  "bitcoin price OR BTC"),
    ("ETH",  "ethereum price OR ETH"),
    ("SOL",  "solana price OR SOL"),
    ("XRP",  "xrp ripple price"),
    ("ADA",  "cardano ada price"),
    ("BNB",  "binance coin BNB price"),
    ("DOGE", "dogecoin price"),
    ("XAU",  "gold price ounce"),
    ("XAG",  "silver price ounce"),
    ("MACRO", "federal reserve inflation rates"),
    ("ETF",   "bitcoin ethereum etf flows"),
    ("CRYPTO", "cryptocurrency market news"),
]
for _sym, _q in _GNEWS_QUERIES:
    SOURCES[f"gnews-{_sym.lower()}"] = {
        "name": f"Google News · {_sym}", "rss": _GNEWS_TMPL.format(q=quote_plus(_q)),
        "trust": 0.66, "tier": 2, "kind": "search", "asset": _sym,
    }

# ── Wire-site Google News filters: full headline stream of the paywalled
#    origins (Bloomberg/Reuters/WSJ/FT) without any paywall — Google indexes
#    their public headlines and attributes the real publisher, which
#    publisher_trust() scores at wire level. ──────────────────────────────
_GNEWS_WIRES = [
    ("bloomberg", "when:48h site:bloomberg.com (crypto OR bitcoin OR fed OR inflation OR markets OR gold OR oil OR rates OR currency)"),
    ("reuters",   "when:48h site:reuters.com (crypto OR bitcoin OR fed OR inflation OR markets OR gold OR oil OR currency OR rates)"),
    ("wsj",       "when:48h site:wsj.com (crypto OR bitcoin OR fed OR inflation OR markets OR gold OR stocks OR federal reserve)"),
    ("ft",        "when:48h site:ft.com (crypto OR bitcoin OR fed OR inflation OR markets OR gold OR federal reserve OR central bank)"),
]
for _w, _q in _GNEWS_WIRES:
    SOURCES[f"gnews-wire-{_w}"] = {
        "name": f"Google News · {_w.upper()} wire", "rss": _GNEWS_TMPL.format(q=quote_plus(_q)),
        "trust": 0.70, "tier": 2, "kind": "search",
    }

# ── Social (Reddit RSS). Reddit throttles hard, so these are fetched
#    sequentially with a delay and failures are tolerated. ──────────────
_REDDIT_SUBS = ["Bitcoin", "CryptoCurrency", "ethereum", "solana", "Ripple",
                "CardanoCoin", "dogecoin", "CryptoMarkets", "Gold", "Silverbugs"]
for _sub in _REDDIT_SUBS:
    SOURCES[f"reddit-{_sub.lower()}"] = {
        "name": f"r/{_sub} (شبکه اجتماعی)",
        "rss": f"https://www.reddit.com/r/{_sub}/.rss",
        "trust": 0.50, "tier": 4, "kind": "social", "sequential": True,
    }

# ── Publisher trust: Google News items are attributed to the real
#    publisher, so we can score them like any other outlet. ─────────────
PUBLISHER_TRUST = {
    "reuters": 0.95, "bloomberg": 0.95, "financial times": 0.90, "wall street journal": 0.90,
    "the wall street journal": 0.90, "cnbc": 0.85, "barron's": 0.85, "forbes": 0.72,
    "coindesk": 0.95, "cointelegraph": 0.86, "the block": 0.90, "decrypt": 0.85,
    "blockworks": 0.85, "kitco": 0.80, "investing.com": 0.80, "marketwatch": 0.85,
    "yahoo finance": 0.78, "business insider": 0.72, "fortune": 0.80, "axios": 0.80,
    "the economist": 0.92, "associated press": 0.92, "ap news": 0.92, "abc news": 0.75,
    "cbs news": 0.75, "nbc news": 0.75, "cnn": 0.74, "newsweek": 0.70, "the guardian": 0.82,
    "benzinga": 0.70, "seeking alpha": 0.68, "beincrypto": 0.75, "cryptoslate": 0.75,
    "cryptopotato": 0.72, "ambcrypto": 0.75, "coingape": 0.66, "u.today": 0.62,
    "bitcoinist": 0.70, "newsbtc": 0.74, "daily hodl": 0.70, "the defiant": 0.80,
    "protos": 0.80, "dl news": 0.80, "crypto briefing": 0.78, "finbold": 0.70,
    "watcher guru": 0.68, "coinpedia": 0.62, "coincu": 0.66, "cryptodaily": 0.66,
    "mining.com": 0.78, "fxempire": 0.82, "fx empire": 0.82, "fxempire.com": 0.82,
    "fxstreet": 0.82, "fx street": 0.82, "fxstreet.com": 0.82, "oilprice": 0.74, "zerohedge": 0.60,
    "the street": 0.70, "thestreet": 0.70, "motley fool": 0.60, "investopedia": 0.78,
    "moneyweb": 0.65, "theprint": 0.60, "times of india": 0.62, "the hindu": 0.70,
    "forexlive": 0.74, "investinglive": 0.74,
    "coin tribune": 0.66, "invezz": 0.68, "unchained": 0.70, "unchained crypto": 0.70,
    "dailycoin": 0.64, "coinpaper": 0.62, "cryip": 0.62,
    # republishers added 2026-09-27 (screened batch)
    "economic times": 0.72, "et markets": 0.72, "business standard": 0.72,
    "livemint": 0.72, "mint": 0.72, "the hindu businessline": 0.70,
    "hindu businessline": 0.70, "businessline": 0.70, "dawn": 0.74,
    "dawn news": 0.74, "euronews": 0.72, "finwire": 0.70, "market.news": 0.66,
    "marketnews": 0.66, "gulf news": 0.66, "hurriyet daily news": 0.64,
    "investor's business daily": 0.66, "investors business daily": 0.66,
    "yonhap news": 0.76, "yonhap": 0.76, "korea herald": 0.70,
    "korea times": 0.66,
    # MASTER-file screen 2026-09-28
    "nft evening": 0.62, "bankless": 0.74, "a16z crypto": 0.82,
    "blockchain reporter": 0.64, "bitcoinke": 0.64, "king world news": 0.62,
    "goldseek": 0.70, "finance magnates": 0.70, "action forex": 0.66,
    "rekt capital": 0.72, "the pomp letter": 0.70, "pomp": 0.70,
    "anthony pompliano": 0.70, "cobie": 0.72, "token unlocks": 0.68,
}
PUBLISHER_TRUST_DEFAULT = 0.64

KIND_LABELS = {
    "crypto":   "کریپتو",
    "metals":   "فلزات و کالا",
    "macro":    "اقتصاد کلان",
    "research": "پژوهش و تحلیل",
    "search":   "جستجوی خبری (گوگل نیوز)",
    "social":   "شبکه‌های اجتماعی",
}


# ---------------------------------------------------------------------------
# CREDIBILITY MODEL
# ---------------------------------------------------------------------------
QUALITY_PENALTIES = {
    "sponsored": 0.35,
    "clickbait": 0.15,
    "too_short": 0.20,
    "risky_words": 0.10,
    "seo_farm": 0.15,        # "price today / live price" style pages
}

SPONSORED_MARKERS = re.compile(
    r"\bsponsored\b|\badvertorial\b|\bpress release\b|\bpr manager\b|\bblockmanpr\b|"
    r"\bpartner content\b|\bbrought to you by\b|\bin partnership with\b|\bweb3wire\b|"
    r"\bpaid (?:post|content)\b|\bmedia release\b|\bmorningstar branded\b",
    re.I,
)

CLICKBAIT_PATTERNS = re.compile(
    r"\b(?:1000x|100x|10x)\b|\bmoon\b|\bto the moon\b|\bguaranteed\b|\bshocking\b|"
    r"\byou won'?t believe\b|\bthis changes everything\b|\blast chance\b|"
    r"\bexplosive growth\b|\bhuge gain\w*\b|\binsane\b|\bcrazy\b|\bnobody is talking about\b|"
    r"\bheres why\b|\bsecret\b|\bget rich\b|\bnext bitcoin\b|\bnext big thing\b|"
    r"\bmust (?:buy|hold) now\b|\bprice explod\w*\b|\bwill 100\b",
    re.I,
)

RISKY_CLAIMS = re.compile(
    r"\bguaranteed (?:return|profit)s?\b|\brisk-?free\b|\b100% (?:sure|certain|guaranteed)\b|"
    r"\bcan'?t (?:lose|fail)\b|\bprice (?:will )?(?:definitely|certainly) (?:go|reach)\b",
    re.I,
)

# Low-substance SEO pages that Google News surfaces a lot. These are hard
# rejected — they are price-ticker templates, not journalism, and they used to
# pollute the report citations.
SEO_FARM_PATTERNS = re.compile(
    r"\blive (?:gold|silver|bitcoin|crypto|price) price\b|\bprice (?:today|now)\b|"
    r"\bhow to buy\b|\bprice prediction \d{4}\b|\bbest (?:crypto|coins?) to buy\b|"
    r"\b\d+ best \w+ to buy\b|\bconverter\b|\bcalculator\b|\bmonth day, year\b|"
    r"\bprice in (?:usd|inr|cad|aud|eur|gbp|pk|php)\b|\bprice of \w+ as of\b|"
    r"\bcurrent price of\b|\bprice forecast \d{4}\b|\bprice target \d{4}\b",
    re.I,
)


def publisher_trust(publisher: str) -> float:
    if not publisher:
        return PUBLISHER_TRUST_DEFAULT
    return PUBLISHER_TRUST.get(publisher.strip().lower(), PUBLISHER_TRUST_DEFAULT)


def make_id(title: str, link: str) -> str:
    return hashlib.md5((title.strip().lower() + "|" + link).encode("utf-8")).hexdigest()[:12]


def classify_topic(title: str, summary: str = "") -> str:
    text = f"{title} {summary}"
    for topic in ("security", "etf", "regulation", "institutional",
                  "macro", "analysis", "defi", "market", "tech"):
        if _TOPIC_COMPILED[topic].search(text):
            return topic
    return "general"


# ---------------------------------------------------------------------------
# RELEVANCE GATE
# ---------------------------------------------------------------------------
# Broad finance feeds (Yahoo Finance, Investing.com, Seeking Alpha, general
# macro wires) also carry company earnings, dividends and stock-picking noise.
# An article is only kept when it either matches a tracked asset or plainly
# belongs to crypto / metals / monetary-policy coverage.
RELEVANCE_PATTERN = re.compile(
    r"\bbitcoin\b|\bbtc\b|\bcrypto\w*\b|\bethereum\b|\bether\b|\bblockchain\b|"
    r"\bstablecoin\w*\b|\btoken\w*\b|\bdefi\b|\betf\b|\baltcoin\w*\b|\bsatoshi\b|"
    r"\bdigital asset\w*\b|\bweb3\b|\bmeme coin\w*\b|\bhalving\b|\bmining\b|"
    r"\bhashrate\b|\b(?:crypto\w*|digital) exchange\w*\b|\bstock exchange\w*\b|\bexchange rate\w*\b|\bbinance\b|\bcoinbase\b|\bkraken\b|\bokx\b|"
    r"\bsec\b|\bcftc\b|\bregulat\w*\b|\bfederal reserve\b|\bfed\b|\bfomc\b|"
    r"\binflation\b|\bcpi\b|\bpce\b|\binterest rate\w*\b|\brate (?:cut|hike)\w*\b|"
    r"\btreasury yield\w*\b|\bdollar index\b|\bdxy\b|\bliquidity\b|\bpowell\b|"
    r"\bgold\b|\bsilver\b|\bbullion\b|\bprecious metal\w*\b|\bcomex\b|"
    r"\bripple\b|\bxrp\b|\bsolana\b|\bcardano\b|\bdogecoin\b|\btether\b|\busdt\b|"
    r"\bcoin\b|\baltcoins?\b|\bwallet\w*\b|\bnft\w*\b|\bdex\b|\bcex\b|"
    r"\bstaking\b|\bairdrop\w*\b|\btokeniz\w*\b|\brwa\b|\bdapp\w*\b|\bmainnet\b|"
    r"\bbull run\b|\bbear market\b|\bcrypto market\b|\bdigital currency\b|"
    r"\bmonetary policy\b|\btariff\w*\b|\bcentral bank\w*\b|"
    r"\bforex\b|\bcurrencies\b|\bcurrency\b|\bfx\b|\beur/?usd\b|\bgbp/?usd\b|\busd/?jpy\b|\baud/?usd\b|\busd/?cad\b|\byen\b|\beuro\b|\bpound\b|"
    # commodities & indices — needed because is_relevant() now asks the
    # headline first: a story whose headline says "crude" / "Wall Street"
    # must still qualify even when it names no tracked asset verbatim.
    r"\boil (?:prices?|markets?|output|supplies|supply|demand|production)\b|"
    r"\bcrude\b|\bbrent\b|\bopec\b|\bnatural gas\b|\bwti\b|"
    r"\bnasdaq\b|\bdow jones\b|\bs&p 500\b|\bwall street\b|\bstock market\b|"
    r"\bnifty\b|\bsensex\b",
    re.I,
)


# Stock-market boilerplate that occasionally slips through the "ETF" keyword.
NOISE_PATTERN = re.compile(
    r"\bdeclares? (?:quarterly |monthly |special )?(?:distribution|dividend)\b|"
    r"\bgoes? ex-dividend\b|\bdividend (?:declared|yield|per share)\b|"
    r"\b(?:stock|shares?) (?:hits?|rise|rises|fall|falls|jumps?|slides?) (?:to )?(?:52-week|all-time|record)\b|"
    r"\bhits? (?:52-week|all-time) (?:high|low)\b|\binsider (?:trading|selling|buying)\b|"
    r"\b(?:sells?|sold|buys?) [\d.,]+ ?(?:m|million|k)? ?(?:shares?|stock)\b|"
    r"\bfiles? (?:confidentially )?for (?:an? )?ipo\b|\bquarterly earnings\b|"
    r"\b(?:director|ceo|cfo) .{0,30}(?:sells?|buys?) [\d,]+ shares\b|"
    r"\bannual meeting\b|\bprice target\b",
    re.I,
)

# Sports & award coverage carried by the general wires (Yonhap, Korea Times,
# Korea Herald, Euronews…). "S. Korea captures gold in women's sabre" used to
# match XAU/XAG and sail in through the asset shortcut. Never market news, so
# it is rejected before anything else — checked on the headline only.
SPORTS_NOISE_PATTERN = re.compile(
    r"\b(?:asian games|asiad|olympi\w*|medals?\b|fencing|sabre\b|epee\b|handball|"
    r"skateboarding|equestrian|dressage|synchroni[sz]ed (?:diving|swimming)|\bdivers\b|"
    r"weightlifting|world cup|championship\w*|grand prix|super bowl|"
    r"(?:wins?|won|claims?|claimed|captures?|captured|grabs?|grabbed|bags?|bagged|"
    r"nabs?|nabbed|secures?|secured) (?:the )?(?:gold|silver|bronze)|"
    r"(?:gold|silver|bronze) medal|"
    r"\b(?:women|men|mixed)[-' ](?:team|event|singles|doubles|relay|final)\b)",
    re.I,
)


# Junk templates that are rejected no matter which asset words the headline
# happens to contain — Indian/US stock-picking SEO ("stocks to buy | Target,
# SL"), IPO filings, dividend and insider boilerplate. Checked before the
# headline-asset shortcut, unlike NOISE_PATTERN which only applies when no
# tracked asset is named (it contains "price target", which must NOT kill a
# legitimate "gold price target $4,000" headline).
HARD_NOISE_PATTERN = re.compile(
    r"\b(?:top |best )?(?:stocks?|shares?) to buy\b|\btop stocks\b|"
    r"\bstock picks?\b|\bstock selection\b|\btarget,? sl\b|\bbuy points?\b|"
    r"\bpicks? \d+ stocks\b|\braise stakes in \d+ stocks\b|\bshare price\b|"
    r"\bdrhp\b|\bfresh issue\b|\bipo (?:papers?|filing|stock)\b|"
    r"\bfiles? (?:for (?:an? )?)?(?:draft )?(?:red herring )?prospectus\b|"
    r"\bgoes? ex-dividend\b|\bdividend (?:declared|yield|per share)\b|"
    r"\binsider (?:trading|selling|buying)\b|\bannual meeting\b|"
    r"\bhits? (?:52-week|all-time) (?:high|low)\b",
    re.I,
)


def is_relevant(assets, title: str, summary: str = "", custom=None) -> bool:
    """Tracked asset hit, or clearly crypto / metals / macro monetary news.

    Order matters:
      1. sports/medal headlines are never market news (see SPORTS_NOISE_PATTERN);
      2. hard junk templates (stock-picking SEO, IPO filings) are rejected even
         when the headline names an asset;
      3. an asset named in the *headline* is enough on its own;
      4. otherwise the headline must survive the noise screen and the whole
         text must look like coverage we track — a stray "oil" buried in a
         summary must not promote an unrelated story to WTI.
    """
    if SPORTS_NOISE_PATTERN.search(title):
        return False
    if HARD_NOISE_PATTERN.search(title):
        return False
    if detect_assets(title, "", custom):
        return True
    if NOISE_PATTERN.search(title):
        return False
    text = f"{title} {summary[:400]}"
    return bool(RELEVANCE_PATTERN.search(text))


# keyword separators people actually type: comma, semicolon, pipe, slash,
# newline, or a dash SET OFF BY A SPACE BEFORE IT ("- kw" and "-kw" both
# split; a bare hyphen inside a slug does not: "wrapped-bitcoin" stays one
# keyword, "pepe-usdt" stays one keyword).
_KW_SPLIT = re.compile(r"[,;|\n\r/]|\s+[-–—]\s*")


def split_keywords(raw):
    """'link - chanlink -linkusdt' -> ['link', 'chanlink', 'linkusdt']"""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        parts = list(raw)
    else:
        parts = _KW_SPLIT.split(str(raw))
    out = []
    for p in parts:
        tok = str(p).strip().strip("-#*").strip()
        if len(tok) >= 2 and tok not in out:
            out.append(tok)
    return out


def build_custom_patterns(custom_assets: dict) -> dict:
    """
    custom_assets: {SYM: {"keywords": "a, b - c" , "keywords_regex": "..."}}
    Returns {SYM: compiled regex} used in addition to the built-in patterns.
    """
    out = {}
    for sym, meta in (custom_assets or {}).items():
        pats = []
        for k in split_keywords(meta.get("keywords")):
            # a multi-word phrase should tolerate any spacing
            pats.append(re.sub(r'\s+', r'\\s+', re.escape(k)))
        if meta.get("keywords_regex"):
            pats.append(meta["keywords_regex"])
        if not pats:
            pats = [re.escape(sym)]
        try:
            out[sym] = re.compile(r"\b(?:%s)\b" % "|".join(pats), re.I)
        except re.error:
            continue
    return out


def detect_assets(title: str, summary: str = "", custom=None):
    """custom: {SYM: compiled regex} from build_custom_patterns()."""
    text = f"{title} {summary}".lower()
    found = [a for a, pat in _ASSET_PATTERNS.items() if re.search(pat, text)]
    for sym, pat in (custom or {}).items():
        if sym not in found and pat.search(text):
            found.append(sym)
    if not found and re.search(r"\bcrypto\b|\bbitcoin\b", text):
        found = ["BTC"]
    return found


def validate_article(art: dict, source_trust: float, now=None,
                     max_age: float = MAX_AGE_HOURS) -> dict:
    """
    Content validation & credibility scoring (0..1).
    Hard reject: sponsored PR, spam topics, empty titles, anything older
    than `max_age` hours (72h by default — user configurable).
    Soft penalties: clickbait, thin body, risky claims, SEO farm pages.
    """
    now = now or datetime.now(timezone.utc)
    title = (art.get("title") or "").strip()
    summary = (art.get("summary") or "").strip()
    link = (art.get("link") or "").strip()

    reasons = []

    if len(title) < 20:
        return {"valid": False, "reasons": ["title_too_short"], "credibility": 0.0}
    if SPONSORED_MARKERS.search(f"{title} {summary}"):
        return {"valid": False, "reasons": ["sponsored"], "credibility": 0.0}
    if re.search(r"\b(?:bet|casino|casinos|slots?|porn|xxx)\b", title, re.I):
        return {"valid": False, "reasons": ["spam_topic"], "credibility": 0.0}
    if SEO_FARM_PATTERNS.search(title):
        return {"valid": False, "reasons": ["seo_page"], "credibility": 0.0}

    pub_ts = art.get("published_ts")
    if pub_ts is None:
        pub_ts = now.timestamp()
    age_hours = None
    if isinstance(pub_ts, (int, float)):
        age_hours = max(0.0, (now.timestamp() - pub_ts) / 3600.0)
        if age_hours > max_age:
            return {"valid": False, "reasons": ["stale"], "credibility": 0.0}

    score = source_trust
    if CLICKBAIT_PATTERNS.search(title):
        score -= QUALITY_PENALTIES["clickbait"]
        reasons.append("clickbait")
    if len(summary) < 40:
        score -= QUALITY_PENALTIES["too_short"]
        reasons.append("thin_content")
    if RISKY_CLAIMS.search(f"{title} {summary}"):
        score -= QUALITY_PENALTIES["risky_words"]
        reasons.append("risky_claims")
    if SPONSORED_MARKERS.search(link):
        score -= QUALITY_PENALTIES["sponsored"]
        reasons.append("sponsored_link")

    if age_hours is not None:
        if age_hours <= 6:
            recency = 1.0
        elif age_hours <= 24:
            recency = 0.96
        elif age_hours <= 48:
            recency = 0.90
        else:
            recency = 0.84
        score *= recency

    score = max(0.05, min(1.0, score))
    return {"valid": True, "reasons": reasons, "credibility": round(score, 3)}
