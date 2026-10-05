"""content_studio.py — which story is worth making, and in what shape.

Two halves, deliberately separated:

**Ranking.** The corpus already knows what is true (``credibility``, computed upstream
from source trust, corroboration and tone). This module adds the other half of the
question — does anyone care — from ``social_signals`` (YouTube views-per-hour,
Telegram views against each channel's own median, Reddit upvotes-per-hour), plus
coverage velocity inside our own corpus, audience fit, and freshness decay.

Credibility is a **gate**, not a weight to trade away: an article under
``credibility_gate`` never enters the list, however loud the demand around it.
Above the gate, virality breaks ties. Every factor keeps its own number in the
output, so a reader can see *why* something ranked first instead of trusting a
single black-box score.

**Drafting.** One story becomes a caption, a 5–8 slide carousel, and a 30–60s
video script. When an AI key is configured the text is written by the same
grounded contract as "Ask the News" (only the supplied article, every number
quoted, no advice); without a key the module falls back to a rule-based
template built from the article's own fields. Either way nothing is invented
that the source did not say.
"""

from __future__ import annotations

import math
import re
import time

# ── factor scales: the reference values every raw signal is normalised against.
#    They are stated here rather than buried, because a score you cannot
#    reproduce by hand is a score you cannot trust.
REF_YOUTUBE_VPH = 2000.0        # views/hour that counts as "very hot" on YouTube
REF_TELEGRAM_VPH = 4000.0       # views/hour for a mid-size Persian channel
REF_REDDIT_SPH = 150.0          # upvotes/hour on a large subreddit
COVERAGE_CAP = 6                # distinct sources that make coverage "full"
TELEGRAM_REL_CAP = 3.0          # views ÷ that channel's own median

DEFAULT_WEIGHTS = {
    "credibility": 1.0,
    "coverage": 0.9,
    "audience": 1.1,
    "freshness": 1.0,
    "youtube": 0.9,
    "telegram": 1.0,
    "reddit": 0.5,
}

DEFAULT_ASSET_WEIGHTS = {
    "XAU": 1.4, "XAG": 1.1, "DXY": 1.3, "BTC": 1.25, "ETH": 1.1, "SOL": 0.9,
    "WTI": 1.2, "BRENT": 1.15, "SPX": 1.0, "NDX": 1.0, "VIX": 1.05,
}

# asset -> the words a Persian or English video/post uses for it
ASSET_WORDS = {
    "XAU": ("طلا", "گلد", "gold", "اونس"),
    "XAG": ("نقره", "silver"),
    "DXY": ("دلار", "شاخص دلار", "dollar", "dxy"),
    "BTC": ("بیت‌کوین", "بیت کوین", "بیتکوین", "bitcoin", "btc"),
    "ETH": ("اتریوم", "اتریوم", "ethereum", "eth"),
    "SOL": ("سولانا", "solana"),
    "WTI": ("نفت", "نفت خام", "oil", "crude", "wti"),
    "BRENT": ("برنت", "brent"),
    "SPX": ("اس‌اند‌پی", "بورس", "وال استریت", "s&p", "stock market", "stocks", "wall street"),
    "NDX": ("نزدک", "nasdaq"),
    "VIX": ("نوسان", "vix", "volatility"),
}

DRAMATIC = ("ریخت", "سقوط", "جهش", "رکورد", "انفجار", "هک", "توافق", "تعلیق", "تحریم",
            "بحران", "هشدار", "جنگ", "توقف", "بازگشت", "غافلگیر", "crash", "plunge",
            "surge", "record", "halt", "ban", "hack")

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has", "was", "were",
    "will", "would", "could", "after", "before", "into", "over", "than", "then", "its",
    "his", "her", "their", "are", "not", "but", "you", "your", "about", "says", "said",
    "new", "how", "why", "what", "when", "who", "امروز", "دیروز", "بازار", "قیمت",
    "خبر", "گزارش", "بررسی", "بیشتر", "کمتر", "است", "بود", "شد", "کرد", "می‌کند",
    "برای", "اما", "یا", "با", "از", "به", "در", "که", "این", "آن", "های", "ها",
}

FOOTER_FA = "این محتوا خلاصهٔ خبر است و توصیهٔ سرمایه‌گذاری نیست."
FOOTER_EN = "Summary of reported news — not investment advice."


# ───────────────────────────── text helpers ─────────────────────────────

def _text_of(article: dict) -> str:
    return " ".join(str(article.get(k) or "") for k in
                    ("title", "title_fa", "summary", "summary_fa"))


def tokens(article: dict) -> set:
    """Significant words of an article, Persian and English, plus its assets."""
    raw = _text_of(article)
    raw = re.sub(r"[^\w\u0600-\u06FF&%]+", " ", raw)
    out = set()
    for word in raw.split():
        w = word.strip().lower()
        if len(w) < 3 or w in STOPWORDS or w.isdigit():
            continue
        out.add(w)
    for sym in _assets(article):
        for alias in ASSET_WORDS.get(sym, ()):
            out.add(alias.lower())
        out.add(sym.lower())
    return out


def _assets(article: dict) -> list:
    raw = article.get("assets") or article.get("symbols") or []
    if isinstance(raw, str):
        raw = raw.split(",")
    return [str(a).strip().upper() for a in raw if str(a).strip()]


def _overlap(text_tokens: set, article_tokens: set) -> int:
    return len(text_tokens & article_tokens)


def _numbers(text: str) -> list:
    """Numeric claims in a text, in the order they appear (Persian digits included)."""
    if not text:
        return []
    s = str(text)
    for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹"):
        s = s.replace(c, str(i))
    return re.findall(r"\d+(?:[.,]\d+)?\s*(?:%|٪|درصد|دلار|تومان|میلیارد|میلیون|هزار)?", s)


def _sentences(text: str) -> list:
    if not text:
        return []
    parts = re.split(r"(?<=[.!?؟।])\s+|\n+", str(text))
    return [p.strip() for p in parts if len(p.strip()) > 12]


def _age_hours(article: dict, now: float) -> float:
    ts = article.get("published_ts") or 0
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        return 0.0
    if ts > 1e11:                     # milliseconds
        ts /= 1000.0
    return max(0.0, (now - ts) / 3600.0) if ts else 24.0


def _norm(value, ref, cap=1.0):
    """Log-normalise a rate against a reference value, clipped to [0, cap].

    Used for the *reported* heat of a story; the score itself uses percentiles,
    because a fixed reference saturates: one viral international clip pins every
    gold story at 1.0 and the factor stops telling them apart.
    """
    if not value or value <= 0:
        return 0.0
    return min(cap, math.log1p(value) / math.log1p(ref))


def percentiles(values):
    """Rank values as 0..1 over this corpus, ties sharing their average rank.

    Zero and missing stay zero: "nobody is talking about this yet" is a fact,
    not a mid-table average.
    """
    ordered = sorted(v for v in values if v and v > 0)
    out = {}
    n = len(ordered)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1] == ordered[i]:
            j += 1
        out[ordered[i]] = ((i + j) / 2.0 + 0.5) / n
        i = j + 1
    return out


# ───────────────────────────── signal matching ─────────────────────────────

def _words(text) -> set:
    raw = re.sub(r"[^\w\u0600-\u06FF&%]+", " ", str(text or ""))
    return {w.lower() for w in raw.split() if len(w) > 2 and w.lower() not in STOPWORDS}


def match_signals(article: dict, signals: dict) -> dict:
    """Which live demand items could be talking about this story.

    Matching is token overlap between the item's own text and the article — an
    asset name counts as a token, so «طلا» in a Telegram post and XAU in the
    corpus meet in the middle. No match means no signal: a hot video about
    something else must not lift this article's score.

    The returned lists are *claims*, not final credit — several articles can
    claim the same viral clip, and ``claim_signals`` downstream gives each clip
    to the article it overlaps most (see the note there).
    """
    toks = tokens(article)
    out = {"youtube_all": [], "telegram_all": [], "reddit_all": []}

    yt = (signals or {}).get("youtube") or {}
    for video in (yt.get("videos") or []):
        hits = _overlap(_words(video.get("title")), toks)
        query_hits = _overlap(_words(video.get("query")), toks)
        if hits < 2 and (hits < 1 or query_hits < 1):
            continue
        out["youtube_all"].append(dict(video, hits=hits + query_hits,
                                       key=video.get("id") or video.get("url")))

    tg = (signals or {}).get("telegram") or {}
    medians = {c.get("channel"): (c.get("median_views") or 0) for c in (tg.get("channels") or [])}
    for post in (tg.get("posts") or []):
        hits = _overlap(_words(post.get("text")), toks)
        if hits < 2:
            continue
        median = medians.get(post.get("channel")) or 0
        rel = (post.get("views") / median) if (post.get("views") and median) else None
        out["telegram_all"].append(dict(post, rel=rel, hits=hits,
                                        key=post.get("url") or (post.get("channel"), post.get("post_id"))))

    rd = (signals or {}).get("reddit") or {}
    for post in (rd.get("posts") or []):
        hits = _overlap(_words(post.get("title")), toks)
        if hits < 2:
            continue
        out["reddit_all"].append(dict(post, hits=hits, key=post.get("link")))
    return out


def claim_signals(claims: list, credibility_of) -> list:
    """Give each demand item to the article that overlaps it most.

    Without this, one viral gold clip credits every gold story of the day and
    the factor stops separating them. Ties go to the article whose own coverage
    looks more specific (more overlapping words), then to the more credible
    one, so the signal lands where it actually belongs.
    """
    best_owner: dict = {}
    for idx, per_article in enumerate(claims):
        for source in ("youtube_all", "telegram_all", "reddit_all"):
            for item in per_article.get(source) or []:
                key = (source, item.get("key"))
                score_key = (item.get("hits") or 0, credibility_of(idx))
                if key not in best_owner or score_key > best_owner[key][0]:
                    best_owner[key] = (score_key, idx)
    out = []
    for idx, per_article in enumerate(claims):
        kept = {"youtube_all": [], "telegram_all": [], "reddit_all": []}
        for source in kept:
            for item in per_article.get(source) or []:
                owner = best_owner.get((source, item.get("key")))
                if owner and owner[1] == idx:
                    kept[source].append(item)
        out.append(kept)
    return out


def aggregate_signals(kept: dict) -> dict:
    """Turn one article's surviving claims into the factors the score reads."""
    yt_items = sorted(kept.get("youtube_all") or [],
                      key=lambda v: -(v.get("views_per_hour") or 0))
    tg_items = sorted(kept.get("telegram_all") or [],
                      key=lambda p: (-(p.get("views_per_hour") or 0), -(p.get("rel") or 0)))
    rd_items = sorted(kept.get("reddit_all") or [],
                      key=lambda p: -(p.get("score_per_hour") or 0))
    tg = None
    if tg_items:
        tg = {"best": tg_items[0], "count": len(tg_items),
              "sum_vph": sum((p.get("views_per_hour") or 0) for p in tg_items[:3]),
              "best_rel": max([p["rel"] for p in tg_items if p.get("rel")] or [0])}
    return {"youtube": yt_items[0] if yt_items else None,
            "telegram": tg,
            "reddit": rd_items[0] if rd_items else None,
            "matches": {"youtube": len(yt_items), "telegram": len(tg_items),
                        "reddit": len(rd_items)}}


def coverage_counts(articles: list) -> dict:
    """How many distinct sources carry the same story (title-token similarity)."""
    packs = [(a.get("id"), tokens(a), a.get("source_key") or a.get("source_name")) for a in articles]
    counts = {}
    for i, (aid, toks, _src) in enumerate(packs):
        sources = set()
        for j, (_oid, otoks, osrc) in enumerate(packs):
            if i == j or not toks or not otoks:
                continue
            shared = len(toks & otoks)
            ratio = shared / max(1, min(len(toks), len(otoks)))
            if shared >= 3 and ratio >= 0.34:
                sources.add(osrc)
        counts[aid] = len([s for s in sources if s])
    return counts


def _title_key(article: dict) -> str:
    text = str(article.get("title_fa") or article.get("title") or "")
    text = re.sub(r"[^\w\u0600-\u06FF]+", " ", text).strip().lower()
    return " ".join(text.split()[:6])


# ───────────────────────────── format choice ─────────────────────────────

def format_scores(article: dict, signal: dict) -> dict:
    """How each format fits this story, with the reason spelled out.

    carousel — several independent points, numbers, or a comparison;
    video    — one dramatic move, or a story that is easier told than read;
    text     — everything else: the honest default, not a failure.
    """
    body = " ".join(_sentences(article.get("summary_fa") or article.get("summary") or ""))
    nums = _numbers(body)[:20]
    sents = _sentences(article.get("summary_fa") or article.get("summary") or "")
    dramatic = sum(1 for w in DRAMATIC if w in _text_of(article).lower())
    has_move = any(re.search(r"\d", n) and ("%" in n or "٪" in n or "درصد" in n) for n in nums)

    carousel = 0.30 + 0.12 * min(4, len(nums)) + 0.10 * min(3, len(sents)) + (0.15 if len(nums) >= 3 else 0)
    video = 0.25 + 0.22 * min(2, dramatic) + (0.15 if has_move else 0)
    if (signal.get("youtube") or {}).get("views_per_hour"):
        video += 0.10
    if (signal.get("telegram") or {}).get("sum_vph"):
        carousel += 0.08
    text = 0.55 - 0.05 * min(3, len(sents)) + (0.10 if len(nums) <= 1 else 0)
    scores = {"text": round(min(1.0, text), 2), "carousel": round(min(1.0, carousel), 2),
              "video": round(min(1.0, video), 2)}
    best = max(scores, key=lambda k: scores[k])
    labels = {"text": "متن", "carousel": "کاروسل", "video": "ویدیو"}
    why = {
        "carousel": "چند نکته و عدد مستقل دارد؛ در اسلایدهای جدا بهتر خوانده می‌شود.",
        "video": "حرکت/رویداد دراماتیک دارد و تقاضای ویدیویی بالایی برای موضوعش هست.",
        "text": "تک‌نکته‌ای و کوتاه است؛ متن سریع‌تر و صادقانه‌تر منتقلش می‌کند.",
    }[best]
    return {"best": best, "best_label": labels[best], "scores": scores, "why": why,
            "numbers": nums[:8], "sentences": len(sents), "dramatic": dramatic}


# ───────────────────────────── ranking ─────────────────────────────

def _cfg(config: dict | None) -> dict:
    cfg = ((config or {}).get("content_studio") or {})
    return cfg if isinstance(cfg, dict) else {}


def rank(articles: list, config: dict | None = None, signals: dict | None = None,
         now: float | None = None, recent_keys: set | None = None) -> dict:
    """Rank the live corpus. Returns {"items": [...], "gated": n, "notes": [...]}."""
    cfg = _cfg(config)
    now = now or time.time()
    gate = float(cfg.get("credibility_gate") or 0.6)
    half_life = float(cfg.get("half_life_hours") or 6.0)
    weights = dict(DEFAULT_WEIGHTS)
    weights.update({k: float(v) for k, v in (cfg.get("weights") or {}).items()
                    if k in DEFAULT_WEIGHTS and isinstance(v, (int, float))})
    asset_weights = dict(DEFAULT_ASSET_WEIGHTS)
    asset_weights.update({str(k).upper(): float(v) for k, v in (cfg.get("asset_weights") or {}).items()
                          if isinstance(v, (int, float))})
    recent_keys = recent_keys or set()
    signals = signals if signals is not None else {}

    coverage = coverage_counts(articles)
    eligible = [a for a in (articles or []) if float(a.get("credibility") or 0) >= gate]
    gated = len(articles or []) - len(eligible)
    claims = claim_signals([match_signals(a, signals) for a in eligible],
                           lambda i: float(eligible[i].get("credibility") or 0))
    cands = []
    for idx, a in enumerate(eligible):
        cred = float(a.get("credibility") or 0)
        syms = _assets(a)
        audience_raw = max([asset_weights.get(s, 0.8) for s in syms] or [0.5])
        signal = aggregate_signals(claims[idx])
        age = _age_hours(a, now)
        fresh = 0.5 ** (age / half_life) if half_life > 0 else 1.0

        yt = signal.get("youtube") or {}
        tg = signal.get("telegram") or {}
        rd = signal.get("reddit") or {}
        # relative demand blended with the channel's own baseline: 60k views on a
        # channel that always gets 20k is a weaker story than 3k on one that
        # usually gets 200, and only the second number captures that
        tg_raw = (0.65 * (tg.get("sum_vph") or 0) +
                  0.35 * (tg.get("best_rel") or 0) * (REF_TELEGRAM_VPH / TELEGRAM_REL_CAP))
        cands.append({
            "article": a,
            "signal": signal,
            "coverage": coverage.get(a.get("id"), 0),
            "raw": {"credibility": cred, "coverage": coverage.get(a.get("id"), 0),
                    "audience": audience_raw, "freshness": fresh,
                    "youtube": yt.get("views_per_hour") or 0,
                    "telegram": tg_raw,
                    "reddit": rd.get("score_per_hour") or 0},
            "yt": yt, "tg": tg, "rd": rd,
            "heat": {"youtube_vph": round(yt.get("views_per_hour") or 0, 1),
                     "telegram_vph": round(tg.get("sum_vph") or 0, 1),
                     "telegram_rel": round(tg.get("best_rel") or 0, 2),
                     "reddit_sph": round(rd.get("score_per_hour") or 0, 2)},
            "syms": syms, "age": age,
        })

    # demand factors are ranked inside this corpus (see percentiles()), while
    # credibility / freshness / audience keep their absolute meaning
    pct = {key: percentiles([c["raw"][key] for c in cands])
           for key in ("coverage", "youtube", "telegram", "reddit")}

    items = []
    for c in cands:
        a, signal, syms, age = c["article"], c["signal"], c["syms"], c["age"]
        yt, tg, rd = c["yt"], c["tg"], c["rd"]
        factors = {
            "credibility": round(c["raw"]["credibility"], 3),
            "coverage": round(pct["coverage"].get(c["raw"]["coverage"], 0.0), 3),
            "audience": round(min(1.0, c["raw"]["audience"] / 1.5), 3),
            "freshness": round(c["raw"]["freshness"], 3),
            "youtube": round(pct["youtube"].get(c["raw"]["youtube"], 0.0), 3),
            "telegram": round(pct["telegram"].get(c["raw"]["telegram"], 0.0), 3),
            "reddit": round(pct["reddit"].get(c["raw"]["reddit"], 0.0), 3),
        }
        total_w = sum(weights.values()) or 1.0
        raw = sum(weights[k] * factors[k] for k in weights) / total_w

        repeat = _title_key(a) in recent_keys or a.get("id") in recent_keys
        if repeat:
            raw *= float(cfg.get("repeat_penalty") or 0.35)

        fmt = format_scores(a, signal)
        items.append({
            "id": a.get("id"),
            "title": a.get("title") or "",
            "title_fa": a.get("title_fa") or a.get("title") or "",
            "summary_fa": a.get("summary_fa") or a.get("summary") or "",
            "source": a.get("source_name") or a.get("source_key") or "",
            "link": a.get("link") or "",
            "assets": syms,
            "published_ts": a.get("published_ts"),
            "age_hours": round(age, 1),
            "credibility": round(cred, 3),
            "score": round(100.0 * raw, 1),
            "factors": factors,
            "heat": c["heat"],
            "repeat": repeat,
            "format": fmt,
            "why": (fmt.get("why") or "رتبه‌بندی بر پایه اعتبار و تقاضا"),
            "signals": {
                "youtube": {"title": yt.get("title"), "channel": yt.get("channel"),
                            "views": yt.get("views"), "vph": yt.get("views_per_hour"),
                            "url": yt.get("url"), "likes": yt.get("likes"),
                            "hits": signal["matches"]["youtube"]},
                "telegram": {"count": signal["matches"]["telegram"],
                             "sum_vph": round(tg.get("sum_vph") or 0, 1),
                             "best_rel": round(tg.get("best_rel") or 0, 2),
                             "text": (tg.get("best") or {}).get("text", "")[:160],
                             "channel": (tg.get("best") or {}).get("channel"),
                             "url": (tg.get("best") or {}).get("url")},
                "reddit": {"title": (rd or {}).get("title"), "sub": (rd or {}).get("sub"),
                           "score": (rd or {}).get("score"), "comments": (rd or {}).get("comments"),
                           "sph": (rd or {}).get("score_per_hour"),
                           "hits": signal["matches"]["reddit"]},
            },
        })

    items.sort(key=lambda i: -i["score"])
    notes = []
    if gated:
        notes.append(f"{gated} خبر زیر آستانهٔ اعتبار ({gate:.0%}) از فهرست حذف شد.")
    if not items:
        notes.append("هیچ خبری از دروازهٔ اعتبار و تازگی عبور نکرد.")
    return {"items": items, "gated": gated, "notes": notes,
            "gate": gate, "generated_ts": now}


# ───────────────────────────── drafting ─────────────────────────────

DRAFT_SYSTEM = """تو مسئول ویرایش نهایی اخبار مالی برای انتشار در Telegram، بله و استودیو محتوا هستی.

ورودی تو یک خبر مالی است. وظیفه تو این است که از متن موجود، مهم‌ترین اطلاعات خبری را استخراج، خلاصه و برای خواندن سریع در کمتر از ۱۵ ثانیه بازنویسی کنی.

قوانین اساسی:
1. هدف خواننده: در چند ثانیه متوجه شود چه اتفاقی افتاده، مربوط به چه بازاری است، عدد یا تغییر مهم چیست، دلیل اصلی چه بوده و واکنش مستقیم بازار چه بوده است.
2. اولویت اطلاعات: حفظ کامل قیمت‌ها، اعداد، درصدها، نرخ بهره، تصمیمات بانک مرکزی و داده‌های اقتصادی. هرگز اعداد را حذف یا گرد نکن.
3. عدم تحلیل شخصی: هرگز از خودت تحلیل، پیش‌بینی یا نتیجه‌گیری که در متن اصلی نیست نساز.
4. عنوان: ۱۰ تا ۱۵ کلمه، کاملاً خبری و حرفه‌ای بدون کلیک‌بیت.
5. ایموجی‌ها: نقش برچسب بصری دارند (حداکثر ۳ تا ۵ ایموجی در کل متن). ایموجی بازار فقط یک بار در ابتدای خبر و قبل از تیتر می‌آید. هرگز در پایان جملات ایموجی نگذار.
   (🟡 طلا | ⚪ نقره | 💵 دلار | 💶 یورو | ₿ کریپتو | 🛢️ نفت | 🏦 بانک مرکزی | 📊 داده اقتصادی | 📈 صعود/رکورد | 📉 افت شدید | 🚨 فوری | 💰 مالی)
6. ساختار کپشن:
   [EMOJI بازار] **عنوان کوتاه و خبری**

   خلاصه خبر در ۲ تا ۴ جمله شامل اتفاق اصلی، عدد مهم، عامل محرک و واکنش بازار.

   📌 **نکته مهم:** [تنها در صورتی که نکته مجزا و کلیدی وجود دارد در یک جمله کوتاه]

خروجی باید دقیقاً شامل این تگ‌ها باشد:

<caption>
پست کامل طبق ساختار استاندارد بالا
</caption>
<slides>
<slide title="عنوان کوتاه">متن اسلاید در حداکثر دو جمله</slide>
(۵ تا ۸ اسلاید: اسلاید قلاب، اسلایدهای نکات و آمارها، اسلاید پایانی منبع و سلب مسئولیت)
</slides>
<script>
<scene sec="0-3" on_screen="متن روی تصویر">روایت گوینده</scene>
(۴ تا ۶ صحنه، ۳۰ تا ۶۰ ثانیه مجموعاً)
</script>
<hashtags>#طلا #بیت‌کوین</hashtags>
"""


def _article_block(article: dict) -> str:
    def clean(v):
        return str(v or "").replace("<", "‹").replace(">", "›").strip()

    lines = [
        f"<news id=\"{clean(article.get('id'))}\" source=\"{clean(article.get('source_name') or article.get('source_key'))}\""
        f" credibility=\"{(float(article.get('credibility') or 0) * 100):.0f}\""
        f" assets=\"{clean(','.join(_assets(article)))}\">",
        f"  <title>{clean(article.get('title'))}</title>",
        f"  <title_fa>{clean(article.get('title_fa'))}</title_fa>",
        f"  <summary_fa>{clean(article.get('summary_fa'))}</summary_fa>",
        f"  <summary>{clean(article.get('summary'))}</summary>",
        f"  <link>{clean(article.get('link'))}</link>",
        "</news>",
    ]
    return "\n".join(lines)


def _tag(text: str, name: str) -> str:
    m = re.search(rf"<{name}>(.*?)</{name}>", text or "", re.S)
    return (m.group(1).strip() if m else "")


def parse_draft(text: str) -> dict:
    """Read the model's block format; tolerate a missing wrapper."""
    if not text:
        return {}
    caption = _tag(text, "caption")
    slides_html = _tag(text, "slides")
    script_html = _tag(text, "script")
    hashtags = _tag(text, "hashtags")
    slides = []
    for m in re.finditer(r"<slide([^>]*)>(.*?)</slide>", slides_html, re.S):
        tm = re.search(r'title="([^"]*)"', m.group(1) or "")
        title = tm.group(1).strip() if tm else ""
        body = re.sub(r"\s+", " ", m.group(2)).strip()
        if title or body:
            slides.append({"title": title, "body": body})
    def attr(attrs: str, name: str) -> str:
        found = re.search(rf'{name}="([^"]*)"', attrs or "")
        return found.group(1).strip() if found else ""

    scenes = []
    for m in re.finditer(r"<scene([^>]*)>(.*?)</scene>", script_html, re.S):
        attrs = m.group(1) or ""
        sec = attr(attrs, "sec")
        on_screen = attr(attrs, "on_screen")
        body = re.sub(r"\s+", " ", m.group(2)).strip()
        if body or on_screen:
            scenes.append({"sec": sec, "on_screen": on_screen, "narration": body})
    if not caption and not slides and not scenes:
        # the model skipped the wrapper: keep its prose as a caption rather than
        # showing the reader an empty card
        caption = re.sub(r"\s+", " ", str(text)).strip()[:1200]
    return {"caption": caption, "slides": slides, "scenes": scenes,
            "hashtags": [h for h in re.split(r"[\s,]+", hashtags or "") if h.startswith("#")]}


def template_draft(article: dict, fmt: dict | None = None) -> dict:
    """No-AI path: strictly follows the 17 financial editorial standards."""
    import news_editorial
    raw_title = article.get("title_fa") or article.get("title") or ""
    summary = article.get("summary_fa") or article.get("summary") or ""
    source = article.get("source_name") or article.get("source_key") or ""
    cred = int(round(float(article.get("credibility") or 0) * 100))
    sents = _sentences(summary)

    # the summary's opening sentence is usually the headline again — quoting it
    # back makes the caption read like a stutter
    def _same_as_title(s: str) -> bool:
        a = set(re.sub(r"[^\w\u0600-\u06FF]+", " ", s.lower()).split())
        b = set(re.sub(r"[^\w\u0600-\u06FF]+", " ", raw_title.lower()).split())
        if not a or not b:
            return False
        return len(a & b) / max(1, min(len(a), len(b))) >= 0.6

    body_sents = [s for s in sents if not _same_as_title(s)]
    nums = (fmt or {}).get("numbers") or _numbers(summary)[:8]

    emoji = news_editorial.detect_market_emoji(article)
    title_line = f"{emoji} **{raw_title}**"
    body_text = " ".join(body_sents[:3]) if body_sents else summary
    key_note = f"\n\n📌 **نکته کلیدی:** ارقام کلیدی: {' · '.join(nums[:4])}" if nums else ""
    footer = f"\n\nمنبع: {source} · اعتبار {cred}٪ — {FOOTER_FA}"

    caption = f"{title_line}\n\n{body_text}{key_note}{footer}"

    slides = [{"title": "تیتر", "body": raw_title}]
    for s in body_sents[:4]:
        slides.append({"title": s[:40], "body": s})
    if nums:
        slides.append({"title": "اعداد کلیدی", "body": " · ".join(nums[:5])})
    slides.append({"title": "منبع و اعتبار",
                   "body": f"{source} · اعتبار {cred}٪ — {FOOTER_FA}"})
    scenes = [
        {"sec": "0-4", "on_screen": raw_title[:48], "narration": raw_title},
        {"sec": "4-14", "on_screen": "",
         "narration": body_sents[0] if body_sents else summary[:120]},
        {"sec": "14-25", "on_screen": "",
         "narration": body_sents[1] if len(body_sents) > 1 else ""},
        {"sec": "25-35", "on_screen": "منبع: " + source,
         "narration": (nums[0] if nums else "") + " — " + FOOTER_FA},
    ]
    scenes = [s for s in scenes if s["narration"] or s["on_screen"]]
    tags = ["#" + (a or "") for a in _assets(article)][:4]
    return {"caption": caption, "slides": slides, "scenes": scenes,
            "hashtags": tags, "method": "template"}


def draft(article: dict, fmt: dict | None = None, use_ai: bool = True) -> dict:
    """Draft the post: AI when a key is configured, template otherwise."""
    out = template_draft(article, fmt)
    if not use_ai:
        return out
    try:
        import ai_features
        user_turn = (f"<news>\n{_article_block(article)}\n</news>\n\n"
                     f"Format: {(fmt or {}).get('best_label', 'متن')}.\n"
                     "Write the caption, the slides and the video script.\n")
        text = ai_features._call_openai(user_turn, max_tokens=1400,
                                        system=DRAFT_SYSTEM, temperature=0.4)
    except Exception:
        text = None
    if not text:
        out["ai_error"] = "کلید هوش مصنوعی تنظیم نشده یا پاسخ نداد؛ نسخهٔ قالب‌محور تولید شد."
        return out
    parsed = parse_draft(text)
    if not (parsed.get("caption") or parsed.get("slides")):
        out["ai_error"] = "پاسخ مدل خوانده نشد؛ نسخهٔ قالب‌محور تولید شد."
        return out
    merged = dict(out)
    merged.update({k: v for k, v in parsed.items() if v})
    merged["method"] = "ai"
    return merged


def status(config: dict | None = None) -> dict:
    """Everything the studio tab needs to explain itself."""
    cfg = _cfg(config)
    return {
        "gate": float(cfg.get("credibility_gate") or 0.6),
        "weights": {**DEFAULT_WEIGHTS, **(cfg.get("weights") or {})},
        "half_life_hours": float(cfg.get("half_life_hours") or 6.0),
        "repeat_penalty": float(cfg.get("repeat_penalty") or 0.35),
        "scales": {"youtube_vph": REF_YOUTUBE_VPH, "telegram_vph": REF_TELEGRAM_VPH,
                   "reddit_sph": REF_REDDIT_SPH, "coverage": COVERAGE_CAP},
    }
