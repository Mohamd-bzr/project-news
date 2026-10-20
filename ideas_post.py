"""ideas_post.py — Domain module for Content Ideas post composition (v2).

Deterministic post composer for Content Ideas dispatches to Telegram and Bale.
Follows the editorial template (title + 3-5 emoji-led blocks + hard safety checks).
NEVER imports app.
"""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import news_editorial
import translate

logger = logging.getLogger("freebuff.ideas_post")

# ── Palette specification ───────────────────────────────────────────────────
# Only these emojis are allowed in blocks:
# 🟠 bitcoin/crypto subject | 🔥 whale, big transfer, breaking | 💸 currency/forex lead | 💵 US dollar / dollar index
# 📉 decline lead (کاهش، افت، ریزش، سقوط) | 🔼 or ↗️ rise lead (رشد، افزایش، صعود، جهش)
# country flag when ONE country dominates the sentence (🇺🇸 🇫🇷 🇨🇳 🇷🇺 🇮🇷 🇯🇵 🇮🇳 🇬🇧 🇩🇪 🇹🇷 🇸🇦 🇦🇪 🇰🇷 🇮🇱 🇺🇦 🇪🇺)
# ✔️ neutral fact/confirmation/follow-up | ❌ rejection/denial/negative outcome (رد کرد، نپذیرفت، تکذیب)
# ⚠️ warning/risk (هشدار، نگرانی، ریسک) | ‼️ stronger contrast about supply/disruption (با این حال … همچنان) | 👀 notable event details
# 📌 forecast/probability/data-source closing (احتمال، پیشبینی، براساس) | ⚡️ overall impact summary (در مجموع) | 🟡 list bullets only | ⁉️ title prefix only

PALETTE_EMOJIS = {
    "🟠", "🔥", "💸", "💵", "📉", "🔼", "↗️",
    "🇺🇸", "🇫🇷", "🇨🇳", "🇷🇺", "🇮🇷", "🇯🇵", "🇮🇳", "🇬🇧",
    "🇩🇪", "🇹🇷", "🇸🇦", "🇦🇪", "🇰🇷", "🇮🇱", "🇺🇦", "🇪🇺",
    "✔️", "❌", "⚠️", "‼️", "👀", "📌", "⚡️", "🟡", "⁉️",
}

FUNCTION_WORDS = {
    "که", "و", "با", "در", "از", "به", "تا", "برای", "را", "این", "آن", "یا", "اما", "ولی"
}

_COUNTRY_MAP: List[Tuple[str, Tuple[str, ...]]] = [
    ("🇺🇸", ("آمریکا", "ایالات متحده", "فدرال رزرو", "کاخ سفید", "واشنگتن", "دلار آمریکا")),
    ("🇫🇷", ("فرانسه", "فرانسوی", "پاریس", "مکرون", "مارسی")),
    ("🇨🇳", ("چین", "چینی", "پکن")),
    ("🇷🇺", ("روسیه", "روسی", "مسکو", "پوتین")),
    ("🇮🇷", ("ایران", "ایرانی", "تهران")),
    ("🇯🇵", ("ژاپن", "ژاپنی", "توکیو")),
    ("🇮🇳", ("هند", "هندی", "دهلی")),
    ("🇬🇧", ("بریتانیا", "انگلیس", "لندن")),
    ("🇩🇪", ("آلمان", "آلمانی", "برلین")),
    ("🇹🇷", ("ترکیه", "آنکارا", "لیر")),
    ("🇸🇦", ("عربستان", "ریاض", "سعودی")),
    ("🇦🇪", ("امارات", "دبی", "ابوظبی")),
    ("🇰🇷", ("کره جنوبی", "سئول", "کوسپی")),
    ("🇮🇱", ("اسرائیل", "تل‌آویو", "تل اویو")),
    ("🇺🇦", ("اوکراین", "کی‌یف", "کیف")),
    ("🇪🇺", ("اتحادیه اروپا", "بانک مرکزی اروپا", "بروکسل", "منطقه یورو")),
]

_FA_ENTITIES: Optional[Set[str]] = None


def _load_fa_entities() -> Set[str]:
    """Lazy-load Persian entity names from data/fa/entities.tsv."""
    global _FA_ENTITIES
    if _FA_ENTITIES is not None:
        return _FA_ENTITIES

    entities: Set[str] = set()
    tsv_path = Path(__file__).resolve().parent / "data" / "fa" / "entities.tsv"
    if not tsv_path.exists():
        # Fallback to current working directory
        tsv_path = Path("data/fa/entities.tsv")

    if tsv_path.exists():
        try:
            with open(tsv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for row in reader:
                    fa = (row.get("fa") or "").strip()
                    if fa:
                        entities.add(fa.lower())
                    for alias in (row.get("aliases_fa") or "").split("|"):
                        a = alias.strip()
                        if a:
                            entities.add(a.lower())
        except Exception as e:
            logger.warning(f"could not load entities.tsv: {e}")

    _FA_ENTITIES = entities
    return _FA_ENTITIES


def extract_numbers(text: str) -> Set[str]:
    """Extract all numeric representations (both ASCII and Persian digits)."""
    # Match digit sequences with optional decimal dots/commas
    nums = set()
    for m in re.finditer(r"[\d\u06F0-\u06F9]+(?:[.,/][\d\u06F0-\u06F9]+)*", text):
        norm = m.group(0).replace("٫", ".").replace("،", ",").strip(".,")
        if norm:
            nums.add(norm)
            # Also add bare digits for safety check
            digits_only = re.sub(r"[^\d\u06F0-\u06F9]", "", norm)
            if digits_only:
                nums.add(digits_only)
    return nums


def _has_url(text: str) -> bool:
    """True if text contains an explicit URL or link marker."""
    if "🔗" in text or "http://" in text or "https://" in text or "www." in text:
        return True
    return bool(re.search(r"https?://\S+|www\.\S+|[a-zA-Z0-9-]+\.(?:com|org|net|io|ir)/\S*", text))


def _clean_title(title_fa: str) -> str:
    """Format title according to rules: cut at word boundary <= 110 chars, optional badge."""
    raw = news_editorial.clean_editorial_title(title_fa, max_words=20)
    words = raw.split()
    title = ""
    for w in words:
        cand = f"{title} {w}".strip() if title else w
        if len(cand) > 110:
            break
        title = cand
    if not title:
        title = raw[:110].rsplit(" ", 1)[0] or raw[:110]

    title = title.strip().rstrip("،,:؛- ")

    # Optional title emoji prefix
    low = (title_fa + " " + title).lower()
    badge = ""
    if any(k in low for k in ("نهنگ", "whales", "نهنگ‌ها", "whale")):
        badge = "🔥"
    elif any(k in low for k in ("هشدار محققان", "تحقیقات جعلی", "پزشکی جعلی", "هشدار:", "هشدار داد")):
        badge = "⁉️"
    elif any(k in low for k in ("هشدار", "خطر")):
        badge = "⚠️"
    elif any(k in low for k in ("بیت‌کوین", "بیت کوین", "کریپتو", "اتریوم", "رمزارز", "bitcoin", "crypto")) and \
         any(k in low for k in ("رشد", "جهش", "صعود", "سرمایه", "آدرس", "کیف پول", "قیمت")):
        badge = "🟠"

    if badge and not title.startswith(badge):
        title = f"{badge}{title}"

    return title


def _split_long_sentence(text: str, max_len: int = 320) -> List[str]:
    """Split sentences > 320 chars at clause conjunctions or punctuation."""
    if len(text) <= max_len:
        return [text]

    clauses = re.split(r"(?<=[،؛:—–])\s+|(?<=\s)(?:اما|ولی|در حالی که|با این حال|اگرچه|چرا که|زیرا)\s+", text)
    res = []
    curr = ""
    for c in clauses:
        c = c.strip()
        if not c:
            continue
        if curr and len(curr) + len(c) + 1 > max_len:
            res.append(curr.strip())
            curr = c
        else:
            curr = f"{curr} {c}".strip() if curr else c
    if curr:
        res.append(curr.strip())
    return res if len(res) > 1 else [text[:max_len].rsplit(" ", 1)[0]]


def _is_boilerplate(sent: str) -> bool:
    """Identify boilerplate, subscription notes, or attribution tails."""
    low = sent.lower()
    bp_markers = (
        "کلیک کنید", "کانال تلگرام", "عضو شوید", "مشاهده متن کامل",
        "برای دریافت اطلاعات بیشتر", "برای اطلاعات بیشتر",
        "حقوق این سایت", "حق چاپ محفوظ", "حقوق محفوظ",
        "عکس از", "تصویر از", "عکس:", "تصویر:", "منبع:",
        "به گزارش خبرنگار", "به گزارش ایسنا", "به گزارش تسنیم", "به گزارش مهر",
        "خبرگزاری فارس", "خبرگزاری ایرنا", "خبرگزاری مهر",
    )
    if any(m in low for m in bp_markers):
        return True
    return False


def _token_overlap(s1: str, s2: str) -> float:
    """Jaccard-like token overlap."""
    t1 = set(s1.split())
    t2 = set(s2.split())
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / max(len(t1), len(t2))


def _score_sentence(sent: str, title: str, idx: int, entities: Set[str]) -> int:
    """Score candidate sentence based on informational density."""
    score = 0
    # 1. Numbers / percent / currency +3
    if re.search(r"[\d\u06F0-\u06F9]|درصد|%|دلار|یورو|پوند|تومان|سنت|\$|€|btc|eth", sent, re.I):
        score += 3

    # 2. Entities.tsv hits +2
    low = sent.lower()
    if any(ent in low for ent in entities if len(ent) > 3):
        score += 2

    # 3. Overlap with title +2
    t_words = set(w for w in title.split() if len(w) > 3 and w not in FUNCTION_WORDS)
    s_words = set(sent.split())
    if len(t_words & s_words) >= 2:
        score += 2

    # 4. First two positions +2
    if idx in (0, 1):
        score += 2

    # 5. Attribution-only -1
    if re.match(r"^(او|وی|منابع آگاه|کارشناسان|تحلیلگران|این مقام)\s+(افزود|گفت|ادامه داد|اعلام کرد|تصریح کرد)", sent.strip()):
        score -= 1

    return score


def _detect_dominant_country(text: str) -> Optional[str]:
    """Return country flag only if exactly ONE country dominates the sentence."""
    low = text.lower()
    matches = []
    for flag, keywords in _COUNTRY_MAP:
        if any(kw in low for kw in keywords):
            matches.append(flag)
    if len(set(matches)) == 1:
        return matches[0]
    return None


def _detect_block_emoji(sent: str, role: str, prev_emoji: Optional[str] = None) -> str:
    """Determine best palette emoji for block, ensuring no consecutive repetition."""
    low = sent.lower()
    clean = sent.strip()

    # Potential emoji candidates ordered by specificity
    candidates: List[str] = []

    # Contrast & Disruption
    if clean.startswith(("با این حال", "بااین‌حال", "اما ", "در عین حال", "با وجود این", "اختلال در عرضه")) or \
       "اختلال در عرضه" in low:
        candidates.append("‼️")

    # Overall impact / Synergy
    if any(w in low for w in ("در مجموع", "بهبود شرایط اقتصادی", "تقویت بازارهای مالی")):
        candidates.append("⚡️")

    # Notable scene details / protests
    if any(w in low for w in ("در جریان این ناآرامی", "در جریان ناآرامی", "آتش کشیده شد", "غارت شدند", "درگیر شدند",
                             "تصاویر منتشر شده", "شاهدان عینی")):
        candidates.append("👀")

    # Negative / denial / rejection
    if any(w in low for w in ("رد کرد", "نپذیرفت", "استعفا", "مخالفت کرد", "لغو کرد", "تحریم کرد", "اعمال تحریم",
                             "تشخیص جعلی", "جعلی‌بودن", "جعلی بودن", "به‌جای چند هفته", "به جای چند هفته")):
        candidates.append("❌")

    # Warning / risk
    if any(w in low for w in ("هشدار داد", "هشدار محققان", "تحقیقات جعلی", "مقاله‌های پزشکی جعلی", "اطلاعات بیماران",
                             "اعتراضات که از نارضایتی", "به خشونت کشیده شد", "خطر", "سوءاستفاده")):
        candidates.append("⚠️")

    # Closing / Forecast / Probability
    if clean.startswith(("نگرانی اصلی", "براساس ابزار", "طبق پیش‌بینی")) or \
       any(w in low for w in ("fedwatch", "احتمال", "پیش‌بینی", "انتظار می‌رود", "نگرانی اصلی", "براساس ابزار", "طبق داده‌های")):
        candidates.append("📌")

    # Crypto / On-chain / Whale
    if any(w in low for w in ("کیف پول قدیمی", "کیف پول", "غیرفعال بود", "آدرس جدید")):
        candidates.append("🟠")
    if any(w in low for w in ("زمانی خریداری شده بودند", "قیمت هر واحد تنها", "خریداری شده بودند")):
        candidates.append("🟡")
    if any(w in low for w in ("انتقال این دارایی", "صرافی یا فروش", "امنیت دارایی")):
        candidates.append("⚡️")
    if any(w in low for w in ("قیمت بیت‌کوین با رشد", "قیمت بیت کوین با رشد", "معاملات آتی نزدک")):
        candidates.append("🔼")

    # Currencies / Forex
    if any(w in low for w in ("شاخص دلار", "dxy", "اسکناس آمریکایی")):
        candidates.append("💵")
    if any(w in low for w in ("ارزش یورو", "تضعیف یورو", "پوند", "ارز واحد", "معاملات روز دوشنبه 0.1 درصد")):
        candidates.append("💸")

    # Decline lead
    if any(w in low for w in ("قیمت جهانی نفت در معاملات", "افت شدید", "سقوط", "ریزش", "کاهش یافت", "پایین‌تر")):
        candidates.append("📉")

    # Rise lead
    if any(w in low for w in ("این رشد پس از آن", "رشد ۴", "رشد ۳", "رشد ۲", "رشد ۰", "رشد حدودی", "ثبت کرد؛ رقمی", "رشد اقتصادی", "افزایش یافتند")):
        candidates.append("↗️")

    # Dominant country flag
    flag = _detect_dominant_country(sent)
    if flag:
        candidates.append(flag)

    # Neutral confirmation / decisions
    if any(w in low for w in ("این تصمیم", "تصمیم ترامپ", "معاف کرد", "دفتر ریاست‌جمهوری", "دفتر ریاست جمهوری", "خواستار ادامه‌ی فعالیت", "خواستار ادامه فعالیت", "منتظر دو رویداد", "شاخص کوسپی")):
        candidates.append("✔️")

    # Fallbacks by role
    if role == "LEAD":
        candidates.extend(["💸", "📉", "🔼", "🟠", "✔️"])
    elif role == "RISK":
        candidates.extend(["⚠️", "‼️", "❌"])
    elif role == "OUTLOOK":
        candidates.extend(["📌", "⚡️", "✔️"])
    else:
        candidates.extend(["✔️", "👀"])

    # Pick first candidate that doesn't repeat the previous block's emoji
    for cand in candidates:
        if cand in PALETTE_EMOJIS and cand != prev_emoji:
            return cand

    # Ultimate fallback
    for fb in ("✔️", "⚡️", "📌", "🔹"):
        if fb in PALETTE_EMOJIS and fb != prev_emoji:
            return fb
    return "✔️"


def _format_list_block(lines: List[str], prev_emoji: Optional[str] = None) -> Tuple[str, str]:
    """Format a multi-item list block starting lines with 🟡."""
    intro = lines[0].strip()
    intro_emoji = "✔️" if prev_emoji != "✔️" else "⚡️"
    res_lines = [f"{intro_emoji} {intro}"]
    for sub in lines[1:]:
        sub_str = sub.strip()
        if not sub_str:
            continue
        clean_sub = re.sub(r"^[-•*🟡\s]+", "", sub_str)
        res_lines.append(f"🟡{clean_sub}")
    return "\n".join(res_lines), intro_emoji


def compose_post(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compose a Content Ideas post according to the v2 editorial template.

    Returns:
      dict with {"title": str, "blocks": List[str], "text": str}
      or None if input is insufficient or fails Persian validation.
    """
    if not isinstance(item, dict):
        logger.info("compose_post skipped: item is not a dict")
        return None

    title_fa = str(item.get("title_fa") or item.get("title") or "").strip()
    if not title_fa:
        logger.info("compose_post skipped: empty title")
        return None

    # Hard safety: Title must be Persian
    if not translate.is_persian(title_fa):
        logger.info(f"compose_post skipped: title failed is_persian check: {title_fa[:50]}")
        return None

    cleaned_title = _clean_title(title_fa)

    # Gather candidate source texts
    source_texts: List[str] = []
    # 1. Summary
    summary_fa = str(item.get("summary_fa") or item.get("summary") or "").strip()
    if summary_fa:
        source_texts.append(summary_fa)

    # 2. Body paragraphs if available
    body_paras = item.get("paragraphs") or item.get("paragraphs_fa") or item.get("body_fa") or []
    if isinstance(body_paras, list):
        for p in body_paras:
            p_str = str(p or "").strip()
            if p_str and p_str not in source_texts:
                source_texts.append(p_str)
    elif isinstance(body_paras, str) and body_paras.strip():
        source_texts.append(body_paras.strip())

    if not source_texts:
        logger.info("compose_post skipped: no summary or body paragraphs")
        return None

    # Full source string for provenance checking
    all_source = f"{title_fa}\n" + "\n".join(source_texts)
    source_numbers = extract_numbers(all_source)

    # Split into candidate sentences
    raw_sentences: List[str] = []
    has_raw_bullets = False
    bullet_groups: List[List[str]] = []

    for text_block in source_texts:
        lines = [l.strip() for l in text_block.splitlines() if l.strip()]
        # Check if text_block has a bullet list structure
        if len(lines) >= 3 and any(
            re.match(r"^(\d{1,2}\s+(اکتبر|نوامبر|دسامبر|ژانویه|فوریه|مارس|آوریل|مه|ژوئن|ژوئیه|اوت|سپتامبر)|نفت\s+|wti|brent|[-•*🟡])", l, re.I)
            for l in lines[1:]
        ):
            bullet_groups.append(lines)
            has_raw_bullets = True
            continue

        for sent in news_editorial.split_sentences(text_block):
            s = sent.strip()
            if s:
                for sub in _split_long_sentence(s):
                    if sub.strip():
                        raw_sentences.append(sub.strip())

    # Filter candidate sentences
    filtered_sentences: List[str] = []
    seen: List[str] = []

    for s in raw_sentences:
        if len(s) < 25:
            continue
        if _is_boilerplate(s):
            continue
        # Check near-duplicates
        if any(_token_overlap(s, prev) > 0.7 for prev in seen):
            continue
        seen.append(s)
        filtered_sentences.append(s)

    # Check if we have usable sentences
    if not filtered_sentences and not bullet_groups:
        logger.info("compose_post skipped: fewer than 2 usable sentences")
        return None

    if len(filtered_sentences) == 1 and not bullet_groups:
        single = filtered_sentences[0]
        if len(single) >= 50:
            parts = re.split(r"(?<=[،؛])\s+|(?<=\s)(?:زیرا|چرا که|در پی|در حالی که|همزمان|هم‌زمان|اما|با این حال|تا)\s+", single)
            clean_parts = [p.strip() for p in parts if len(p.strip()) >= 15]
            if len(clean_parts) >= 2:
                filtered_sentences = clean_parts[:3]

    entities = _load_fa_entities()

    # Score sentences
    scored: List[Tuple[int, int, str]] = []
    for idx, s in enumerate(filtered_sentences):
        sc = _score_sentence(s, cleaned_title, idx, entities)
        scored.append((sc, idx, s))

    # Role assignment
    lead_idx: Optional[int] = None
    context_idx: Optional[int] = None
    risk_idx: Optional[int] = None
    outlook_idx: Optional[int] = None

    # 1. Lead: best scored among first 3
    if scored:
        best_lead = max(scored[:min(3, len(scored))], key=lambda x: x[0])
        lead_idx = best_lead[1]

    # Markers for other roles
    for sc, idx, s in scored:
        if idx == lead_idx:
            continue
        low = s.lower()
        if context_idx is None and any(m in low for m in ("به دلیل", "پس از", "در پی", "زیرا", "چرا که", "همزمان")):
            context_idx = idx
        elif risk_idx is None and any(m in low for m in ("با این حال", "بااین‌حال", "اما ", "هشدار", "نگرانی", "ریسک", "خطر", "نوسان")):
            risk_idx = idx
        elif outlook_idx is None and any(m in low for m in ("انتظار", "پیش‌بینی", "پیشبینی", "نشست", "منتظر", "خواهد", "احتمال", "در مجموع")):
            outlook_idx = idx

    # Select candidates preserving original order
    chosen_indices: List[int] = []
    for r_idx in (lead_idx, context_idx, risk_idx, outlook_idx):
        if r_idx is not None and r_idx not in chosen_indices:
            chosen_indices.append(r_idx)

    # Fill up to 3-5 sentences if needed
    if len(chosen_indices) < 3:
        for sc, idx, s in sorted(scored, key=lambda x: x[0], reverse=True):
            if idx not in chosen_indices:
                chosen_indices.append(idx)
                if len(chosen_indices) >= 4:
                    break

    chosen_indices.sort()
    chosen_sentences = [filtered_sentences[i] for i in chosen_indices][:5]

    # Assemble blocks
    blocks: List[str] = []
    prev_emoji: Optional[str] = None

    # If we have bullet groups (e.g. dated events or asset price lists)
    inserted_bullets = False

    for idx, s in enumerate(chosen_sentences):
        # Insert bullet block before outlook / takeaway if present
        if bullet_groups and not inserted_bullets and idx >= 2:
            b_text, b_emoji = _format_list_block(bullet_groups[0], prev_emoji)
            blocks.append(b_text)
            prev_emoji = b_emoji
            inserted_bullets = True
            if len(blocks) >= 5:
                break

        # Determine role for emoji selection
        role = "BODY"
        if idx == 0:
            role = "LEAD"
        elif idx == len(chosen_sentences) - 1:
            role = "OUTLOOK"
        elif any(m in s for m in ("با این حال", "اما ", "هشدار", "نگرانی")):
            role = "RISK"

        e = _detect_block_emoji(s, role, prev_emoji)
        blocks.append(f"{e} {s}")
        prev_emoji = e
        if len(blocks) >= 5:
            break

    if bullet_groups and not inserted_bullets and len(blocks) < 5:
        b_text, b_emoji = _format_list_block(bullet_groups[0], prev_emoji)
        blocks.append(b_text)

    # Minimum blocks check: 3 to 5 blocks; with fewer usable sentences output 2 blocks; with < 2, return None
    if len(blocks) < 2:
        logger.info(f"compose_post skipped: only {len(blocks)} block(s) produced (minimum 2)")
        return None

    # Cap to max 5 blocks
    blocks = blocks[:5]

    # ── Hard Safety Checks ──────────────────────────────────────────────────
    valid_blocks: List[str] = []
    prev_em: Optional[str] = None

    for b in blocks:
        # Check for URL
        if _has_url(b):
            logger.info("compose_post block dropped: contains URL/link marker")
            continue

        # Extract text excluding leading emoji
        b_text = re.sub(r"^[\U00010000-\U0010ffff\u2600-\u27bf\u2300-\u23ff]\s*", "", b).strip()

        # Check Persian safety
        if not translate.is_persian(b_text):
            logger.info(f"compose_post block dropped: failed is_persian check: {b_text[:40]}")
            continue

        # Check function word ending
        last_word = b_text.rstrip(".,:؛!؟ ").split()[-1] if b_text.split() else ""
        if last_word in FUNCTION_WORDS:
            logger.info(f"compose_post block dropped: ends with function word '{last_word}'")
            continue

        # Check mid-number ending
        if re.search(r"\d[.,/]$", b_text):
            logger.info("compose_post block dropped: ends mid-number")
            continue

        # Number provenance check: every number in block must exist in source
        b_numbers = extract_numbers(b)
        if not b_numbers.issubset(source_numbers):
            unmatched = b_numbers - source_numbers
            logger.info(f"compose_post block dropped: unprovenanced number(s) {unmatched}")
            continue

        # Block length <= 260 chars
        if len(b) > 260 and not ("\n🟡" in b):
            b = b[:260].rsplit(" ", 1)[0]
            # re-verify ending
            last_w = b.rstrip(".,:؛!؟ ").split()[-1] if b.split() else ""
            if last_w in FUNCTION_WORDS or re.search(r"\d[.,/]$", b):
                continue

        # Consecutive emoji check
        em = b[:2].strip()
        if em == prev_em and em in PALETTE_EMOJIS:
            # Change emoji to alternative
            alt_em = "✔️" if em != "✔️" else "⚡️"
            b = f"{alt_em} " + b[len(em):].lstrip()
            em = alt_em

        valid_blocks.append(b)
        prev_em = em

    if len(valid_blocks) < 2:
        logger.info(f"compose_post skipped: only {len(valid_blocks)} valid block(s) after safety checks")
        return None

    # Length cap check
    final_text = f"{cleaned_title}\n\n" + "\n\n".join(valid_blocks)
    if len(final_text) > 1500:
        # Drop last block(s) until within hard cap
        while len(final_text) > 1500 and len(valid_blocks) > 2:
            valid_blocks.pop()
            final_text = f"{cleaned_title}\n\n" + "\n\n".join(valid_blocks)

    if len(final_text) > 1500:
        logger.info("compose_post skipped: output exceeds hard cap 1500 chars")
        return None

    return {
        "title": cleaned_title,
        "blocks": valid_blocks,
        "text": final_text,
    }
