#!/usr/bin/env python3
"""
Reddit live scores — arctic-shift bridge
========================================
Reddit's RSS carries no score field and reddit.com's JSON endpoints answer
403/429 to this server, so upvote counts are recovered from the Arctic Shift
public archive (https://arctic-shift.photon-reddit.com) which stores
frequently-refreshed post metadata (`score`, `num_comments`).

The `scrape_all()` pipeline calls `attach_scores()` once per cycle for the
social articles; anything below the configured minimum score — or with no
readable score at all — is dropped before validation (fail-closed), so the
counters in the UI reflect the cut. A post whose score only lands in the
archive later re-enters the feed on a subsequent cycle once it qualifies.
"""

import json
import re
import time
from pathlib import Path

import requests

# Reddit RSS links look like https://www.reddit.com/r/<sub>/comments/<id8>/slug/
_ID_RE = re.compile(r"/comments/([a-z0-9]{6,10})/", re.I)

API_URL = "https://arctic-shift.photon-reddit.com/api/posts/ids"
_BATCH = 25          # ids per request (URL length + server comfort)
_PAUSE = 0.4         # seconds between requests — be polite
_TIMEOUT = 20

_CACHE_FILE = Path(__file__).with_name(".reddit_scores.json")
_CACHE_TTL = 6 * 3600     # scores older than this are re-fetched
_CACHE_MIN = 600          # but never re-fetch more often than 10 minutes

_cache = {}              # id -> {"score": int|None, "comments": int|None,
                         #        "ts": epoch}
_loaded = False


def _load_cache():
    global _loaded
    _loaded = True
    try:
        if _CACHE_FILE.exists():
            raw = json.loads(_CACHE_FILE.read_text("utf-8"))
            if isinstance(raw, dict):
                _cache.update(raw)
    except Exception:
        pass


def _save_cache():
    try:
        _CACHE_FILE.write_text(
            json.dumps(_cache, ensure_ascii=False), "utf-8")
    except Exception:
        pass


def _extract_id(link: str):
    m = _ID_RE.search(link or "")
    return m.group(1) if m else None


def fetch_scores(ids):
    """Return {id: (score, num_comments)} for the ids we could resolve.
    Missing ids simply don't appear in the result. Never raises."""
    if not ids:
        return {}
    out = {}
    for i in range(0, len(ids), _BATCH):
        chunk = ids[i:i + _BATCH]
        try:
            r = requests.get(API_URL, params={"ids": ",".join(chunk)},
                             timeout=_TIMEOUT,
                             headers={"User-Agent": "mohmd-news/1.0"})
            if r.status_code != 200:
                continue
            for row in (r.json().get("data") or []):
                rid = row.get("id")
                if rid:
                    out[rid] = (row.get("score"), row.get("num_comments"))
        except Exception:
            continue
        time.sleep(_PAUSE)
    return out


def attach_scores(articles, min_score=0, min_comments=0, max_age_hours=None):
    """Attach `reddit_score` / `reddit_comments` to social articles and drop
    the ones below `min_score` upvotes or `min_comments` comments.
    Returns (kept_articles, dropped_count).

    Cache discipline: an entry younger than _CACHE_TTL is trusted; a miss
    (post not in the archive yet — a few minutes old) is remembered for
    _CACHE_MIN so one cycle cannot hammer the API with re-queries.
    `max_age_hours` bounds the fetch to articles that can pass the freshness
    gate anyway."""
    if not articles:
        return articles, 0
    if not _loaded:
        _load_cache()

    now = time.time()
    cutoff = now - (max_age_hours * 3600) if max_age_hours else None

    want, id_map = [], {}
    for a in articles:
        rid = _extract_id(a.get("link") or "")
        if not rid:
            continue
        key = a.get("id") or a.get("link") or id(a)   # raw pre-validation
        id_map[key] = rid
        ent = _cache.get(rid)
        fresh_enough = (cutoff is None or
                        (a.get("published_ts") or 0) >= cutoff)
        if ent and (now - ent.get("ts", 0)) < _CACHE_TTL:
            a["reddit_score"] = ent.get("score")
            a["reddit_comments"] = ent.get("comments")
        elif fresh_enough:
            want.append(rid)

    if want:
        fetched_now = fetch_scores(sorted(set(want)))
        for rid in sorted(set(want)):
            if rid in fetched_now:
                score, comments = fetched_now[rid]
                _cache[rid] = {"score": score, "comments": comments, "ts": now}
            else:
                # archive miss (post is only minutes old) — park it briefly so
                # one cycle cannot hammer the API re-probing a missing id
                _cache[rid] = {"score": None, "comments": None,
                               "ts": now - (_CACHE_TTL - _CACHE_MIN)}
        _save_cache()

    # attach whatever the cache now holds — also when `want` was empty
    # (everything already cached) since these article dicts are brand new
    for a in articles:
        key = a.get("id") or a.get("link") or id(a)
        rid = id_map.get(key)
        if rid and rid in _cache and "reddit_score" not in a:
            ent = _cache[rid]
            a["reddit_score"] = ent.get("score")
            a["reddit_comments"] = ent.get("comments")

    if min_score <= 0 and min_comments <= 0:
        return articles, 0

    kept, dropped = [], 0
    for a in articles:
        score = a.get("reddit_score")
        comments = a.get("reddit_comments")
        # fail-closed: an unresolved score (archive lag, API down) drops the
        # post — the next cycle re-probes it, so a post that genuinely earns
        # the minimum re-enters the feed once the archive has its score
        ok_score = (min_score <= 0 or (score is not None and score >= min_score))
        ok_comments = (min_comments <= 0 or
                       (comments is not None and comments >= min_comments))
        if ok_score and ok_comments:
            kept.append(a)
        else:
            dropped += 1
    return kept, dropped
