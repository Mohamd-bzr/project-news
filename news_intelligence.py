"""News intelligence: dedup, correlation, anomaly detection.

No heavy ML dependencies. Uses TF-IDF + cosine similarity for dedup.
Uses simple statistical methods for correlation and anomaly detection.
"""

import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

_lock = threading.Lock()
logger = logging.getLogger("news_intelligence")

# ============================================================
# DEDUPLICATION
# ============================================================

_STOP_WORDS = {
    'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'has', 'had',
    'are', 'was', 'were', 'will', 'would', 'could', 'should', 'been', 'being',
    'about', 'after', 'into', 'over', 'more', 'most', 'other', 'some', 'such',
    'than', 'them', 'then', 'these', 'they', 'what', 'when', 'where', 'which',
    'who', 'why', 'how', 'all', 'any', 'both', 'each', 'few',
    'past', 'mark', 'reaches', 'hits', 'breaks', 'barrier', 'tops', 'passes',
    'new', 'time',
}

def _tokenize(text: str) -> List[str]:
    """Smart word tokenization for financial news dedup."""
    text = (text or "").lower()
    text = re.sub(r'\$?(\d+),?000\b', r'\1k', text)
    text = re.sub(r'\bath\b', 'high', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    return [w for w in text.split() if len(w) > 2 and w not in _STOP_WORDS]


def _cosine_similarity(vec1: Dict[str, int], vec2: Dict[str, int]) -> float:
    """Compute cosine similarity between two term-frequency vectors."""
    keys = set(vec1.keys()) & set(vec2.keys())
    if not keys:
        return 0.0

    dot = sum(vec1[k] * vec2[k] for k in keys)
    mag1 = math.sqrt(sum(v**2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v**2 for v in vec2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def _compute_tf(tokens: List[str]) -> Dict[str, int]:
    """Compute term frequency vector."""
    tf = {}
    for token in tokens:
        tf[token] = tf.get(token, 0) + 1
    return tf


class Deduplicator:
    """Embedding-free deduplication using TF-IDF-like similarity."""

    def __init__(self, similarity_threshold: float = 0.65, ttl_hours: int = 48):
        self.threshold = similarity_threshold
        self.ttl_seconds = ttl_hours * 3600
        self._articles = []  # (timestamp, tf_vector, article_id)
        self._lock = threading.Lock()
        self._last_purge = 0.0

    def is_duplicate(self, article: Dict) -> Tuple[bool, Optional[str]]:
        """Check if article is a duplicate of any recent article.

        Returns:
            (is_dup, duplicate_of_id) — duplicate_of_id is None if not dup
        """
        title = article.get('title', '') or ''
        summary = article.get('summary', '') or ''
        combined = f"{title} {summary}".strip()

        if not combined:
            return False, None

        tokens = _tokenize(combined)
        tf = _compute_tf(tokens)
        now = time.time()
        # A stable id: the built-in hash() is salted per process, so the same
        # text used to get a different fallback id after every restart.
        article_id = article.get('id') or hashlib.sha1(combined.encode('utf-8')).hexdigest()[:16]

        with self._lock:
            # Purge expired entries. Throttled: dedup_batch calls this once per
            # article, and rebuilding the whole list each time made the batch
            # O(n²) on lists of a thousand-odd articles.
            if now - self._last_purge > 60.0:
                self._articles = [
                    (ts, vec, aid) for ts, vec, aid in self._articles
                    if now - ts < self.ttl_seconds
                ]
                self._last_purge = now

            # Check against the other articles already seen. Comparing an
            # article with its own stored vector always scores 1.0 — the
            # similarity of a text with itself is above any threshold — which
            # made every headline from the previous cycle its own duplicate.
            for ts, existing_tf, existing_id in self._articles:
                if existing_id == article_id:
                    continue
                sim = _cosine_similarity(tf, existing_tf)
                if sim >= self.threshold:
                    return True, existing_id

            # Remember it, refreshing the timestamp instead of storing the same
            # id twice (a carried-forward headline is re-checked every cycle).
            self._articles = [(ts, vec, aid) for ts, vec, aid in self._articles
                              if aid != article_id]
            self._articles.append((now, tf, article_id))
            return False, None

    def dedup_batch(self, articles: List[Dict]) -> Tuple[List[Dict], int]:
        """Remove duplicates from a batch. Returns (unique_articles, dup_count)."""
        unique = []
        dup_count = 0
        for article in articles:
            is_dup, _ = self.is_duplicate(article)
            if not is_dup:
                unique.append(article)
            else:
                dup_count += 1
        return unique, dup_count


# Global deduplicator
_dedup = Deduplicator()


# ============================================================
# NEWS-TO-PRICE CORRELATION
# ============================================================

class CorrelationTracker:
    """Track how asset prices move after news events.

    Stores news events with timestamps and later correlates with
    price movements at 1h, 4h, 24h after the event.
    """

    DB_PATH = Path(__file__).parent / "correlation.json"
    # Newest MAX_EVENTS are kept on disk. record_event trims the in-memory
    # list once it passes 2x this, so a full file is always available to save.
    MAX_EVENTS = 5000
    # Minimum seconds between disk writes. Bounds the write rate no matter how
    # many events a cycle produces.
    FLUSH_SECONDS = 60.0
    # A given (article, asset) pair is one event, however often the price
    # poller runs. The price refresh fires every 12 s and used to re-record the
    # same headline for every asset it mentions, dozens of times an hour.
    EVENT_TTL_SECONDS = 24 * 3600

    def __init__(self):
        self._events = []  # list of {ts, symbol, sentiment, price_at_event, price_1h, ...}
        self._lock = threading.Lock()
        self._dirty = False
        self._last_save = 0.0
        self._seen = {}    # (symbol, article_id) -> first seen ts
        self._load()

    def _load(self):
        try:
            if self.DB_PATH.exists():
                with open(self.DB_PATH, 'r', encoding='utf-8') as f:
                    self._events = json.load(f)
                if not isinstance(self._events, list):
                    raise ValueError("correlation.json is not a list")
        except Exception as e:
            logger.warning("correlation.json unreadable (%s); starting empty", e)
            self._events = []
        # a .tmp left behind by a killed process is always a partial write
        try:
            stale = self.DB_PATH.with_suffix(".json.tmp")
            if stale.exists():
                stale.unlink()
                logger.warning("removed stale partial write %s", stale)
        except OSError as e:
            logger.warning("could not clear stale tmp: %s", e)

    def _save(self, force: bool = False) -> bool:
        """Persist the newest MAX_EVENTS events to disk, atomically.

        Called from record_event/update_prices thousands of times per cycle, so
        it debounces: a write only happens if something changed AND the last
        write is older than FLUSH_SECONDS. Writing the whole list on every
        event made the cycle O(n^2) in disk I/O (~23s of a 140s cycle measured).

        Writes go to a .tmp sibling and are moved into place with os.replace,
        so a kill mid-write can no longer leave a truncated/empty file.
        """
        if not self._dirty and not force:
            return True
        now = time.time()
        if not force and (now - self._last_save) < self.FLUSH_SECONDS:
            return True
        tmp = self.DB_PATH.with_suffix(".json.tmp")
        try:
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(self._events[-self.MAX_EVENTS:], f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.DB_PATH)
            self._dirty = False
            self._last_save = now
            return True
        except Exception as e:
            logger.error("correlation save failed: %s", e)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    def save(self) -> bool:
        """Force a write. Call once at the end of a scrape cycle."""
        with self._lock:
            return self._save(force=True)

    def record_event(self, symbol: str, sentiment_score: float, price: float,
                     article_id: Optional[str] = None):
        """Record a news event for future correlation.

        Idempotent per (article, asset): the caller runs on every price push, so
        without this the store filled with the same handful of headlines and the
        1h/4h/24h statistics described nothing but the last few minutes.
        """
        key = (str(symbol).upper(), str(article_id)) if article_id else None
        with self._lock:
            if key is not None:
                seen_at = self._seen.get(key)
                if seen_at is not None and time.time() - seen_at < self.EVENT_TTL_SECONDS:
                    return
                # drop the dead keys while we are here, so the set cannot grow
                if len(self._seen) > self.MAX_EVENTS:
                    cutoff = time.time() - self.EVENT_TTL_SECONDS
                    self._seen = {k: ts for k, ts in self._seen.items() if ts >= cutoff}
                self._seen[key] = time.time()
            self._events.append({
                'ts': time.time(),
                'symbol': symbol,
                'article_id': article_id,
                'sentiment': sentiment_score,
                'price': price,
                'price_1h': None,
                'price_4h': None,
                'price_24h': None,
            })
            if len(self._events) > self.MAX_EVENTS * 2:
                self._events = self._events[-self.MAX_EVENTS:]
            self._dirty = True
            self._save()

    def update_prices(self, symbol: str, current_price: float):
        """Update price checkpoints for recent events."""
        now = time.time()
        with self._lock:
            for event in self._events:
                if event['symbol'] != symbol:
                    continue
                age_hours = (now - event['ts']) / 3600

                if event['price_1h'] is None and age_hours >= 1:
                    event['price_1h'] = current_price
                if event['price_4h'] is None and age_hours >= 4:
                    event['price_4h'] = current_price
                if event['price_24h'] is None and age_hours >= 24:
                    event['price_24h'] = current_price
            self._dirty = True
            self._save()

    def get_correlation(self, symbol: str) -> Dict:
        """Compute correlation stats for a symbol.

        Returns:
            {
                'positive_news_avg_move': {'1h': %, '4h': %, '24h': %},
                'negative_news_avg_move': {'1h': %, '4h': %, '24h': %},
                'total_events': int,
                'accuracy': float  # % of time sentiment matched price direction
            }
        """
        with self._lock:
            events = [e for e in self._events if e['symbol'] == symbol]

        if len(events) < 5:
            return {'total_events': len(events), 'insufficient_data': True}

        positive = [e for e in events if e.get('sentiment', 0) > 0.15]
        negative = [e for e in events if e.get('sentiment', 0) < -0.15]

        def avg_move(events_list, key):
            moves = []
            for e in events_list:
                if e.get(key) is not None and e.get('price', 0) > 0:
                    move_pct = ((e[key] - e['price']) / e['price']) * 100
                    moves.append(move_pct)
            return round(sum(moves) / len(moves), 2) if moves else None

        pos_moves = {
            '1h': avg_move(positive, 'price_1h'),
            '4h': avg_move(positive, 'price_4h'),
            '24h': avg_move(positive, 'price_24h'),
        }
        neg_moves = {
            '1h': avg_move(negative, 'price_1h'),
            '4h': avg_move(negative, 'price_4h'),
            '24h': avg_move(negative, 'price_24h'),
        }

        # Calculate accuracy (% of time sentiment matched price direction)
        correct = 0
        total = 0
        for e in events:
            if e.get('price_1h') is not None and e.get('price', 0) > 0:
                actual_move = e['price_1h'] - e['price']
                sent = e.get('sentiment', 0)
                if (sent > 0 and actual_move > 0) or (sent < 0 and actual_move < 0):
                    correct += 1
                total += 1

        accuracy = round(correct / total * 100, 1) if total > 0 else 0

        return {
            'positive_news_avg_move': pos_moves,
            'negative_news_avg_move': neg_moves,
            'total_events': len(events),
            'positive_events': len(positive),
            'negative_events': len(negative),
            'accuracy': accuracy,
        }


_correlation = CorrelationTracker()


# ============================================================
# VOLUME ANOMALY DETECTION
# ============================================================

class AnomalyDetector:
    """Detect unusual news volume for assets.

    If an asset gets 3x its normal article count in a cycle, flag it.
    """

    def __init__(self):
        self._history = defaultdict(list)  # symbol -> [count_per_cycle]
        self._lock = threading.Lock()

    def record_cycle(self, articles: List[Dict]):
        """Record article counts per asset for this cycle."""
        counts = defaultdict(int)
        for article in articles:
            symbols = list(set(article.get('symbols', []) or []) | set(article.get('assets', []) or []))
            if article.get('symbol'):
                symbols.append(article['symbol'])
            for sym in symbols:
                counts[sym.upper()] += 1

        with self._lock:
            for sym, count in counts.items():
                self._history[sym].append(count)
                # Keep last 100 cycles
                if len(self._history[sym]) > 100:
                    self._history[sym] = self._history[sym][-100:]

    def detect_anomalies(self) -> List[Dict]:
        """Detect current cycle anomalies.

        Returns list of:
            {'symbol': str, 'current_count': int, 'avg_count': float, 'ratio': float}
        """
        anomalies = []
        with self._lock:
            for sym, counts in self._history.items():
                if len(counts) < 5:
                    continue
                current = counts[-1]
                avg = sum(counts[:-1]) / max(len(counts) - 1, 1)
                if avg > 0 and current / avg >= 3.0:
                    anomalies.append({
                        'symbol': sym,
                        'current_count': current,
                        'avg_count': round(avg, 1),
                        'ratio': round(current / avg, 1),
                    })
        return sorted(anomalies, key=lambda x: x['ratio'], reverse=True)


_anomaly = AnomalyDetector()


# ============================================================
# PUBLIC API
# ============================================================

def dedup_articles(articles: List[Dict]) -> Tuple[List[Dict], int]:
    """Deduplicate articles. Returns (unique_articles, dup_count)."""
    return _dedup.dedup_batch(articles)


def _get_price_for_sym(prices: Dict, sym: str) -> Optional[float]:
    """Safely lookup price from various price dictionary formats."""
    sym_upper = sym.upper()
    lookup_keys = [sym_upper, sym_upper + '-USD']
    if sym_upper == 'GOLD':
        lookup_keys.extend(['XAU', 'GC=F'])
    elif sym_upper == 'SILVER':
        lookup_keys.extend(['XAG', 'SI=F'])
    elif sym_upper == 'XAU':
        lookup_keys.extend(['GOLD', 'GC=F'])
    elif sym_upper == 'XAG':
        lookup_keys.extend(['SILVER', 'SI=F'])

    for k in lookup_keys:
        if k in prices:
            val = prices[k]
            if isinstance(val, dict):
                p = val.get('price')
                if p is not None:
                    try:
                        return float(p)
                    except (ValueError, TypeError):
                        pass
            elif isinstance(val, (int, float)):
                return float(val)
    return None


def record_news_events(articles: List[Dict], live_prices: Dict):
    """Record news events for correlation tracking."""
    if not articles or not live_prices:
        return
    for article in articles:
        score = article.get('sentiment_score', 0)
        symbols = list(set(article.get('symbols', []) or []) | set(article.get('assets', []) or []))
        if article.get('symbol'):
            symbols.append(article['symbol'])
        aid = article.get('id')
        for sym in symbols:
            price = _get_price_for_sym(live_prices, sym)
            if price and price > 0:
                _correlation.record_event(sym.upper(), score, price, article_id=aid)


def update_correlation_prices(live_prices: Dict):
    """Update price checkpoints for correlation."""
    if not live_prices:
        return
    for sym, data in live_prices.items():
        price = data.get('price') if isinstance(data, dict) else data
        if price is not None:
            try:
                p_val = float(price)
                if p_val > 0:
                    _correlation.update_prices(sym.upper(), p_val)
            except (ValueError, TypeError):
                pass


def get_intelligence_summary() -> Dict:
    """Get full intelligence summary for API."""
    anomalies = _anomaly.detect_anomalies()
    correlations = {}
    for sym in ['BTC', 'ETH', 'SOL', 'XRP', 'GOLD', 'XAU']:
        corr = _correlation.get_correlation(sym)
        if not corr.get('insufficient_data'):
            correlations[sym] = corr

    return {
        'anomalies': anomalies,
        'correlations': correlations,
        'dedup_cache_size': len(_dedup._articles),
    }
