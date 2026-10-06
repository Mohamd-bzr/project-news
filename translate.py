#!/usr/bin/env python3
"""
Translation engine — English -> Persian (فارسی)
================================================
Uses the free Google web endpoint (no API key):

    https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=fa&q=...

Characteristics that make it viable for a 30-minute cron style bot:
  • batched — many texts travel in one HTTP request (repeated `q` params),
  • no practical rate limit at this volume (probed: 12 rapid calls, 12 OK),
  • long paragraphs translate in a single call,
  • every translation is cached on disk, so a cycle only pays for *new* text.

Design rules:
  • translation is best-effort — on failure we return the English text and
    flag it, never block or crash the news cycle,
  • Persian output gets Persian numerals (۱۲۳) which is what a Persian
    reader expects on a finance dashboard.
"""

import hashlib
import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from fa_format import fa_digits  # canonical Persian-digit helper

BASE_DIR = Path(__file__).parent
CACHE_FILE = BASE_DIR / ".translate_cache.json"

ENDPOINT = "https://clients5.google.com/translate_a/t"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/128.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}

MAX_CHARS = 4000          # endpoint ceiling per text
BATCH = 16                # texts per HTTP request
WORKERS = 4

_LOCK = threading.Lock()
_CACHE = {}
_LOADED = False
_DIRTY = False
_STATS = {"requests": 0, "ok": 0, "failed": 0, "cache_hits": 0, "translated": 0}

# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------

def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _ensure_loaded():
    global _LOADED, _CACHE
    if _LOADED:
        return
    with _LOCK:
        if _LOADED:
            return
        try:
            _CACHE = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _CACHE = {}
        _LOADED = True


def _flush():
    global _DIRTY
    with _LOCK:
        if not _DIRTY:
            return
        try:
            # keep the cache bounded — newest ~30k entries are plenty
            if len(_CACHE) > 40000:
                for k in list(_CACHE)[:10000]:
                    _CACHE.pop(k, None)
            # atomic: a truncated 2 MB translation cache would cost a full
            # re-translation of every headline after a crash
            tmp = CACHE_FILE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(_CACHE, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, CACHE_FILE)
            _DIRTY = False
        except Exception:
            pass


def cache_stats() -> dict:
    _ensure_loaded()
    return {**_STATS, "cached_total": len(_CACHE)}


# ---------------------------------------------------------------------------
# Google endpoint
# ---------------------------------------------------------------------------

def _flatten(data):
    """Normalize every response shape we have seen into a list[str]."""
    if isinstance(data, list) and data and isinstance(data[0], str):
        return list(data)
    if isinstance(data, dict):
        return [str(data.get("translation") or "")]
    out = []
    for item in (data if isinstance(data, list) else []):
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, list):
            if item and isinstance(item[0], list):
                # [[["متن","en",...],["بیشتر",...]]]
                out.append("".join(seg[0] for seg in item
                                   if isinstance(seg, list) and seg and seg[0]))
            elif item and isinstance(item[0], str):
                out.append(item[0])
            else:
                out.append("")
        else:
            out.append("")
    return out


def _translate_batch(texts: list) -> list:
    """One HTTP request for up to BATCH texts. Returns [] on total failure."""
    clean = [(t or "").strip()[:MAX_CHARS] for t in texts]
    params = [("client", "dict-chrome-ex"), ("sl", "en"), ("tl", "fa")]
    params += [("q", t) for t in clean]
    for attempt in range(3):
        try:
            with _LOCK:
                _STATS["requests"] += 1
            r = requests.get(ENDPOINT, params=params, headers=UA, timeout=25)
            if r.status_code == 200:
                res = _flatten(r.json())
                if len(res) < len(clean):          # pad if Google dropped some
                    res += [""] * (len(clean) - len(res))
                with _LOCK:
                    _STATS["ok"] += 1
                return res[:len(clean)]
            if r.status_code in (429, 500, 502, 503):
                time.sleep(1.2 * (attempt + 1))
                continue
            break
        except Exception:
            time.sleep(0.8 * (attempt + 1))
    with _LOCK:
        _STATS["failed"] += 1
    return []


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


_FA_CHAR_RE = re.compile(r"[\u0600-\u06FF]")


def _looks_persian(text: str) -> bool:
    """True when the text is already Persian (native wire sources)."""
    t = (text or "").strip()
    if len(t) < 4:
        return False
    fa = len(_FA_CHAR_RE.findall(t))
    return fa / len(t) > 0.25


def translate_many(texts, persian_digits: bool = True) -> dict:
    """
    Translate an iterable of English strings to Persian.
    Returns {original: persian}; missing / failed entries are simply absent.
    """
    _ensure_loaded()
    wanted, seen = [], set()
    for t in texts:
        t = (t or "").strip()
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        wanted.append(t)
    if not wanted:
        return {}

    # native-Persian guard: the Persian wire sources (ایسنا، دنیای اقتصاد…)
    # arrive already Persian — sending them through the EN→FA endpoint wastes
    # calls and can mangle the text. Identity-mapped, cached like any other.
    out = {}
    todo = []
    for t in wanted:
        if _looks_persian(t):
            out[t] = fa_digits(t) if persian_digits else t
        else:
            todo.append(t)
    if not todo:
        return out
    keep = []
    with _LOCK:
        for t in todo:
            hit = _CACHE.get(_cache_key(t))
            if hit is not None:
                out[t] = hit
                _STATS["cache_hits"] += 1
            else:
                keep.append(t)

    if keep:
        batches = [keep[i:i + BATCH] for i in range(0, len(keep), BATCH)]
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            results = list(ex.map(_translate_batch, batches))
        global _DIRTY
        for batch, res in zip(batches, results):
            if not res:
                continue
            for src, dst in zip(batch, res):
                dst = (dst or "").strip()
                if not dst:
                    continue
                if persian_digits:
                    dst = fa_digits(dst)
                out[src] = dst
                with _LOCK:
                    _CACHE[_cache_key(src)] = dst
                    _STATS["translated"] += 1
                    _DIRTY = True

    return out


def translate_one(text: str, persian_digits: bool = True):
    if not text:
        return None
    return translate_many([text], persian_digits=persian_digits).get(text)


def translate_paragraphs(paragraphs, persian_digits: bool = True) -> list:
    """Translate a list of long paragraphs — used for full article text."""
    texts = [p for p in (paragraphs or []) if (p or "").strip()]
    if not texts:
        return []
    joined = translate_many(texts, persian_digits=persian_digits)
    return [joined.get(t, t) for t in texts]


def save_cache():
    _flush()


if __name__ == "__main__":
    import sys
    samples = [
        "Bitcoin slides toward $77,000 ahead of the Senate vote on the CLARITY Act",
        "Ethereum wallet loses $7.8 million in a custom Safe module exploit",
        "Gold and silver fell to five-week lows, wiping out $650 billion in value",
    ]
    t0 = time.time()
    res = translate_many(samples)
    for s in samples:
        print("-", s)
        print("  ", res.get(s, "(failed)"))
    print(f"\n{time.time()-t0:.1f}s  stats={cache_stats()}")
    save_cache()
