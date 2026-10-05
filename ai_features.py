"""AI-powered features for FreeBuff.
Summarization, anomaly detection, and predictions.

Uses OpenAI API (gpt-4o-mini) for summaries.
Uses local statistical methods for anomalies and predictions.
No heavy ML dependencies required.
"""

import json
import time
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger('freebuff.ai')

# ============================================================
# NEWS SUMMARIZATION
# ============================================================

_summary_cache = {}  # symbol -> {summary, ts}
_summary_lock = threading.Lock()
_SUMMARY_TTL = 3600  # 1 hour

OPENAI_API_KEY = None  # Set from settings
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_BASE_URL = None


def _init_openai(api_key: str, model: Optional[str] = None, base_url: Optional[str] = None):
    global OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL
    OPENAI_API_KEY = (api_key or "").strip() or None
    if model:
        OPENAI_MODEL = model
    if base_url:
        OPENAI_BASE_URL = base_url.rstrip('/')
    elif OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-or-"):
        OPENAI_BASE_URL = "https://openrouter.ai/api/v1"
    else:
        OPENAI_BASE_URL = "https://api.openai.com/v1"


def _call_openai(prompt: str, max_tokens: int = 500,
                 system: Optional[str] = None,
                 temperature: float = 0.3) -> Optional[str]:
    """Call OpenAI or OpenRouter API. Returns response text or None.

    `system` prepends a system-role message — the "Ask the News" RAG feature
    needs one fixed instruction block ahead of the per-request article turn.
    """
    if not OPENAI_API_KEY:
        return None
    
    import requests
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    base = OPENAI_BASE_URL
    if not base:
        if OPENAI_API_KEY.startswith("sk-or-"):
            base = "https://openrouter.ai/api/v1"
        else:
            base = "https://api.openai.com/v1"

    url = f"{base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    if "openrouter" in base.lower():
        headers["HTTP-Referer"] = "http://localhost:5055"
        headers["X-Title"] = "FreeBuff"

    model = OPENAI_MODEL or "gpt-4o-mini"
    if "openrouter" in base.lower() and model == "gpt-4o-mini":
        model = "openai/gpt-4o-mini"

    try:
        resp = requests.post(
            url,
            headers=headers,
            json={
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content']
        else:
            logger.error(f"AI API error ({url}): {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"AI API call failed ({url}): {e}")
        return None


def summarize_asset_news(symbol: str, articles: List[Dict]) -> Optional[Dict]:
    """Generate AI summary for an asset's recent news.
    
    Returns:
        {'summary': str, 'key_points': [str], 'sentiment': str, 'timestamp': float}
    """
    sym_u = symbol.upper()
    # Check cache
    with _summary_lock:
        cached = _summary_cache.get(sym_u)
        if cached and time.time() - cached.get('timestamp', 0) < _SUMMARY_TTL:
            return cached
    
    # Filter articles for this symbol. The union matters: `symbols or assets`
    # ignored every `assets` tag the moment something also wrote `symbols`.
    asset_articles = [
        a for a in articles
        if sym_u in (set(a.get('symbols') or []) | set(a.get('assets') or []))
    ]
    if not asset_articles:
        return None
    
    # Build prompt
    article_list = "\n".join([
        f"- [{a.get('source_name', '?')}] {a.get('title', '')}: {a.get('summary', '')[:150]}"
        for a in asset_articles[:15]  # Limit to 15 articles
    ])
    
    prompt = f"""Analyze these recent news articles about {sym_u} and provide:

1. A 2-3 sentence summary of the overall sentiment and key developments
2. 3-5 key bullet points
3. Overall sentiment: bullish, bearish, or neutral

Articles:
{article_list}

Respond in JSON format:
{{
    "summary": "...",
    "key_points": ["...", "...", "..."],
    "sentiment": "bullish|bearish|neutral"
}}"""
    
    response = _call_openai(prompt, max_tokens=400)
    if not response:
        return None
    
    # Parse response
    try:
        clean = response.strip()
        if "```json" in clean:
            clean = clean.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in clean:
            clean = clean.split("```", 1)[1].split("```", 1)[0].strip()
        json_start = clean.find('{')
        json_end = clean.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(clean[json_start:json_end])
        else:
            result = {"summary": clean, "key_points": [], "sentiment": "neutral"}
    except Exception:
        result = {"summary": response[:500], "key_points": [], "sentiment": "neutral"}
    
    result['timestamp'] = time.time()
    result['article_count'] = len(asset_articles)
    
    # Cache
    with _summary_lock:
        _summary_cache[sym_u] = result
    
    return result


# ============================================================
# VOLUME ANOMALY DETECTION (statistical, no AI)
# ============================================================

class VolumeAnomalyDetector:
    """Detect unusual news volume using z-score analysis.
    
    No external dependencies. Pure statistical.
    """
    
    def __init__(self, window: int = 30, threshold: float = 2.5):
        self.window = window  # rolling window size
        self.threshold = threshold  # z-score threshold
        self._history = defaultdict(list)  # symbol -> [count_per_cycle]
        self._lock = threading.Lock()
    
    def record(self, articles: List[Dict]):
        """Record article counts for this cycle."""
        counts = defaultdict(int)
        for a in articles:
            syms = set(a.get('symbols') or []) | set(a.get('assets') or [])
            for sym in syms:
                counts[sym.upper()] += 1
        
        with self._lock:
            for sym, count in counts.items():
                self._history[sym].append(count)
                if len(self._history[sym]) > self.window * 3:
                    self._history[sym] = self._history[sym][-self.window * 3:]
    
    def detect(self) -> List[Dict]:
        """Detect anomalies in the most recent cycle.
        
        Returns list of anomalies sorted by severity.
        """
        anomalies = []
        with self._lock:
            for sym, counts in self._history.items():
                if len(counts) < self.window:
                    continue
                
                recent = counts[-1]
                historical = counts[-self.window:-1]  # exclude current
                
                if not historical:
                    continue
                
                mean = sum(historical) / len(historical)
                variance = sum((x - mean) ** 2 for x in historical) / len(historical)
                std = variance ** 0.5
                
                if std == 0:
                    if recent > mean:
                        z_score = (recent - mean) / 0.5
                    else:
                        continue
                else:
                    z_score = (recent - mean) / std
                
                if z_score >= self.threshold:
                    anomalies.append({
                        'symbol': sym,
                        'current_count': recent,
                        'avg_count': round(mean, 1),
                        'std': round(std, 1),
                        'z_score': round(z_score, 1),
                        'severity': 'high' if z_score >= 3.5 else 'medium',
                        'message': f"{sym}: {recent} articles (avg {mean:.0f}, z-score {z_score:.1f})",
                    })
        
        return sorted(anomalies, key=lambda x: x['z_score'], reverse=True)


# ============================================================
# PREDICTIVE SENTIMENT (local ML, no API)
# ============================================================

class SentimentPredictor:
    """Predict future sentiment trend using historical data.
    
    Uses simple moving average crossover and momentum.
    No ML library required — pure Python math.
    """
    
    def __init__(self):
        self._history = defaultdict(list)  # symbol -> [(ts, sentiment_score)]
        self._price_history = defaultdict(list)  # symbol -> [(ts, price)]
        self._lock = threading.Lock()
    
    def record(self, symbol: str, sentiment_score: float, price: Optional[float] = None):
        """Record sentiment and price for a symbol."""
        now = time.time()
        sym_u = symbol.upper()
        with self._lock:
            self._history[sym_u].append((now, float(sentiment_score or 0.0)))
            if price is not None:
                self._price_history[sym_u].append((now, float(price)))
            
            # Keep last 1000 entries
            if len(self._history[sym_u]) > 1000:
                self._history[sym_u] = self._history[sym_u][-1000:]
            if len(self._price_history[sym_u]) > 1000:
                self._price_history[sym_u] = self._price_history[sym_u][-1000:]
    
    def predict(self, symbol: str) -> Dict:
        """Predict sentiment trend for next 24 hours.
        
        Returns:
            {
                'prediction': 'bullish' | 'bearish' | 'neutral',
                'confidence': float (0-1),
                'momentum': float (-1 to 1),
                'short_ma': float,
                'long_ma': float,
                'data_points': int,
            }
        """
        sym_u = symbol.upper()
        with self._lock:
            scores = [s for _, s in self._history.get(sym_u, [])]
        
        if len(scores) < 10:
            return {'prediction': 'neutral', 'direction': 'neutral', 'confidence': 0.0, 'data_points': len(scores)}
        
        # Short-term MA (last 5)
        short_ma = sum(scores[-5:]) / 5.0
        
        # Long-term MA (last 20)
        long_window = min(20, len(scores))
        long_ma = sum(scores[-long_window:]) / float(long_window)
        
        # Momentum (rate of change in last 10)
        recent = scores[-10:]
        momentum = (recent[-1] - recent[0]) / max(abs(recent[0]), 0.01)
        momentum = max(-1.0, min(1.0, momentum))
        
        # Prediction
        if short_ma > long_ma + 0.05 and momentum > 0.1:
            prediction = 'bullish'
            confidence = min(1.0, abs(short_ma - long_ma) * 5 + abs(momentum))
        elif short_ma < long_ma - 0.05 and momentum < -0.1:
            prediction = 'bearish'
            confidence = min(1.0, abs(short_ma - long_ma) * 5 + abs(momentum))
        else:
            prediction = 'neutral'
            confidence = 1.0 - min(1.0, abs(short_ma - long_ma) * 5)
        
        return {
            'prediction': prediction,
            'direction': prediction,
            'confidence': round(confidence, 3),
            'momentum': round(momentum, 3),
            'short_ma': round(short_ma, 3),
            'long_ma': round(long_ma, 3),
            'data_points': len(scores),
        }


# Global instances
_anomaly_detector = VolumeAnomalyDetector()
_predictor = SentimentPredictor()


# ============================================================
# PUBLIC API
# ============================================================

def get_ai_summary(symbol: str, articles: List[Dict]) -> Optional[Dict]:
    """Get AI summary for an asset (cached, may return None if no API key)."""
    return summarize_asset_news(symbol, articles)


def detect_anomalies(articles: List[Dict]) -> List[Dict]:
    """Detect news volume anomalies."""
    _anomaly_detector.record(articles)
    return _anomaly_detector.detect()


def predict_sentiment(symbol: str, articles: List[Dict]) -> Dict:
    """Get sentiment prediction for an asset."""
    sym_u = symbol.upper()
    asset_articles = [
        a for a in articles
        if sym_u in (set(a.get('symbols') or []) | set(a.get('assets') or []))
    ]
    if asset_articles:
        avg_score = sum(float(a.get('sentiment_score', 0.0)) for a in asset_articles) / len(asset_articles)
        _predictor.record(sym_u, avg_score)
    
    return _predictor.predict(sym_u)


def get_all_predictions(articles: List[Dict]) -> Dict:
    """Get predictions for all tracked symbols."""
    symbols = set()
    for a in articles:
        for sym in (set(a.get('symbols') or []) | set(a.get('assets') or [])):
            symbols.add(sym.upper())
    
    predictions = {}
    for sym in symbols:
        predictions[sym] = predict_sentiment(sym, articles)
    
    return predictions
