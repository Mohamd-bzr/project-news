"""channel_profile.py — "which of today's stories belong on the gold/coin page?"

One page was studied (@tgjusocialmedia, «شبکه اطلاع رسانی طلا، سکه و ارز»,
212K followers, 15 following). Its grid is not analysis: it is **price cards and
one-line news cards**. Almost every tile is a dark-navy graphic with one asset
price and one sentence — «طلا در ۲۴ میلیون», «افت ۵۰,۰۰۰ دلاری با کارت ملی»,
«سقف تاریخی جدید». The badge on the tile says which lane it belongs to:
`نوسان قیمت` · `اخبار طلا` · `اخبار داخلی` · `نوسان بازار` · `بازارهای جهانی` ·
`امروز در بازار`.

So the question this module answers is not "is this important?" — the feed and
the reports already answer that. It is **"does this look like something that
page would publish?"** That is a different, narrower question, and it is
answered here with the same discipline the rest of the project uses:

* **Explainable.** Every item keeps its own factors, and the badge it would wear
  on the grid is returned next to the score. Nothing is a black box.
* **Local, deterministic, free.** Persian and English lexicons, no model, no API.
* **A gate, not a weight.** Off-profile stories (protocol hacks, meme coins,
  NFT drops, celebrity gossip) are excluded outright rather than ranked low;
  a page's identity is defined by what it refuses as much as by what it runs.

The module is pure: `rank_for_channel(articles, now)` is the only entry point
the server needs, and every helper is independently testable.
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import persian_words

# ──────────────────────────────────────────────────────────────────────────
# The page profile, as observed on the grid
# ──────────────────────────────────────────────────────────────────────────
# bucket -> (label, badge, emoji, weight, keywords)
# `badge` is the tag the page prints on the tile itself; `weight` is how central
# the lane is to the page (its price cards are the whole reason people follow).
BUCKETS: Dict[str, Dict[str, Any]] = {
    "gold": {
        "label": "طلا و اونس",
        "badge": "نوسان قیمت",
        "emoji": "🟡",
        "weight": 1.00,
        "words": (
            "طلا", "طلای", "اونس", "اونس طلا", "زر", "گلد", "زرین", "طلای آب",
            "آب شده", "مثقال", "طلای ۱۸", "طلای ۲۴", "طلای ۱۴", "عیار",
            "gold", "xau", "bullion", "ounce", "gold price",
        ),
    },
    "coin": {
        "label": "سکه",
        "badge": "اخبار طلا",
        "emoji": "🪙",
        "weight": 1.00,
        "words": (
            "سکه", "سکه امامی", "بهار آزادی", "سکه طرح جدید", "نیم سکه", "نیم‌سکه",
            "ربع سکه", "ربع‌سکه", "سکه فولادی", "تمام سکه", "سکه فروشی",
            "باند سکه", "صکه", "coin", "mashhad coin",
        ),
    },
    "currency": {
        "label": "ارز و دلار",
        "badge": "نوسان بازار",
        "emoji": "💵",
        "weight": 0.95,
        # «دلار» is this page's core subject *and* a word every crypto story
        # uses when it quotes a loss or a fee. Those are different articles, so
        # the bare word is marked ambiguous: it only opens this lane when
        # nothing else in the article did (see ``detect_buckets``).
        "ambiguous": ("دلار", "dollar"),
        "words": (
            "دلار آزاد", "نرخ دلار", "قیمت دلار", "تومان", "ریال", "پوند", "یورو",
            "لیر", "درهم", "ارز", "نرخ ارز", "بازار سیاه", "حواله", "صرافی",
            "کارت ملی", "کارت بانکی", "ارزش ارز", "euro", "pound",
            "exchange rate", "forex", "rial", "toman",
        ),
    },
    "global": {
        "label": "بازارهای جهانی",
        "badge": "بازارهای جهانی",
        "emoji": "🌍",
        "weight": 0.65,
        "words": (
            "فدرال رزرو", "بانک مرکزی آمریکا", "نرخ بهره", "بهره آمریکا",
            "وال استریت", "شاخص دلار", "داده‌های آمریکا", "نفت", "برنت", "اوپک",
            "طلای جهانی", "بازار جهانی", "چین", "ژاپن", "اروپا",
            "federal reserve", "fed", "fomc", "wall street", "opec", "crude",
            "brent", "gold price", "dxy", "treasury yield", "recession",
        ),
    },
    "crypto": {
        "label": "ارز دیجیتال",
        "badge": "بازارهای جهانی",
        "emoji": "₿",
        "weight": 0.35,
        "words": (
            "بیت کوین", "بیت‌کوین", "بیتکوین", "تتر", "اتریوم", "کریپتو",
            "رمزارز", "ارز دیجیتال", "استیبل کوین", "سولانا",
            "bitcoin", "btc", "ethereum", "crypto", "tether", "usdt",
        ),
    },
}

# Lanes the page never runs. These are hard excludes, not low scores: a card
# about a bridge exploit or an NFT drop on a gold-price page is off-brand even
# if it is well sourced and viral. Detection is deliberately narrow so ordinary
# market coverage ("ETF ورود پول به بیت‌کوین") is not swept up by it.
OFF_PROFILE: Dict[str, Dict[str, Any]] = {
    "security": {
        "label": "امنیت و هک",
        "words": (
            "هک", "هک شد", "نفوذ", "سرقت", "دوربین", "حمله سایبری", "آسیب‌پذیری",
            "پولشویی", "کلاهبرداری", "سرقتگاه",
            "hack", "hacked", "exploit", "breach", "stolen", "scam", "phishing",
            "ransomware", "vulnerability", "laundering",
        ),
    },
    "defi": {
        "label": "دی‌فای و توکن",
        "words": (
            "دی فای", "دی‌فای", "استیکینگ", "استخر نقدینگی", "ییلد فارم",
            "هاک", "پامپ و دامپ", "نیتوکن", "ایردراپ", "پیش فروش توکن",
            "defi", "staking", "liquidity pool", "yield farm", "airdrop",
            "rug pull", "presale", "token launch",
        ),
    },
    "meme": {
        "label": "میم و توکن طنز",
        "words": (
            "میم کوین", "میم‌کوین", "شیبا", "دوج کوین", "دوج", "پپه", "bonk",
            "meme coin", "shiba", "dogecoin", "doge", "pepe coin", "pump up",
        ),
    },
    "celebrity": {
        "label": "سلبریتی و رسانه",
        "words": (
            "سلبریتی", "اینفلوئنسر", "تایمز", "بیلی ایلیش", "سلیوم",
            "elon musk", "taylor swift", "celebrity",
            "influencer", "instagram model",
        ),
    },
}

# Signal words that mark a story as a *price card* rather than a story: the
# page's single most common tile is "one asset, one number, one sentence".
PRICE_UNITS = (
    "تومان", "ریال", "دلار", "درصد", "٪", "تومانی", "میلیون", "میلیارد",
    "usd", "toman", "rial", "%",
)

NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")

# Persian normalisation: Arabic ي/ك, Arabic-Indic digits, ZWNJ, tatweel.
_PERSIAN_MAP = {
    "ي": "ی",   # ARABIC YEH  -> FARSI YEH
    "ك": "ک",   # ARABIC KAF  -> KEHEH
    "ۀ": "ه",         # HEH WITH YEH ABOVE -> HEH
    "‌": " ",        # ZWNJ -> space
    "‏": " ",        # RLM
    "‎": " ",        # LRM
    "ـ": "",              # TATWEEL
    "ً": "", "ٌ": "", "ٍ": "", "َ": "",
    "ُ": "", "ِ": "", "ّ": "", "ْ": "",
}
_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}       # ٠..٩
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})  # ۰..۹

_ZWNJ_RE = re.compile("[ً-ٰٟۖ-ۭـ]")
# The Arabic-Indic digits live at U+0661..U+0669, **inside** the range the
# diacritic class above spans, so stripping first silently deleted any price
# written "١٢" and normalize() turned it into nothing. Folding the digits
# before the strip is what keeps them; the class itself is left narrow so it
# cannot grow back over them.
_SPACE_RE = re.compile(r"\s+")


def normalize(text: Any) -> str:
    """Fold a headline/summary into the one spelling the lexicons expect."""
    s = str(text or "")
    s = s.translate(_DIGIT_MAP)     # digits first: they must survive stripping
    s = _ZWNJ_RE.sub(" ", s)
    for a, b in _PERSIAN_MAP.items():
        s = s.replace(a, b)
    # fold what the maps above don't cover: diacritics, tatweel, ZWNJ —
    # «نیم‌سکه» and «نیم سکه» must land on the same matching text
    from fa_format import fa_fold
    return _SPACE_RE.sub(" ", fa_fold(s)).strip().lower()


def article_text(article: Any) -> str:
    """The whole searchable surface of one article, normalised once.

    Every field is read with ``.get``/``or`` on purpose: this runs over the
    live corpus, which is whatever the 100+ scrapers handed over, and one
    record with a null title must not take the whole board down.
    """
    if not isinstance(article, dict):
        return ""
    return normalize(" ".join(str(article.get(k) or "") for k in (
        "title_fa", "title", "summary_fa", "summary",
    )))


# Persian has no spaces between a noun and its plural/possessive suffix, so a
# plain `in` test is wrong in both directions: «زر» fires inside «بزرگ» and
# «وام» inside «دوام». These are the only continuations a bare stem is allowed
# to have. «ین» is included because «زرین» really is the gold lane, while a
# bare «ی» is not: it is what makes «زرین» a hit rather than a near-miss.
_FA_SUFFIXES = ("ها", "های", "هایی", "تر", "ترین", "ام", "ات", "اش", "ای", "ین")

_LATIN_RE = re.compile(r"[a-z0-9 &'.-]+")
_LETTER = r"[a-z0-9\u0600-\u06FF]"


def _hit(text: str, word: str) -> bool:
    """Word-boundary match that survives Persian agglutination.

    A latin ``coin`` must not fire inside ``bitcoin``, and ``oil`` must not fire
    inside ``boil``. On the Persian side the naive substring test is just as
    wrong — «زر» inside «بزرگ», «وام» inside «دوام» — so the stem must not be
    flanked by another letter, *except* for the inflectional suffixes listed in
    ``_FA_SUFFIXES`` which keep a stem a legitimate hit («سکه» in «سکه‌ها»).
    """
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
    """Which page lanes this article speaks to, and on what evidence.

    Returns ``{bucket: [matched keywords]}`` — the words themselves come back
    so the UI can show *why* a card was proposed, not just a score.

    Ambiguous words («دلار») open their lane only when nothing else already
    did, which is what keeps «تیم کریپتو روزانه ۵۰ هزار دلار درآمد دارد» in the
    crypto lane instead of the FX lane the page owns.
    """
    text = article_text(article)
    strong: Dict[str, List[str]] = {}
    ambiguous: Dict[str, List[str]] = {}
    for key, spec in BUCKETS.items():
        amb = set(spec.get("ambiguous") or ())
        for w in spec["words"]:
            if not _hit(text, w):
                continue
            (ambiguous if normalize(w) in {normalize(a) for a in amb} else strong).setdefault(key, [])
            bucket_list = strong if normalize(w) not in {normalize(a) for a in amb} else ambiguous
            if w not in bucket_list[key]:
                bucket_list[key].append(w)

    found: Dict[str, List[str]] = {k: v[:6] for k, v in strong.items() if v}
    for key, hits in ambiguous.items():
        if key not in found and not found:
            found[key] = hits[:6]

    # Vendored Persian coin vocabulary (mohamadkhalaj/persian-crypto-words,
    # MIT — see persian_words): the static bucket words above know «بیت کوین»
    # but not «ریپل» or «پولکادات». Lexicon hits join the crypto lane as
    # *evidence*, keeping the board's why-explainable. A «دلار»-only story
    # stays FX — the lexicon only ever opens the crypto lane itself.
    extra = persian_words.crypto_evidence(text)
    if extra:
        cur = found.setdefault("crypto", [])
        for w in extra:
            if w not in cur:
                cur.append(w)
        found["crypto"] = cur[:8]
    return found


def detect_off_profile(article: Dict[str, Any]) -> Dict[str, List[str]]:
    """Which off-profile lanes this article falls into (empty = publishable)."""
    text = article_text(article)
    found: Dict[str, List[str]] = {}
    for key, spec in OFF_PROFILE.items():
        hits = [w for w in spec["words"] if _hit(text, w)]
        if hits:
            found[key] = hits[:4]
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


def _price_readiness(text: str, nums: List[str]) -> float:
    """0–1: how close this story is to the page's signature "price card" tile.

    A card carries a number, a unit and an asset. Missing any one of the three
    means it is a story that *mentions* a price, not a price card.
    """
    if not nums:
        return 0.0
    score = 0.34                                        # it has a number
    if any(_hit(text, u) for u in PRICE_UNITS):
        score += 0.33                                   # ...with a unit
    has_asset = any(_hit(text, w) for key in ("gold", "coin", "currency")
                    for w in BUCKETS[key]["words"][:6])
    if has_asset:
        score += 0.33                                   # ...about a tracked asset
    return min(1.0, score)


def _freshness(age_hours: float, half_life_hours: float = 8.0) -> float:
    """The page posts 3–5 tiles a day; a 40-hour-old price is not a price."""
    if age_hours <= 0:
        return 1.0
    return max(0.05, min(1.0, 2 ** (-age_hours / max(1.0, half_life_hours))))


def _age_hours(article: Dict[str, Any], now: float) -> float:
    ts = float(article.get("published_ts") or 0)
    if ts > 1e11:                       # milliseconds, some feeds hand them over
        ts /= 1000.0
    if ts <= 0:
        return 12.0                     # undated: neither rewarded nor buried
    return max(0.0, (now - ts) / 3600.0)


def score_article(article: Dict[str, Any], now: Optional[float] = None,
                  min_credibility: float = 0.55) -> Dict[str, Any]:
    """Fit of one article to the page, 0–100, with every factor kept.

    The credibility floor is a gate: a well-shaped story from a source the
    project already distrusts does not get a pretty score, it gets nothing.
    """
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
    # `or 0.7` treated an explicit 0.0 (zero-trust source) as "missing" and
    # let it through the gate at default credibility
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
        # Off-profile is a hard exclude, as the module docstring promises. A
        # bridge-exploit story that happens to quote a dollar figure is not a
        # slow card on this page, it is a card the page never runs — the gold
        # lane it "matched" is only the word «دلار» inside a theft figure.
        lane = OFF_PROFILE[next(iter(off))]["label"]
        return {
            "fit": 0.0, "publishable": False,
            "reason": f"خارج از موضوع پیج — {lane}",
            "buckets": buckets, "off_profile": off, "age_hours": age,
            "factors": {},
        }
    if not buckets:
        return {
            "fit": 0.0, "publishable": False,
            "reason": "بخش طلا/سکه/ارز در متن خبر نبود",
            "buckets": buckets, "off_profile": off, "age_hours": age,
            "factors": {},
        }

    # ── factors, each kept on its own ────────────────────────────────────
    # topic: the lanes it hits, weighted by how central they are to the page,
    # saturating so one article does not win by name-dropping everything.
    weights = [BUCKETS[b]["weight"] for b in buckets]
    topic = min(1.0, sum(sorted(weights, reverse=True)[:2]) / 1.6)

    price = _price_readiness(text, nums)
    fresh = _freshness(age)

    # Penalties that are real editorial facts, not taste.
    penalty = 0.0
    if article.get("source_kind") == "social":
        penalty += 0.10

    fit = (0.40 * topic + 0.26 * price + 0.22 * fresh + 0.12 * credibility)
    fit *= (1.0 - penalty)
    fit = max(0.0, min(1.0, fit)) * 100.0

    if "crypto" in buckets:
        # a story that names real crypto is a crypto story: the translator
        # renders the English "coins"/"digital currency" inside crypto
        # summaries as «سکه»/«ارز», which must never out-badge the lane the
        # story actually belongs to
        primary = "crypto"
    else:
        primary = max(buckets, key=lambda b: (BUCKETS[b]["weight"], len(buckets[b])))
    spec = BUCKETS[primary]

    why: List[str] = [f"در «{spec['label']}»", f"{len(nums)} عدد قابل استناد" if nums else "بدون عدد"]
    if price >= 0.6:
        why.append("قالب کارت قیمت")
    if article.get("source_kind") == "social":
        why.append("منبع اجتماعی")

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
            "price_card": round(price, 2),
            "freshness": round(fresh, 2),
            "credibility": round(credibility, 2),
            "penalty": round(penalty, 2),
        },
    }


# ──────────────────────────────────────────────────────────────────────────
# Virality engine — "why would this travel?"
# ──────────────────────────────────────────────────────────────────────────
# The page-fit score above answers "does this belong on the page?". This half
# answers the question the operator actually asks: "of the stories that fit,
# which one would people FORWARD?" Five explainable factors, each 0..1:
#
#   shock    — the market actually moved: |24h %| against the asset's own
#              recent volatility (the spark series), not a fixed threshold,
#              plus a "trading at the window's extreme" bonus for records.
#   pocket   — hits the Iranian consumer's own wallet: domestic price words,
#              not global abstractions.
#   novelty  — the dramatic angle: records, firsts, round numbers, bans,
#              warnings — the words a story needs to be retold at dinner.
#   demand   — real social demand when the pipeline has it (Reddit score);
#              no signal scores low, never fabricated.
#   freshness— the usual recency half-life.
#
# Everything degrades honestly: no market row → shock is neutral-low and the
# reason says so; no Reddit score → demand stays low. Nothing is invented.

_POCKET_WORDS = (
    "دلار", "تومان", "قیمت طلا", "سکه", "بازار تهران", "بورس", "کارت ملی",
    "بنزین", "اجاره", "مسکن", "گرانی", "ارز آزاد", "بازار آزاد", "خودرو",
    "حقوق", "اجاره‌بها", "مصوبه", "یارانه", "دلار آزاد", "حواله", "گشایش",
    "صرافی", "درآمد", "خرید", "فروش", "قیمت روز",
)
_NOVELTY_WORDS = (
    "رکورد", "بی‌سابقه", "برای اولین بار", "اولین بار",
    "تاریخی", "جهش", "سقوط", "سقف تاریخی", "کف تاریخی", "انفجار", "هشدار",
    "فورس ماژور", "ممنوع", "تعلیق", "تحریم", "شوک", "بحران",
    "ناگهان", "ناگهانی", "پرش", "ریزش", "به بالاترین",
    "به پایین‌ترین", "شکست سقف", "شکست حمایت", "record", "surge", "plunge",
    "historic", "unprecedented", "crash", "warn",
)
_ROUND_RE = re.compile(r"(?:^|[\s،.:؛])([1-9]\d*)\s*(هزار|میلیون|میلیارد)(?:[\s،.:؛]|$)")


def _sat(x: float) -> float:
    """1 − e^(−x): fast rise, honest ceiling — the same saturation curve the
    studio uses for demand, so the two boards read the same language."""
    if x <= 0:
        return 0.0
    return 1.0 - pow(2.718281828, -x)


def viral_score(article: Dict[str, Any], market: Optional[Dict[str, Any]] = None,
                now: Optional[float] = None) -> Dict[str, Any]:
    """Virality potential of one story, 0–100, every factor kept.

    ``market`` is the STATE['market'] snapshot: {SYM: {price, change_24h,
    spark: [...]}}. Only the article's tagged assets are consulted.
    """
    now = now or time.time()
    text = article_text(article)
    reasons: List[str] = []

    # ── shock: the tape itself ──
    shock, shock_src = 0.30, "بدون داده بازار — نمرهٔ خنثی"
    assets = [a for a in (article.get("assets") or []) if isinstance(a, str)]
    mkt = market or {}
    best = None
    for sym in assets:
        row = mkt.get(sym)
        if not row:
            continue
        chg = row.get("change_24h")
        # STATE['market'] rows carry the raw `closes` history (the `spark`
        # name only exists in the /api/data serializer) — accept either.
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
        shock_src = "حرکت " + best[1] + " در ۲۴ ساعت"
    reasons.append(shock_src)

    # ── pocket: the reader's own wallet ──
    hits = [w for w in _POCKET_WORDS if _hit(text, w)]
    pocket = min(1.0, _sat(len(hits) / 2.5))
    if hits:
        reasons.append("ارتباط مستقیم با جیب مخاطب: " + "، ".join(hits[:3]))

    # ── novelty: the retellable angle ──
    drama = [w for w in _NOVELTY_WORDS if _hit(text, w)]
    rounds = list(_ROUND_RE.finditer(text))
    novelty = min(1.0, _sat(len(drama) / 2.0 + len(rounds) / 3.0))
    if drama:
        reasons.append("زاویهٔ خبری: " + "، ".join(drama[:3]))
    if rounds:
        reasons.append("عدد رند و به‌یادماندنی در متن")

    # ── demand: real social signal when the pipeline has one ──
    rs = article.get("reddit_score")
    try:
        rs = float(rs) if rs is not None else None
    except (TypeError, ValueError):
        rs = None
    demand = min(1.0, _sat(rs / 1500.0)) if rs else 0.15
    if rs:
        reasons.append("تقاضای اجتماعی: " + str(int(rs)) + " امتیاز ردیت")

    fresh = _freshness(_age_hours(article, now), half_life_hours=6.0)

    viral = (0.30 * shock + 0.25 * pocket + 0.20 * novelty
             + 0.15 * demand + 0.10 * fresh) * 100.0
    return {
        "viral": round(viral, 1),
        "viral_factors": {
            "shock": round(shock, 2),
            "pocket": round(pocket, 2),
            "novelty": round(novelty, 2),
            "demand": round(demand, 2),
            "freshness": round(fresh, 2),
        },
        "viral_why": reasons[:4],
    }


# ──────────────────────────────────────────────────────────────────────────
# Caption — the page's own voice, built from the article's own fields only
# ──────────────────────────────────────────────────────────────────────────
def _tidy_fa(text: str, limit: int = 110) -> str:
    s = _SPACE_RE.sub(" ", str(text or "").replace("‌", " ").strip())
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0]
    return cut + "…"


def build_caption(item: Dict[str, Any]) -> Dict[str, Any]:
    """A ready-to-post card for one item — numbers quoted, nothing invented.

    The page's tile format, reproduced:
    ``[emoji] headline`` / ``the one sentence with the numbers`` /
    ``badge · jalali-ish date stamp`` .  Every number in it came out of the
    article itself (see ``item["numbers"]``); the footer says so.
    """
    art = item.get("article") or {}
    title = _tidy_fa(art.get("title_fa") or art.get("title") or "", 95)
    summary = _tidy_fa(art.get("summary_fa") or art.get("summary") or "", 180)
    emoji = item.get("emoji") or "📊"
    badge = item.get("badge") or "نوسان قیمت"
    nums = item.get("numbers") or []

    # The one sentence that carries the price, if the summary has one.
    money_sentence = ""
    for chunk in re.split(r"(?<=[.。!؟])\s+", summary):
        if any(u in chunk for u in ("تومان", "دلار", "ریال", "درصد", "٪", "میلیون")):
            money_sentence = _tidy_fa(chunk, 160)
            break
    if not money_sentence and nums:
        money_sentence = "عدد کلیدی خبر: " + " · ".join(nums[:4])

    body = money_sentence or summary or "جزئیات خبر در لینک منبع."
    lines = [f"{emoji} {title}", "", body, "", f"🏷️ {badge}"]
    if nums:
        lines.append(f"🔢 اعداد خبر: {'، '.join(nums[:6])}")

    return {
        "text": "\n".join(lines),
        "headline": f"{emoji} {title}",
        "body": body,
        "badge": badge,
        "numbers": nums,
        "hashtags": ["#طلا", "#سکه", "#قیمت_دلار", "#بازار", "#tgju"],
    }


def _dedupe_key(article: Dict[str, Any]) -> str:
    """Same six words = the same story. A page posts one tile per story."""
    toks = normalize(article.get("title_fa") or article.get("title") or "").split()
    kept = [t for t in toks if t not in ("و", "در", "به", "از", "با", "که")]
    # first six WORDS — the old [:6] sliced the joined STRING, so any two
    # headlines sharing six characters collided as "the same story"
    return " ".join(kept[:6])


def rank_for_channel(articles: Iterable[Dict[str, Any]], now: Optional[float] = None,
                     limit: int = 40, min_fit: float = 12.0,
                     min_credibility: float = 0.55,
                     market: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """The page's board for right now: what to post, in what lane, and why.

    Stories that pass the page gates are ranked by *viral potential first*
    (0.6) with page-fit second (0.4) — the operator asked "which of these
    would travel?", not "which is most on-brand".

    Rejections are counted rather than hidden — an operator needs to see that a
    tab is empty because the corpus had nothing for this page, not because the
    filter silently swallowed everything.
    """
    now = now or time.time()
    scored: List[Dict[str, Any]] = []
    seen: set = set()
    rejected = {"off_profile": 0, "no_bucket": 0, "low_credibility": 0, "duplicate": 0}

    for art in articles or []:
        res = score_article(art, now=now, min_credibility=min_credibility)
        if not res["publishable"]:
            # Count the real reason rather than guessing it back off the prose:
            # a story that trips two gates must land in the bucket a reader
            # would put it in.
            if res["off_profile"]:
                rejected["off_profile"] += 1
            elif "اعتبار منبع" in res["reason"]:
                rejected["low_credibility"] += 1
            else:
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
            "summary_fa": (art.get("summary_fa") or art.get("summary") or "")[:200],
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
            "rank": round(0.6 * vir["viral"] + 0.4 * res["fit"], 1),
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
    items = [i for i in scored if i["fit"] >= min_fit][:max(1, limit)]

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
            "handle": "@tgjusocialmedia",
            "name": "شبکه اطلاع رسانی طلا، سکه و ارز",
            "buckets": {k: {"label": v["label"], "badge": v["badge"], "emoji": v["emoji"]}
                        for k, v in BUCKETS.items()},
        },
    }


def slice_board(board: Dict[str, Any], limit: int) -> Dict[str, Any]:
    """A narrower view of a ranked board, without re-ranking it.

    ``limit`` is a lens, not a filter: the board is ranked once at full width
    and every caller gets a prefix of the same order, so a small request — a
    health check, a second tab — can never reshape what the next reader sees.
    ``lanes`` is recomputed for the slice so the chip counts keep summing to
    ``len(items)``, which is the invariant the UI renders.
    """
    n = max(1, int(limit))
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
