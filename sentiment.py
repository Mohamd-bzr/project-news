"""Lightweight sentiment analysis for financial news.
No heavy ML dependencies — uses VADER + custom lexicons.

Usage:
    from sentiment import analyze_sentiment, analyze_batch, get_aggregate_sentiment
    result = analyze_sentiment("Bitcoin surges to new all-time high")
    # {'score': 0.85, 'label': 'positive', 'confidence': 0.92}
"""

import hashlib
import re
import threading
import time
from typing import Dict, List, Optional

# Try to import VADER
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    HAS_VADER = True
except ImportError:
    _vader = None
    HAS_VADER = False

# Custom financial lexicons (English)
_BULLISH_WORDS = {
    'surge', 'surges', 'surging', 'soar', 'soars', 'soaring', 'rally', 'rallies',
    'bull', 'bullish', 'pump', 'pumps', 'moon', 'mooning', 'breakout', 'breaks out',
    'all-time high', 'ath', 'record high', 'new high', 'buy', 'buying', 'accumulate',
    'adoption', 'partnership', 'approval', 'approved', 'etf approved', 'institutional',
    'upgrade', 'outperform', 'beat', 'beats', 'exceeds', 'growth', 'profit',
    'green', 'uptrend', 'recovery', 'rebound', 'bounce', 'support holds',
    'halving', 'scarcity', 'deflationary',
}

_BEARISH_WORDS = {
    'crash', 'crashes', 'crashing', 'plunge', 'plunges', 'plunging', 'dump', 'dumps',
    'bear', 'bearish', 'sell-off', 'selloff', 'liquidation', 'liquidated', 'rugpull',
    'hack', 'hacked', 'hacking', 'exploit', 'exploited', 'vulnerability',
    'ban', 'banned', 'banning', 'regulation', 'regulatory', 'lawsuit', 'sued',
    'fraud', 'scam', 'ponzi', 'collapse', 'collapses', 'decline', 'declines',
    'fear', 'panic', 'red', 'downtrend', 'correction', 'bubble', 'overvalued',
    'bankruptcy', 'insolvency', 'default', 'debt', 'recession', 'inflation',
}

# Custom financial lexicons (Persian/Farsi)
_PERSIAN_BULLISH = {
    'افزایش', 'رشد', 'صعود', 'جهش', 'پامپ', 'خرید', 'حمایت', 'مقاومت شکست',
    'بیشترین قیمت', 'رکورد', 'تأیید', 'مشارکت', 'همکاری', 'institutional',
    'کسب سود', 'بازگشت', 'ترند صعودی', 'سبز', 'خوشبینانه', 'چشمگیر', 'چشمگیری',
    'رشد چشمگیر', 'صعودی', 'پیشرفت',
}

_PERSIAN_BEARISH = {
    'سقوط', 'کاهش', 'نزول', 'ریزش', 'فروش', 'panic', 'ترس',
    'هک', 'کلاهبرداری', 'banned', 'ممنوعیت', 'شکایت', 'قانون',
    'ورشکستگی', 'بحران', 'تورم', 'رکود', 'حباب', 'بیشارزش',
    'قرمز', 'بدبینانه', 'لیکوئید', 'تراژدی', 'فاجعه', 'نزولی',
    'ضرر', 'ریسک',
}

# Emoji sentiment signals
_EMOJI_SENTIMENT = {
    '🚀': 0.8, '📈': 0.6, '🟢': 0.5, '💪': 0.4, '🔥': 0.3, '🐂': 0.6,
    '💰': 0.3, '✅': 0.4, '🎯': 0.3, '⬆️': 0.3,
    '📉': -0.6, '🔴': -0.5, '💀': -0.7, '⚠️': -0.3, '🐻': -0.6,
    '🏴': -0.4, '⛔': -0.5, '🚫': -0.4, '⬇️': -0.3,
    '😱': -0.5, '🆘': -0.6,
}

_sentiment_lock = threading.Lock()
_cache = {}  # text_hash -> (score, label, confidence, timestamp)
_CACHE_TTL = 3600  # 1 hour


def _text_hash(text: str) -> str:
    """Stable across processes.

    This was the built-in hash(), which is salted per interpreter (PYTHONHASHSEED)
    and only 64 bits wide, so the same headline got a different key after every
    restart and cache entries never matched across a restart.
    """
    return hashlib.sha1(text.lower().strip().encode("utf-8")).hexdigest()[:16]


def _clean_text(text: str) -> str:
    """Remove HTML, URLs, special chars."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return text.lower().strip()


def _vader_score(text: str) -> float:
    """Get VADER compound score: -1.0 (negative) to +1.0 (positive)."""
    if not HAS_VADER or not text:
        return 0.0
    scores = _vader.polarity_scores(text)
    return scores['compound']


def _lexicon_score(text: str, lang: str = 'en') -> float:
    """Score based on keyword matching. Returns -1.0 to +1.0."""
    words = set(text.lower().split())

    if lang == 'fa':
        bullish_set = _PERSIAN_BULLISH
        bearish_set = _PERSIAN_BEARISH
    else:
        bullish_set = _BULLISH_WORDS
        bearish_set = _BEARISH_WORDS

    bull_count = len(words & bullish_set)
    bear_count = len(words & bearish_set)

    # Also check phrases (multi-word)
    text_lower = text.lower()
    for phrase in bullish_set:
        if ' ' in phrase and phrase in text_lower:
            bull_count += 1
    for phrase in bearish_set:
        if ' ' in phrase and phrase in text_lower:
            bear_count += 1

    total = bull_count + bear_count
    if total == 0:
        return 0.0

    return (bull_count - bear_count) / total


def _emoji_score(text: str) -> float:
    """Score based on emoji sentiment."""
    total = 0.0
    count = 0
    for emoji, score in _EMOJI_SENTIMENT.items():
        occurrences = text.count(emoji)
        if occurrences:
            total += score * occurrences
            count += occurrences
    if count == 0:
        return 0.0
    return max(-1.0, min(1.0, total / count))


def _detect_language(text: str) -> str:
    """Simple language detection."""
    persian_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    total_chars = len(text.strip())
    if total_chars == 0:
        return 'en'
    return 'fa' if persian_chars / total_chars > 0.3 else 'en'


def analyze_sentiment(text: str, title: str = "") -> Dict:
    """Analyze sentiment of a single text.

    Args:
        text: Article content or summary
        title: Article title (optional, used for boosting)

    Returns:
        {'score': float, 'label': str, 'confidence': float}
        score: -1.0 (very bearish) to +1.0 (very bullish)
        label: 'positive', 'negative', or 'neutral'
        confidence: 0.0 to 1.0
    """
    if not text and not title:
        return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}

    # Check cache
    key = _text_hash((text or '') + (title or ''))
    with _sentiment_lock:
        if key in _cache:
            cached_score, cached_label, cached_conf, cached_ts = _cache[key]
            if time.time() - cached_ts < _CACHE_TTL:
                return {'score': cached_score, 'label': cached_label, 'confidence': cached_conf}

    combined_text = f"{title} {text}".strip()
    lang = _detect_language(combined_text)
    clean = _clean_text(combined_text)

    # Calculate component scores
    scores = []
    weights = []

    # VADER (English only, high weight)
    if lang == 'en' and HAS_VADER:
        v = _vader_score(clean)
        scores.append(v)
        weights.append(3.0)

    # Keyword lexicon (both languages, medium weight)
    lx = _lexicon_score(clean, lang)
    scores.append(lx)
    weights.append(2.0)

    # Emoji (low weight)
    em = _emoji_score(combined_text)
    if em != 0.0:
        scores.append(em)
        weights.append(1.0)

    # Title boost (if title is more extreme than body)
    if title:
        title_lx = _lexicon_score(_clean_text(title), lang)
        if abs(title_lx) > 0.3:
            scores.append(title_lx)
            weights.append(1.5)

    # Weighted average
    if not scores:
        final_score = 0.0
    else:
        final_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    final_score = max(-1.0, min(1.0, final_score))

    # Label
    if final_score > 0.15:
        label = 'positive'
    elif final_score < -0.15:
        label = 'negative'
    else:
        label = 'neutral'

    # Confidence (based on agreement between methods)
    if len(scores) >= 2:
        all_same_sign = all(s > 0 for s in scores) or all(s < 0 for s in scores)
        confidence = min(1.0, abs(final_score) * (1.2 if all_same_sign else 0.8))
    else:
        confidence = min(1.0, abs(final_score) * 0.7)

    final_score = round(final_score, 3)
    confidence = round(confidence, 3)

    # Cache result
    with _sentiment_lock:
        _cache[key] = (final_score, label, confidence, time.time())

    return {'score': final_score, 'label': label, 'confidence': confidence}


def analyze_batch(articles: List[Dict]) -> List[Dict]:
    """Add sentiment scores to a list of articles.

    Modifies articles in-place and returns the list.
    Each article gets: sentiment_score, sentiment_label, sentiment_confidence
    """
    for article in articles:
        title = article.get('title', '') or article.get('title_fa', '')
        text = article.get('summary', '') or article.get('summary_fa', '')
        result = analyze_sentiment(text, title)
        article['sentiment_score'] = result['score']
        article['sentiment_label'] = result['label']
        article['sentiment_confidence'] = result['confidence']
    return articles


def _normalize_sym(sym: str) -> set:
    s = (sym or "").strip().upper()
    synonyms = {s}
    if s in ('GOLD', 'XAU'):
        synonyms.update({'GOLD', 'XAU'})
    elif s in ('SILVER', 'XAG'):
        synonyms.update({'SILVER', 'XAG'})
    elif s.endswith('-USD'):
        synonyms.add(s[:-4])
    return synonyms


def get_aggregate_sentiment(articles: List[Dict], symbol: str = None) -> Dict:
    """Calculate aggregate sentiment for articles, optionally filtered by symbol.

    Returns:
        {
            'avg_score': float,
            'positive_count': int,
            'negative_count': int,
            'neutral_count': int,
            'total': int,
            'trend': 'bullish' | 'bearish' | 'mixed'
        }
    """
    if symbol:
        sym_set = _normalize_sym(symbol)
        filtered = []
        for a in articles:
            a_syms = set(a.get('symbols', []) or []) | set(a.get('assets', []) or [])
            if a.get('symbol'):
                a_syms.add(a['symbol'].upper())
            if any(s.upper() in sym_set for s in a_syms):
                filtered.append(a)
        articles = filtered

    scores = [a.get('sentiment_score', 0) for a in articles if 'sentiment_score' in a]

    if not scores:
        return {
            'avg_score': 0.0,
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'total': 0,
            'trend': 'mixed',
        }

    avg = sum(scores) / len(scores)
    pos = sum(1 for s in scores if s > 0.15)
    neg = sum(1 for s in scores if s < -0.15)
    neu = len(scores) - pos - neg

    if avg > 0.1:
        trend = 'bullish'
    elif avg < -0.1:
        trend = 'bearish'
    else:
        trend = 'mixed'

    return {
        'avg_score': round(avg, 3),
        'positive_count': pos,
        'negative_count': neg,
        'neutral_count': neu,
        'total': len(scores),
        'trend': trend,
    }
