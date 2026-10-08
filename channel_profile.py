"""channel_profile.py — Editorial news filter and ranker for tgju.org/news.

Filters and ranks foreign/international news discovered across global wire feeds
for publication on the news section of TGJU (https://www.tgju.org/news).

Editorial Pillars:
* Focus: High-impact international financial & markets coverage:
  - Gold & Precious Metals (XAU, Silver, COMEX, Central Banks)
  - Global Macro, Commodities & Oil (Fed, Rates, Inflation, OPEC, Wall Street)
  - Currencies & Forex (DXY, EUR/USD, Central Banks)
  - Crypto & Web3 (BTC, ETH, Sol, ETFs, Regulations, Viral Market Trends)
  - Big Tech & AI (Nvidia, Apple, Microsoft, AI Infrastructure, Nasdaq)
* Hard Exclusion (Off-Profile):
  - Domestic Iranian news ("تومان", "سکه بهار آزادی", "بورس تهران", "کارت ملی"...)
    is excluded because domestic Iranian news is authored by the domestic desk elsewhere.
  - Phishing scams, seed-phrase drainers, and non-financial gossip.
* Viral trends: Market surges, viral meme momentum, and dramatic record breakouts
  are covered and surfaced as high-engagement story ideas.
* Local, deterministic, explainable: No black-box model, Persian & English lexicons.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import persian_words

# ──────────────────────────────────────────────────────────────────────────
# Editorial Desks for tgju.org/news
# ──────────────────────────────────────────────────────────────────────────
# bucket -> (label, badge, emoji, weight, keywords, optional assets)
BUCKETS: Dict[str, Dict[str, Any]] = {
    "gold": {
        "label": "طلا و فلزات گران‌بها",
        "badge": "طلا و فلزات",
        "emoji": "🟡",
        "weight": 1.00,
        "assets": ("XAU", "XAG"),
        "words": (
            "طلا", "طلای", "اونس", "اونس طلا", "زر", "گلد", "زرین", "نقره",
            "پلاتین", "پالادیوم", "فلزات گرانبها", "فلزات گران‌بها", "طلای جهانی",
            "gold", "xau", "bullion", "ounce", "gold price", "gold prices",
            "precious metals", "silver", "xag", "platinum", "palladium", "comex",
            "central bank gold", "safe haven", "safe-haven", "gold reserves",
        ),
    },
    "global": {
        "label": "اقتصاد جهان و نفت",
        "badge": "اقتصاد جهان",
        "emoji": "🌍",
        "weight": 0.95,
        "assets": ("WTI", "BRENT", "SPX", "VIX"),
        "words": (
            "فدرال رزرو", "بانک مرکزی آمریکا", "پاول", "نرخ بهره", "بهره آمریکا",
            "کاهش نرخ بهره", "افزایش نرخ بهره", "تورم", "رکود", "وال استریت", "نفت",
            "برنت", "اوپک", "شاخص اس اند پی", "اوراق قرضه", "بازار جهانی", "اقتصاد جهان",
            "تعرفه", "جنگ تجاری", "داده‌های آمریکا", "اشتغال آمریکا", "صندوق بین‌المللی پول",
            "federal reserve", "fed", "fomc", "powell", "interest rate", "interest rates",
            "rate cut", "rate cuts", "rate hike", "rate hikes", "inflation", "cpi", "pce",
            "ppi", "gdp", "treasury", "treasury yield", "yields", "recession", "wall street",
            "s&p 500", "spx", "dow jones", "opec", "crude", "oil", "brent", "wti", "petroleum",
            "energy", "trade war", "tariffs", "central bank", "world bank", "imf", "labor market",
            "nonfarm", "unemployment",
        ),
    },
    "currency": {
        "label": "ارز و فارکس",
        "badge": "ارز و فارکس",
        "emoji": "💵",
        "weight": 0.90,
        "assets": ("DXY",),
        "ambiguous": ("دلار", "dollar", "usd"),
        "words": (
            "شاخص دلار", "دلار آمریکا", "فارکس", "برابری ارزها", "یورو", "ین", "ین ژاپن",
            "پوند", "پوند انگلیس", "یوان", "یوان چین", "فرانک سوئیس", "بانک مرکزی اروپا",
            "بانک مرکزی ژاپن", "نرخ ارز جهانی",
            "dxy", "dollar index", "us dollar", "greenback", "forex", "fx",
            "eur/usd", "usd/jpy", "gbp/usd", "usd/chf", "aud/usd", "euro", "yen",
            "pound", "sterling", "yuan", "renminbi", "ecb", "boj", "bank of japan",
            "european central bank", "currency pair", "exchange rate",
        ),
    },
    "crypto": {
        "label": "ارز دیجیتال و بلاک‌چین",
        "badge": "ارز دیجیتال",
        "emoji": "₿",
        "weight": 0.95,
        "assets": ("BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "BNB"),
        "words": (
            "بیت کوین", "بیت‌کوین", "بیتکوین", "اتریوم", "کریپتو", "رمزارز",
            "ارز دیجیتال", "استیبل کوین", "سولانا", "ریپل", "تتر", "بایننس",
            "کوین‌بیس", "کمیسیون بورس", "صندوق etf", "صندوق ای تی اف", "هاوینگ",
            "آلت کوین", "آلت‌کوین", "بلاک چین", "بلاکچین", "میم کوین", "دوج کوین",
            "شیبا", "پپه", "لیکویید", "نهنگ کریپتو",
            "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
            "tether", "usdt", "solana", "sol", "xrp", "ripple", "binance", "coinbase",
            "sec", "spot etf", "etf inflow", "etf outflow", "halving", "altcoin",
            "blockchain", "web3", "dogecoin", "doge", "shiba", "pepe", "memecoin",
            "liquidations", "crypto market", "defi",
        ),
    },
    "tech": {
        "label": "فناوری و هوش مصنوعی",
        "badge": "فناوری و AI",
        "emoji": "🤖",
        "weight": 1.00,
        "assets": ("NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"),
        "words": (
            "انویدیا", "اپل", "مایکروسافت", "گوگل", "آلفابت", "آمازون", "متا",
            "تسلا", "هوش مصنوعی", "هوش‌مصنوعی", "اوپن ای آی", "اوپن‌ای‌آی", "چت جی پی تی", "چت جی‌پی‌تی",
            "دیپ‌سیک", "دیپ سیک", "جمینای", "جمینی", "کلود", "آنتروپیک", "آنتورپیک",
            "مدل زبانی", "یادگیری ماشین", "تراشه", "تراشه‌ها", "نیمه‌هادی", "نیمه‌رسانا",
            "دیتاسنتر", "مراکز داده", "سوپرکامپیوتر", "رایانش ابری", "پردازش ابری", "رباتیک",
            "سهام فناوری", "غول‌های فناوری", "نزدک", "ان‌ویدیا", "اینتل", "ای‌ام‌دی", "کوآلکام", "اوراکل",
            "nvidia", "nvda", "apple", "aapl", "microsoft", "msft", "google", "alphabet",
            "googl", "amazon", "amzn", "meta", "tesla", "tsla", "ai", "artificial intelligence",
            "openai", "chatgpt", "deepseek", "anthropic", "claude", "gemini", "semiconductor",
            "semiconductors", "chips", "tsmc", "intel", "amd", "qualcomm", "broadcom", "asml",
            "oracle", "datacenter", "data center", "cloud computing", "robotics", "supercomputer",
            "blackwell", "h100", "b200", "agi", "llm", "large language model", "genai", "generative ai",
            "machine learning", "tech stocks", "big tech", "nasdaq", "ndx",
        ),
    },
    "coin": {
        "label": "مسکوکات و شمش",
        "badge": "فلزات",
        "emoji": "🪙",
        "weight": 0.80,
        "words": (
            "شمش طلا", "سکه طلا جهانی", "مسکوکات", "ضرابخانه",
            "gold bar", "gold coin", "silver coin", "bullion coin", "mint", "us mint",
        ),
    },
}

# Stories that never belong on the tgju.org/news foreign news desk.
# Hard exclusions:
# 1. Domestic Iranian market news (handled separately by domestic editorial desk).
# 2. Phishing scams and fraud.
# 3. Off-topic celebrity gossip.
OFF_PROFILE: Dict[str, Dict[str, Any]] = {
    "domestic": {
        "label": "اخبار داخلی و بازار ایران",
        "words": (
            "تومان", "ریال", "کارت ملی", "سکه بهار آزادی", "سکه امامی", "نیم سکه", "ربع سکه",
            "طلای ۱۸", "طلای ۲۴", "طلای آب", "آب شده", "آبشده", "مثقال", "بازار تهران", "سبزه میدان",
            "بورس تهران", "فرابورس", "سامانه نیما", "ارز نیمایی", "سامانه سنا", "ارز توافقی",
            "یارانه", "خودرو داخلی", "ایران خودرو", "سایپا", "وزارت صمت", "بانک مرکزی ایران",
            "شاخص کل بورس", "بازار آزاد تهران", "صرافی ملی", "صندوق بازنشستگی", "مجلس شورای اسلامی",
            "toman", "iranian rial", "tehran market", "tsetmc", "cbi.ir",
        ),
    },
    "scam": {
        "label": "اسپم و کلاهبرداری",
        "words": (
            "airdrop claim", "free giveaway", "seed phrase", "wallet drainer", "phishing scam",
            "کلاهبرداری ایردراپ", "سرقت کلمات بازیابی", "فیشینگ",
        ),
    },
    "gossip": {
        "label": "سلبریتی و زرد غیرمالی",
        "words": (
            "hollywood", "kardashian", "taylor swift", "سلبریتی زرد", "اینفلوئنسر زرد", "بازیگر هالیوود",
        ),
    },
}

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")

# Persian normalisation: Arabic ي/ك, Arabic-Indic digits, ZWNJ, tatweel.
_PERSIAN_MAP = {
    "ي": "ی",
    "ك": "ک",
    "ۀ": "ه",
    "‌": " ",
    "‏": " ",
    "‎": " ",
    "ـ": "",
    "ً": "", "ٌ": "", "ٍ": "", "َ": "",
    "ُ": "", "ِ": "", "ّ": "", "ْ": "",
}
_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})

_ZWNJ_RE = re.compile("[ً-ٰٟۖ-ۭـ]")
_SPACE_RE = re.compile(r"\s+")


def normalize(text: Any) -> str:
    """Fold headline/summary text into normalized representation for matching."""
    s = str(text or "")
    s = s.translate(_DIGIT_MAP)
    s = _ZWNJ_RE.sub(" ", s)
    for a, b in _PERSIAN_MAP.items():
        s = s.replace(a, b)
    from fa_format import fa_fold
    return _SPACE_RE.sub(" ", fa_fold(s)).strip().lower()


def article_text(article: Any) -> str:
    """The whole searchable surface of one article, normalised once."""
    if not isinstance(article, dict):
        return ""
    return normalize(" ".join(str(article.get(k) or "") for k in (
        "title_fa", "title", "summary_fa", "summary",
    )))


_FA_SUFFIXES = ("ها", "های", "هایی", "تر", "ترین", "ام", "ات", "اش", "ای", "ین")
_LATIN_RE = re.compile(r"[a-z0-9 &'.-]+")
_LETTER = r"[a-z0-9\u0600-\u06FF]"


def _hit(text: str, word: str) -> bool:
    """Word-boundary match that survives Persian agglutination and English boundaries."""
    w = normalize(word)
    if not w:
        return False
    if _LATIN_RE.fullmatch(w):
        return re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", text) is not None
    m = re.search(r"(?<!" + _LETTER + r")" + re.escape(w), text)
    if not m:
        return False
    rest = text[m.end():]
    if not rest or not re.match(_LETTER, rest):
        return True
    return any(rest.startswith(s) for s in _FA_SUFFIXES)


def detect_buckets(article: Dict[str, Any]) -> Dict[str, List[str]]:
    """Which TGJU editorial desks this article speaks to, and on what evidence."""
    text = article_text(article)
    assets = [str(a).upper() for a in (article.get("assets") or []) if isinstance(a, str)]
    strong: Dict[str, List[str]] = {}
    ambiguous: Dict[str, List[str]] = {}

    for key, spec in BUCKETS.items():
        # Check tagged asset symbols
        spec_assets = spec.get("assets") or ()
        for a in assets:
            if a in spec_assets:
                strong.setdefault(key, []).append(a)

        amb = set(spec.get("ambiguous") or ())
        for w in spec["words"]:
            if not _hit(text, w):
                continue
            is_amb = normalize(w) in {normalize(x) for x in amb}
            target_map = ambiguous if is_amb else strong
            target_map.setdefault(key, [])
            if w not in target_map[key]:
                target_map[key].append(w)

    found: Dict[str, List[str]] = {k: v[:6] for k, v in strong.items() if v}
    for key, hits in ambiguous.items():
        if key not in found and not found:
            found[key] = hits[:6]

    # Vendored Persian crypto lexicon
    extra = persian_words.crypto_evidence(text)
    if extra:
        cur = found.setdefault("crypto", [])
        for w in extra:
            if w not in cur:
                cur.append(w)
        found["crypto"] = cur[:8]

    return found


def detect_off_profile(article: Dict[str, Any]) -> Dict[str, List[str]]:
    """Which off-profile categories this article falls into (empty = publishable)."""
    text = article_text(article)
    found: Dict[str, List[str]] = {}

    # Hard guard: Iranian domestic sources, domains (.ir) or names
    src_key = str(article.get("source_key") or "").lower()
    link = str(article.get("link") or "").lower()
    src_name = str(article.get("source_name") or "")
    if (src_key in ("tejaratnews", "donya-eqtesad", "eghtesadonline", "isna", "mehrnews", "arzdigital")
            or ".ir/" in link or ".ir" in link.split("/")[2:3]
            or "tejaratnews" in link or "donya-e-eqtesad" in link or "arzdigital" in link
            or any(w in src_name for w in ("تجارت نیوز", "دنیای اقتصاد", "ایسنا", "مهر", "اقتصاد آنلاین"))):
        found["domestic"] = ["منبع داخلی"]

    for key, spec in OFF_PROFILE.items():
        hits = [w for w in spec["words"] if _hit(text, w)]
        if hits:
            found.setdefault(key, []).extend(hits[:4])
    return found


def numbers_in(article: Dict[str, Any]) -> List[str]:
    """Every numeric claim in the Persian (else English) text, de-duplicated."""
    raw = str(article.get("title_fa") or article.get("title") or "")
    raw += " " + str(article.get("summary_fa") or article.get("summary") or "")
    out: List[str] = []
    for m in NUMBER_RE.finditer(raw.translate(_DIGIT_MAP)):
        n = m.group(0)
        if n not in out:
            out.append(n)
    return out[:12]


_IMPACT_WORDS = (
    "fed", "fomc", "powell", "rate cut", "rate hike", "interest rate", "cpi", "pce", "inflation",
    "gdp", "recession", "opec", "crude", "etf", "sec", "earnings", "revenue", "guidance",
    "target", "all-time high", "breakout", "plunge", "rally", "liquidation", "yield",
    "treasury", "central bank", "tariffs", "sanctions", "ai", "breakthrough", "record",
    "فدرال رزرو", "نرخ بهره", "تورم", "کاهش نرخ", "افزایش نرخ", "رکود", "صندوق etf",
    "سقف تاریخی", "شکست مقاومت", "ریزش", "رالی", "اوراق قرضه", "بانک مرکزی", "تعرفه",
    "سود سهام", "درآمد سهام", "گزارش مالی", "رکورد", "جهش", "سقوط", "اوپک", "پاول",
)


def _market_impact(text: str, nums: List[str]) -> float:
    """0–1: Editorial news value and market-moving substance for tgju.org/news."""
    score = 0.35
    if nums:
        score += 0.25
    hits = sum(1 for w in _IMPACT_WORDS if _hit(text, w))
    if hits >= 1:
        score += 0.25
    if hits >= 3:
        score += 0.15
    return min(1.0, score)


def _freshness(age_hours: float, half_life_hours: float = 12.0) -> float:
    """Editorial freshness for website desk."""
    if age_hours <= 0:
        return 1.0
    return max(0.05, min(1.0, 2 ** (-age_hours / max(1.0, half_life_hours))))


def _age_hours(article: Dict[str, Any], now: float) -> float:
    ts = float(article.get("published_ts") or 0)
    if ts > 1e11:
        ts /= 1000.0
    if ts <= 0:
        return 12.0
    return max(0.0, (now - ts) / 3600.0)


def score_article(article: Dict[str, Any], now: Optional[float] = None,
                  min_credibility: float = 0.55) -> Dict[str, Any]:
    """Fit of one article for tgju.org/news, 0–100, explainable factors kept."""
    now = now or time.time()
    if not isinstance(article, dict):
        return {"fit": 0.0, "publishable": False,
                "reason": "رکورد خبر نامعتبر", "buckets": {}, "off_profile": {},
                "age_hours": 0.0, "factors": {}}

    text = article_text(article)
    buckets = detect_buckets(article)
    off = detect_off_profile(article)
    nums = numbers_in(article)

    _cred_raw = article.get("credibility")
    credibility = 0.7 if _cred_raw is None else float(_cred_raw)
    age = _age_hours(article, now)

    if credibility < min_credibility:
        return {
            "fit": 0.0, "publishable": False,
            "reason": f"رد شده — اعتبار منبع {credibility*100:.0f}٪ زیر آستانه {min_credibility*100:.0f}٪",
            "buckets": buckets, "off_profile": off, "age_hours": age,
            "factors": {},
        }
    if off:
        lane = OFF_PROFILE[next(iter(off))]["label"]
        return {
            "fit": 0.0, "publishable": False,
            "reason": f"خارج از موضوع — {lane}",
            "buckets": buckets, "off_profile": off, "age_hours": age,
            "factors": {},
        }
    if not buckets:
        return {
            "fit": 0.0, "publishable": False,
            "reason": "موضوع خبر در حوزه‌های هدف tgju.org/news نبود",
            "buckets": buckets, "off_profile": off, "age_hours": age,
            "factors": {},
        }

    weights = [BUCKETS[b]["weight"] for b in buckets]
    topic = min(1.0, sum(sorted(weights, reverse=True)[:2]) / 1.7)
    impact = _market_impact(text, nums)
    fresh = _freshness(age, half_life_hours=12.0)

    penalty = 0.0
    if article.get("source_kind") == "social":
        penalty += 0.08

    fit = (0.35 * topic + 0.30 * impact + 0.20 * fresh + 0.15 * credibility)
    fit *= (1.0 - penalty)
    fit = max(0.0, min(1.0, fit)) * 100.0

    # Select primary desk bucket
    if "tech" in buckets and any(_hit(text, w) for w in (
        "nvidia", "ai", "apple", "microsoft", "openai", "semiconductor", "هوش مصنوعی", "تراشه", "انویدیا",
    )):
        primary = "tech"
    elif "crypto" in buckets:
        primary = "crypto"
    else:
        primary = max(buckets, key=lambda b: (BUCKETS[b]["weight"], len(buckets[b])))

    spec = BUCKETS[primary]
    why: List[str] = [f"بخش «{spec['label']}»", f"{len(nums)} عدد/داده کلیدی" if nums else "بدون عدد"]
    if impact >= 0.7:
        why.append("اثرگذاری بالا بر بازار")
    if article.get("source_kind") == "social":
        why.append("منبع شبکه اجتماعی")

    return {
        "fit": round(fit, 1),
        "publishable": True,
        "reason": " · ".join(why),
        "primary_bucket": primary,
        "badge": spec["badge"],
        "bucket_label": spec["label"],
        "emoji": spec["emoji"],
        "buckets": buckets,
        "off_profile": off,
        "numbers": nums,
        "age_hours": round(age, 2),
        "factors": {
            "topic": round(topic, 2),
            "market_impact": round(impact, 2),
            "freshness": round(fresh, 2),
            "credibility": round(credibility, 2),
            "penalty": round(penalty, 2),
        },
    }


# ──────────────────────────────────────────────────────────────────────────
# Virality Engine — Viral Trends & Social Momentum
# ──────────────────────────────────────────────────────────────────────────
_VIRAL_WORDS = (
    "رکورد", "بی‌سابقه", "برای اولین بار", "اولین بار",
    "تاریخی", "جهش", "سقوط", "سقف تاریخی", "کف تاریخی", "انفجار", "هشدار",
    "شوک", "بحران", "ناگهان", "ناگهانی", "پرش", "ریزش", "به بالاترین",
    "به پایین‌ترین", "شکست سقف", "شکست حمایت", "رکورد تاریخی", "وحشت",
    "پامپ", "طوفان", "میلیارد دلاری", "تریلیون دلاری", "انفجار قیمت",
    "record", "surge", "plunge", "historic", "unprecedented", "crash", "warn", "warning",
    "all-time high", "ath", "breakout", "crisis", "shock", "explosion", "skyrocket",
    "massive", "bull run", "bear market", "liquidation", "frenzy", "trillion", "billion",
)
_ROUND_RE = re.compile(r"(?:^|[\s،.:؛])([1-9]\d*)\s*(هزار|میلیون|میلیارد)(?:[\s،.:؛]|$)")


def _sat(x: float) -> float:
    if x <= 0:
        return 0.0
    return 1.0 - pow(2.718281828, -x)


def viral_score(article: Dict[str, Any], market: Optional[Dict[str, Any]] = None,
                now: Optional[float] = None) -> Dict[str, Any]:
    """Virality and social momentum score of one story, 0–100."""
    now = now or time.time()
    text = article_text(article)
    reasons: List[str] = []

    # 1. Market Shock & Asset Moves
    shock, shock_src = 0.35, "نوسان عادی بازار"
    assets = [a for a in (article.get("assets") or []) if isinstance(a, str)]
    mkt = market or {}
    best = None
    for sym in assets:
        row = mkt.get(sym)
        if not row:
            continue
        chg = row.get("change_24h")
        spark = [float(x) for x in (row.get("closes") or row.get("spark") or [])
                 if isinstance(x, (int, float))]
        price = row.get("price")
        z = 0.0
        if chg is not None and len(spark) >= 6:
            rets = [abs((spark[i] - spark[i - 1]) / spark[i - 1]) * 100.0
                    for i in range(1, len(spark)) if spark[i - 1]]
            base = max(0.35, sum(rets) / len(rets) if rets else 1.0)
            z = abs(float(chg)) / base
            at_extreme = price is not None and spark and price >= max(spark) * 0.999
            if at_extreme and float(chg) > 0:
                z += 0.8
            elif at_extreme and float(chg) < 0:
                z += 0.5
        elif chg is not None:
            z = abs(float(chg)) / 3.0
        if best is None or z > best[0]:
            best = (z, sym)
    if best:
        shock = min(1.0, _sat(best[0] / 1.8))
        shock_src = f"حرکت ۲۴ ساعته نماد {best[1]}"
    reasons.append(shock_src)

    # 2. Drama, Records & Novelty
    drama = [w for w in _VIRAL_WORDS if _hit(text, w)]
    rounds = list(_ROUND_RE.finditer(text))
    novelty = min(1.0, _sat(len(drama) / 2.0 + len(rounds) / 3.0))
    if drama:
        reasons.append("زاویه وایرال: " + "، ".join(drama[:3]))

    # 3. Viral Buzz Topics (Gold records, Bitcoin ATH, AI rally, Memecoins)
    buzz_words = ("gold", "bitcoin", "nvidia", "ai", "rate cut", "oil", "doge", "pepe", "طلا", "بیت کوین", "هوش مصنوعی", "انویدیا", "نفت")
    buzz = min(1.0, _sat(sum(1 for w in buzz_words if _hit(text, w)) / 1.5))
    if buzz > 0.5:
        reasons.append("موضوع پرطرفدار و ترند")

    # 4. Social Demand (Reddit score / Social signals)
    rs = article.get("reddit_score")
    try:
        rs = float(rs) if rs is not None else None
    except (TypeError, ValueError):
        rs = None
    demand = min(1.0, _sat(rs / 1500.0)) if rs else 0.20
    if rs:
        reasons.append(f"تقاضای اجتماعی: {int(rs)} امتیاز ردیت")

    # 5. Freshness
    fresh = _freshness(_age_hours(article, now), half_life_hours=8.0)

    viral = (0.30 * shock + 0.30 * novelty + 0.20 * buzz + 0.10 * demand + 0.10 * fresh) * 100.0
    return {
        "viral": round(viral, 1),
        "viral_factors": {
            "shock": round(shock, 2),
            "novelty": round(novelty, 2),
            "buzz": round(buzz, 2),
            "demand": round(demand, 2),
            "freshness": round(fresh, 2),
        },
        "viral_why": reasons[:4],
    }


def _tidy_fa(text: str, limit: int = 120) -> str:
    s = _SPACE_RE.sub(" ", str(text or "").replace("‌", " ").strip())
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0]
    return cut + "…"


def build_caption(item: Dict[str, Any]) -> Dict[str, Any]:
    """Editorial brief for tgju.org/news desk."""
    art = item.get("article") or {}
    title = _tidy_fa(art.get("title_fa") or art.get("title") or "", 100)
    summary = _tidy_fa(art.get("summary_fa") or art.get("summary") or "", 200)
    emoji = item.get("emoji") or "📰"
    badge = item.get("badge") or "خبر بین‌الملل"
    nums = item.get("numbers") or []

    body = summary or "جزئیات خبر و داده‌های تکمیلی در گزارش کامل منبع."
    lines = [f"{emoji} {title}", "", body, "", f"🏷️ {badge} · TGJU News"]
    if nums:
        lines.append(f"🔢 داده‌های کلیدی: {'، '.join(nums[:5])}")

    return {
        "text": "\n".join(lines),
        "headline": f"{emoji} {title}",
        "body": body,
        "badge": badge,
        "numbers": nums,
        "hashtags": ["#TGJU", "#اخبار_بازار", "#اقتصاد_جهان", f"#{badge.replace(' ', '_')}"],
    }


def _dedupe_key(article: Dict[str, Any]) -> str:
    """Same six key words = duplicate story."""
    toks = normalize(article.get("title_fa") or article.get("title") or "").split()
    kept = [t for t in toks if t not in ("و", "در", "به", "از", "با", "که", "the", "a", "an", "in", "to", "for")]
    return " ".join(kept[:6])


def rank_for_channel(articles: Iterable[Dict[str, Any]], now: Optional[float] = None,
                     limit: Optional[int] = None, min_fit: float = 12.0,
                     min_credibility: float = 0.55,
                     market: Optional[Dict[str, Any]] = None,
                     ai_only: bool = False) -> Dict[str, Any]:
    """Rank foreign news for tgju.org/news editorial desk.

    Composite ranking balances viral trend interest (55%) with editorial fit (45%).
    When ai_only is True, strictly restricts content ideas to Artificial Intelligence & Tech.
    If limit is specified (e.g. 150), caps results to the top ranked stories.
    """
    now = now or time.time()
    scored: List[Dict[str, Any]] = []
    seen: set = set()
    rejected = {"off_profile": 0, "no_bucket": 0, "low_credibility": 0, "duplicate": 0}

    for art in articles or []:
        res = score_article(art, now=now, min_credibility=min_credibility)
        if not res["publishable"]:
            if res["off_profile"]:
                rejected["off_profile"] += 1
            elif "اعتبار منبع" in res["reason"]:
                rejected["low_credibility"] += 1
            else:
                rejected["no_bucket"] += 1
            continue

        if ai_only and res.get("primary_bucket") != "tech":
            rejected["no_bucket"] += 1
            continue

        key = _dedupe_key(art)
        if key and key in seen:
            rejected["duplicate"] += 1
            continue
        seen.add(key)

        vir = viral_score(art, market=market, now=now)
        item = {
            "id": art.get("id", ""),
            "title": art.get("title", ""),
            "title_fa": art.get("title_fa", ""),
            "summary_fa": art.get("summary_fa") or art.get("summary") or "",
            "source": art.get("source_name") or art.get("source_key") or "",
            "source_kind": art.get("source_kind", ""),
            "link": art.get("link", ""),
            "image": art.get("image") or "",
            "credibility": round(float(art.get("credibility") or 0.7), 2),
            "published_ts": art.get("published_ts"),
            "fit": res["fit"],
            "viral": vir["viral"],
            "viral_factors": vir["viral_factors"],
            "viral_why": vir["viral_why"],
            "rank": round(0.55 * vir["viral"] + 0.45 * res["fit"], 1),
            "why": res["reason"],
            "primary_bucket": res["primary_bucket"],
            "badge": res["badge"],
            "bucket_label": res["bucket_label"],
            "emoji": res["emoji"],
            "buckets": res["buckets"],
            "off_profile": res["off_profile"],
            "numbers": res["numbers"],
            "age_hours": res["age_hours"],
            "factors": res["factors"],
            "article": art,
        }
        item["caption"] = build_caption(item)
        scored.append(item)

    scored.sort(key=lambda x: (-x["rank"], x["age_hours"]))
    qualified = [i for i in scored if i["fit"] >= min_fit]
    if limit is not None and int(limit) > 0:
        items = qualified[:int(limit)]
    else:
        items = qualified

    lanes: Dict[str, int] = {}
    for i in items:
        lanes[i["badge"]] = lanes.get(i["badge"], 0) + 1

    return {
        "items": items,
        "scanned": len(scored),
        "lanes": lanes,
        "rejected": rejected,
        "generated_ts": now,
        "profile": {
            "handle": "https://www.tgju.org/news",
            "name": "شبکه اطلاع‌رسانی طلا و ارز — تحریریه اخبار",
            "buckets": {k: {"label": v["label"], "badge": v["badge"], "emoji": v["emoji"]}
                        for k, v in BUCKETS.items()},
        },
    }


def slice_board(board: Dict[str, Any], limit: Optional[int] = None) -> Dict[str, Any]:
    """A narrower view of a ranked board, without re-ranking it."""
    if not limit or int(limit) <= 0:
        return board
    n = int(limit)
    items = list((board or {}).get("items") or [])
    if len(items) <= n:
        return board
    out = dict(board)
    out["items"] = items[:n]
    lanes: Dict[str, int] = {}
    for i in out["items"]:
        badge = i.get("badge") or ""
        lanes[badge] = lanes.get(badge, 0) + 1
    out["lanes"] = lanes
    return out
