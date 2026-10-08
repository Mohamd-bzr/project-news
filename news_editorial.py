"""news_editorial.py — Standardized Editorial Engine for Financial News.
==================================================================
Implements the 17 professional editorial rules for publishing financial news
across Telegram, Bale messenger, and Content Studio (استودیو محتوا).

Core Rules & Guidelines:
1. Fast consumption: Reader grasps within 15 seconds:
   - What happened?
   - Which asset/market?
   - Key number, price level, or % change?
   - Primary driver/catalyst?
   - Direct market reaction?
2. Preserves all numbers, prices, percentages, central bank decisions, economic data.
3. Strict visual emoji tags at start of title only (🟡, ⚪, 💵, 💶, ₿, 🛢️, 🏦, 📊, 📈, 📉, 🚨, 💰).
   No emojis at ends of sentences; max 3-5 emojis per post.
4. Summary: 2 to 4 coherent sentences (never chopped off mid-sentence).
5. Structure:
   [EMOJI بازار] **عنوان کوتاه و خبری (۱۰ تا ۱۵ کلمه)**

   خلاصه خبر در ۲ تا ۴ جمله شامل اتفاق اصلی، عدد/درصد کلیدی، دلیل یا محرک، و واکنش بازار.

   📌 **نکته مهم:** [تنها در صورتی که نکته مجزا و کلیدی وجود دارد]
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


FINANCIAL_EDITORIAL_SYSTEM_PROMPT = """تو مسئول ویرایش نهایی اخبار مالی برای انتشار در Telegram، بله و استودیو محتوا هستی.

ورودی تو یک خبر مالی خام است که ممکن است کوتاه، متوسط یا بسیار طولانی باشد.
وظیفه تو این نیست که خبر را از نو تحلیل کنی یا اطلاعات جدید به آن اضافه کنی. وظیفه تو این است که از متن موجود، مهم‌ترین اطلاعات خبری را استخراج، خلاصه و برای خواندن سریع در کمتر از ۱۵ ثانیه بازنویسی کنی.

## هدف
خواننده باید با خواندن خروجی در چند ثانیه متوجه شود:
* چه اتفاقی افتاده؟
* مربوط به چه بازار یا دارایی‌ای است؟
* عدد یا تغییر مهم چیست؟
* دلیل یا عامل اصلی چه بوده؟
* اگر خبر حاوی اثر مستقیم بر بازار است، این اثر چیست؟

## قوانین استخراج و نگارش:
1. اولویت اول (حتماً حفظ شود):
   اتفاق اصلی خبر، قیمت یا سطح مهم، درصد رشد یا افت، رکورد جدید یا شکست سطح مهم، تصمیم بانک مرکزی، داده اقتصادی مهم (CPI، NFP، نرخ بهره و...)، آمار اقتصادی، پیش‌بینی یا برآورد رسمی، اظهارنظر مهم مقام یا مدیر، عامل مستقیم حرکت بازار.
2. اولویت دوم (در صورت وجود حفظ شود):
   دلیل اصلی اتفاق، واکنش بازار، سطوح تکنیکال، مقایسه با دوره قبل، زمان‌بندی رویداد بعدی.
3. حذفیات ضروری:
   توضیحات تکراری، تاریخچه طولانی، معرفی طولانی شرکت/دارایی، نقل‌قول‌های طویل، تبلیغات، جملات کلی و مقدمه‌چینی.
4. قانون طلایی خلاصه:
   اتفاق اصلی → عدد/داده مهم → دلیل یا محرک → نتیجه یا واکنش بازار.
5. طول خلاصه:
   برای خبرهای معمولی: ۲ تا ۴ جمله روان. برای خبر بسیار مهم: حداکثر ۵ جمله. برای خبر کوتاه: ۱ تا ۲ جمله.
6. عنوان:
   حداکثر ۱۰ تا ۱۵ کلمه، خبری، جذاب و بدون کلیک‌بیت. عنوان نباید فقط نام دارایی باشد.
7. ایموجی‌ها:
   ایموجی فقط برچسب بصری است، نه تزئین. حداکثر ۳ تا ۵ ایموجی در کل پست.
   ایموجی بازار فقط یک بار در ابتدای خبر و قبل از تیتر می‌آید. هرگز در انتهای هر جمله ایموجی نگذار!
   ایموجی‌های مجاز:
   🟡 طلا | ⚪ نقره | 💵 دلار | 💶 یورو | ₿ بیت‌کوین و کریپتو | 🛢️ نفت و انرژی | 🏦 بانک مرکزی | 📊 داده‌های اقتصادی | 📈 صعود/رکورد | 📉 افت شدید | 🚨 خبر فوری | 💰 بازار مالی
8. حفظ کامل اعداد:
   در اخبار مالی عددها بخش اصلی خبر هستند. قیمت، درصد، نرخ بهره، تورم و ارقام کلیدی را هرگز حذف نکن و گرد نکن.
9. بدون تحلیل شخصی:
   هرگز پیش‌بینی، توصیه یا تحلیلی که در متن خبر وجود ندارد از خودت نساز.
10. نقل‌قول‌ها:
    به جای آوردن کل نقل‌قول، مفهوم اصلی را در یک جمله خلاصه کن.

## ساختار خروجی استاندارد:
[EMOJI بازار] **عنوان کوتاه و خبری**

خلاصه خبر در ۲ تا ۴ جمله، شامل اتفاق اصلی، عدد مهم، عامل اصلی و واکنش بازار در صورت وجود.

📌 **نکته مهم:** فقط در صورتی که یک نکته بسیار مهم و مشخص وجود دارد، یک جمله کوتاه اضافه کن (اگر چیز جدیدی اضافه نمی‌کند، اصلاً ننویس).
"""


def detect_market_emoji(article: Dict[str, Any]) -> str:
    """Detect the most appropriate visual emoji tag based on asset, topic, and sentiment."""
    title = str(article.get("title_fa") or article.get("title") or "").strip().lower()
    summary = str(article.get("summary_fa") or article.get("summary") or "").strip().lower()
    text = f"{title} {summary}"

    assets = [str(a).upper() for a in (article.get("assets") or [])]

    # 1. Breaking news
    if any(w in text for w in ("خبر فوری", "فوری:", "breaking news", "flash news", "alert:")):
        return "🚨"

    # 2. Tech / AI
    if any(a in assets for a in ("NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA")) or any(w in text for w in ("هوش مصنوعی", "تراشه", "انویدیا", "اوپن ای آی", "چت جی پی تی", "ai", "nvidia", "apple", "semiconductor", "openai")):
        return "🤖"

    # 3. Central banks / Interest rates
    if any(w in text for w in ("بانک مرکزی", "فدرال رزرو", "پاول", "لاگارد", "نرخ بهره", "fomc", "central bank", "ecb", "سیاست پولی")):
        return "🏦"

    # 4. Macro / Economic data releases
    if any(w in text for w in ("cpi", "nfp", "gdp", "pmi", "تورم", "تولید ناخالص", "اشتغال", "بیکاری", "خرده‌فروشی", "خرده فروشی", "شاخص قیمت")):
        return "📊"

    # 5. Gold & Precious metals
    if "XAU" in assets or any(w in text for w in ("طلا", "اونس", "انس جهانی", "gold", "xau")):
        return "🟡"
    if "XAG" in assets or any(w in text for w in ("نقره", "silver", "xag")):
        return "⚪"

    # 6. Crypto
    if any(a in assets for a in ("BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE")) or any(w in text for w in ("بیت‌کوین", "بیت کوین", "کریپتو", "اتریوم", "رمزارز", "ارز دیجیتال", "bitcoin", "crypto")):
        return "₿"

    # 7. Oil & Energy
    if any(a in assets for a in ("WTI", "BRENT")) or any(w in text for w in ("نفت", "اوپک", "برنت", "نفت خام", "بنزین", "oil", "crude", "brent", "opec")):
        return "🛢️"

    # 8. Fiat Currencies
    if "DXY" in assets or any(w in text for w in ("شاخص دلار", "اسکناس آمریکایی", "dxy", "قیمت دلار", "نرخ دلار", "دلار آمریکا")):
        return "💵"
    if any(w in text for w in ("یورو", "eur", "euro")):
        return "💶"
    if "دلار" in title or "dollar" in title:
        return "💵"

    # 8. US / American Economy
    if any(w in text for w in ("آمریکا", "آمریکایی", "سیتی", "واشنگتن", "ایالات متحده", "us ", "u.s.", "citi")):
        return "🇺🇸"

    # 8. Severe Drops / Surges
    if any(w in text for w in ("سقوط", "ریزش شدید", "افت سنگین", "افت ۳", "افت ۴", "افت ۵", "افت ۶", "افت ۷", "افت ۸", "افت ۹", "افت ۱۰", "crash", "plunge", "slump")):
        return "📉"
    if any(w in text for w in ("رکورد تاریخی", "جهش شدید", "رشد چشمگیر", "قله تاریخی", "all-time high", "ath", "surge")):
        return "📈"

    # 9. Corporate / Industry
    if any(w in text for w in ("سهام شرکت", "درآمد فصلی", "بورس تهران", "وال استریت", "سهامداران")):
        return "🏭"

    # 10. Default financial market
    return "💰"


def clean_editorial_title(title: str, max_words: int = 15) -> str:
    """Sanitize title: strip existing emoji prefixes, clickbait, and keep to 10-15 words."""
    title = re.sub(r"^[\s\u200c]*[🟡⚪💵💶₿🛢️🏦🌍🏭📊💰⚠️🚨📈📉📌🔥⚡🔴🟢🏅🔔📰🕒🔗]+\s*", "", title)
    title = re.sub(r"^(خبر فوری|فوری\s*[:|]|breaking\s*[:|])\s*", "", title, flags=re.I)
    title = title.strip()

    words = title.split()
    if len(words) > max_words:
        # Keep first max_words, ensuring not cutting off an open quote or bad join
        title = " ".join(words[:max_words]).rstrip("،,:؛- ") + "…"
    return title


# Contrast markers: the sentence that turns the story («با این حال»…) opens
# the caveat block — the ‼️ paragraph of the editorial template.
_CONTRAST_MARKERS = (
    "بااین‌حال", "با این حال", "بااین حال", "با این‌حال",
    "اما ", "اما،", "هرچند", "هر چند", "درحالی‌که", "در حالی که",
    "با وجود", "در عین حال", "البته", "با این وجود", "در مقابل",
    "از سوی دیگر", "در عوض", " nevertheless",
)


def split_sentences(text: str) -> List[str]:
    """Sentence split that knows a Persian decimal point is not a full stop.

    «۱.۲ درصد رشد کرد.» used to break after «۱.» — the newsletter and the
    digest both showed a block ending in a bare «۱.». A «.» sitting between
    two digits is a decimal separator (or a «۲.» ordinal), so the two halves
    are stitched back together before anything downstream sees them.
    """
    out: List[str] = []
    for part in re.split(r"(?<=[.!?؟])\s+|\n+", str(text or "")):
        part = part.strip()
        if not part:
            continue
        if out and re.search(r"\d\.$", out[-1]) and re.match(r"^\d", part):
            out[-1] = f"{out[-1]} {part}"      # was a decimal point, not a stop
        else:
            out.append(part)
    return out


def editorial_blocks(summary_text: str) -> Tuple[str, str]:
    """Split a summary into (lead, caveat) paragraphs for the editorial
    template: every sentence before the first contrast marker is the lead,
    that marker's sentence onward is the caveat. Formatting only — no word
    of the summary is rewritten."""
    sents = split_sentences(summary_text)
    if len(sents) < 2:
        return (str(summary_text or "").strip(), "")
    cut = None
    for idx, sent in enumerate(sents[1:], start=1):
        if any(m in sent for m in _CONTRAST_MARKERS):
            cut = idx
            break
    if cut is None:
        return (" ".join(sents), "")
    lead = " ".join(sents[:cut])
    caveat = " ".join(sents[cut:])
    return (lead, caveat)


# ── the content-ideas push: 500-1000 chars summary in clean paragraphs ────────
IDEAS_SUMMARY_CHARS = 1000


# end-of-thought marks, best first: a sentence end reads finished
_IDEAS_CUT_MARKS = (".", "؟", "!")


def ideas_summary(summary_text: str,
                  max_chars: int = IDEAS_SUMMARY_CHARS) -> Tuple[str, str]:
    """A clean summary up to 1000 characters, formatted in complete sentences.

    Never chops a single sentence in half. Cuts only on complete sentence ends
    (., !, ؟) and strips any trailing dangling conjunctions (، و...).
    """
    text = " ".join(str(summary_text or "").split()).strip()
    if not text:
        return ("", "")

    # Clean up awkward trailing conjunctions or punctuation
    text = re.sub(r'[\s،,;؛]+(?:و|یا|اما|که|به)$', '', text).strip()

    if len(text) > max_chars:
        head = text[:max_chars]
        sentence_ends = [head.rfind(m) for m in _IDEAS_CUT_MARKS]
        best_cut = max(sentence_ends)
        if best_cut > int(max_chars * 0.4):
            text = head[:best_cut + 1].strip()
        else:
            word = head.rfind(" ")
            stem = head[:word] if word > 0 else text[:max_chars - 1]
            text = stem.rstrip(" ،؛,;:-،٫") + "…"

    text = re.sub(r'[\s،,;؛]+(?:و|یا|اما|که|به)$', '', text).strip()

    lead, caveat = editorial_blocks(text)
    if lead and caveat:
        lead = re.sub(r'[\s،,;؛]+(?:و|یا|اما|که|به)$', '', lead).strip()
        caveat = re.sub(r'[\s،,;؛]+(?:و|یا|اما|که|به)$', '', caveat).strip()
        return (lead, caveat)

    sents = split_sentences(text)
    if len(sents) >= 2:
        middle = len(text) / 2
        cut = min(range(1, len(sents)),
                  key=lambda i: abs(len(" ".join(sents[:i])) - middle))
        lead = " ".join(sents[:cut]).strip()
        caveat = " ".join(sents[cut:]).strip()
        lead = re.sub(r'[\s،,;؛]+(?:و|یا|اما|که|به)$', '', lead).strip()
        caveat = re.sub(r'[\s،,;؛]+(?:و|یا|اما|که|به)$', '', caveat).strip()
        return (lead, caveat)

    # When there is only 1 sentence, keep it intact as lead; never chop mid-sentence
    return (text, "")


def format_editorial_summary(summary_text: str, min_sents: int = 2, max_sents: int = 4) -> Tuple[str, Optional[str]]:
    """Organize summary text into 2-4 key sentences, retaining numbers and drivers.
    Returns (summary_text, optional_key_takeaway).
    """
    if not summary_text:
        return ("", None)

    # Split into clean sentences
    raw_sents = [s for s in split_sentences(summary_text) if len(s) > 15]
    if not raw_sents:
        raw_sents = [summary_text.strip()]

    # Filter out boilerplate sentences
    clean_sents = []
    for s in raw_sents:
        # Skip sentences that look like author meta-commentary or disclaimers
        if any(skip in s for skip in ("در کانون توجه قرار گرفت", "برای اطلاعات بیشتر", "کلیک کنید", "کانال تلگرام ما")):
            continue
        clean_sents.append(s)

    if not clean_sents:
        clean_sents = raw_sents

    # Prioritize sentences that have numbers, percentages, or market drivers
    has_num_regex = re.compile(r"[\d۰-۹]|درصد|دلار|تومان|نرخ|واحد")
    key_sents = []
    other_sents = []

    for s in clean_sents:
        if has_num_regex.search(s):
            key_sents.append(s)
        else:
            other_sents.append(s)

    # Pick up to max_sents
    selected = (key_sents + other_sents)[:max_sents]
    if len(selected) < min_sents and len(clean_sents) >= min_sents:
        selected = clean_sents[:min_sents]

    # Check for optional key takeaway from remaining sentences if distinct
    key_takeaway = None
    remaining = [s for s in clean_sents if s not in selected]
    for r in remaining:
        # If it has a critical decision, projection, or quote
        if any(term in r for term in ("اعلام کرد", "پیش‌بینی", "انتظار می‌رود", "تصمیم گرفت", "هدف قیمتی")):
            key_takeaway = r
            break

    # Format summary paragraphs
    summary_body = " ".join(selected)
    return (summary_body, key_takeaway)


def format_editorial_post(
    article: Dict[str, Any],
    target: str = "telegram_html",
    include_link: bool = True,
    include_meta: bool = True
) -> str:
    """Render a financial news post adhering to all 17 editorial standards.
    
    target:
      - 'telegram_html': Uses <b> for bold, <a href="..."> for links
      - 'markdown' or 'bale': Uses **bold** and plain links
      - 'plain': No markup
    """
    emoji = detect_market_emoji(article)
    raw_title = str(article.get("title_fa") or article.get("title") or "خبر مالی").strip()
    title = clean_editorial_title(raw_title)

    raw_summary = str(article.get("summary_fa") or article.get("summary") or "").strip()
    summary, takeaway = format_editorial_summary(raw_summary)

    source = str(article.get("source_name") or article.get("source_key") or "رسانه‌های مالی").strip()
    url = str(article.get("link") or "").strip()

    # Time representation
    time_fa = str(article.get("time_fa") or article.get("datetime_fa") or "").strip()

    is_html = (target == "telegram_html")
    is_md = (target in ("markdown", "bale"))

    lines = []

    # Title line
    if is_html:
        lines.append(f"{emoji} <b>{title}</b>")
    elif is_md:
        lines.append(f"{emoji} **{title}**")
    else:
        lines.append(f"{emoji} {title}")

    lines.append("")

    # Summary body
    lines.append(summary)

    # Optional key takeaway
    if takeaway:
        lines.append("")
        if is_html:
            lines.append(f"📌 <b>نکته کلیدی:</b> {takeaway}")
        elif is_md:
            lines.append(f"📌 **نکته کلیدی:** {takeaway}")
        else:
            lines.append(f"📌 نکته کلیدی: {takeaway}")

    # Metadata & source line
    if include_meta or (include_link and url):
        lines.append("")
        meta_parts = []
        if source:
            meta_parts.append(f"📰 {source}")
        if time_fa:
            meta_parts.append(f"🕒 {time_fa}")

        if meta_parts:
            lines.append(" · ".join(meta_parts))

        if include_link and url:
            if is_html:
                lines.append(f'🔗 <a href="{url}">مشاهده متن کامل خبر</a>')
            elif is_md:
                lines.append(f"🔗 [مشاهده متن کامل خبر]({url})")
            else:
                lines.append(f"🔗 {url}")

    return "\n".join(lines).strip()
