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

    # 2. Central banks / Interest rates
    if any(w in text for w in ("بانک مرکزی", "فدرال رزرو", "پاول", "لاگارد", "نرخ بهره", "fomc", "central bank", "ecb", "سیاست پولی")):
        return "🏦"

    # 3. Macro / Economic data releases
    if any(w in text for w in ("cpi", "nfp", "gdp", "pmi", "تورم", "تولید ناخالص", "اشتغال", "بیکاری", "خرده‌فروشی", "خرده فروشی", "شاخص قیمت")):
        return "📊"

    # 4. Gold & Precious metals
    if "XAU" in assets or any(w in text for w in ("طلا", "اونس", "انس جهانی", "gold", "xau")):
        return "🟡"
    if "XAG" in assets or any(w in text for w in ("نقره", "silver", "xag")):
        return "⚪"

    # 5. Crypto
    if any(a in assets for a in ("BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE")) or any(w in text for w in ("بیت‌کوین", "بیت کوین", "کریپتو", "اتریوم", "رمزارز", "ارز دیجیتال", "bitcoin", "crypto")):
        return "₿"

    # 6. Oil & Energy
    if any(a in assets for a in ("WTI", "BRENT")) or any(w in text for w in ("نفت", "اوپک", "برنت", "نفت خام", "بنزین", "oil", "crude", "brent", "opec")):
        return "🛢️"

    # 7. Fiat Currencies
    if "DXY" in assets or any(w in text for w in ("شاخص دلار", "اسکناس آمریکایی", "dxy", "قیمت دلار", "نرخ دلار", "دلار آمریکا")):
        return "💵"
    if any(w in text for w in ("یورو", "eur", "euro")):
        return "💶"
    if "دلار" in title or "dollar" in title:
        return "💵"

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


def format_editorial_summary(summary_text: str, min_sents: int = 2, max_sents: int = 4) -> Tuple[str, Optional[str]]:
    """Organize summary text into 2-4 key sentences, retaining numbers and drivers.
    Returns (summary_text, optional_key_takeaway).
    """
    if not summary_text:
        return ("", None)

    # Split into clean sentences
    raw_sents = [s.strip() for s in re.split(r"(?<=[.!?؟\n])\s+", summary_text) if len(s.strip()) > 15]
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
