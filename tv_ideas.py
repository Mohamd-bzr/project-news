#!/usr/bin/env python3
"""
TradingView Ideas fetcher — parses the embedded JSON on public ideas pages
(no API key, no auth). One page per symbol tag, e.g. /ideas/btcusd/.
Fails independently and returns [] on any problem.

Permalinks: the numeric ``id`` in the payload is NOT the public URL — the
resolvable address lives in ``chart_url`` ("/chart/SYMBOL/<slug>-<title>/").
``https://www.tradingview.com/idea/<id>/`` returns 404, which is why the old
cards never opened. Chart thumbnails likewise live on
``s3.tradingview.com/c/<slug>_big.png`` (the ``/s/`` prefix 403s).
"""

from __future__ import annotations

import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_CACHE: dict[str, dict] = {}          # tag -> {"ts": float, "items": [...]}
_TTL = 1800.0                         # ideas change slowly — 30 min cache
_PAGE_TIMEOUT = 12
_IDEAS_BASE = "https://www.tradingview.com/ideas/"
_AUTHOR_BASE = "https://www.tradingview.com/u/"
_FOLLOWERS: dict[str, dict] = {}      # username -> {"ts", "count"}
_FOLLOWERS_TTL = 86400.0              # an author's follower count moves slowly
_FOLLOWERS_RE = re.compile(r'"followers"\s*:\s*"?(\d+)')

# TradingView's own idea feed labels, mirrored by the dashboard's filter bar
SORTS = ("popular", "recent", "followers")   # Popular · Latest · author reach
KINDS = ("all", "picked", "video", "education")

# TradingView slug per tracked asset (the /ideas/<slug>/ page is per market)
TAG_BY_ASSET = {
    "BTC": "btcusd", "ETH": "ethusd", "SOL": "solusd", "XRP": "xrpusd",
    "ADA": "adausd", "BNB": "bnbusd", "DOGE": "dogeusd", "LINK": "linkusd",
    "XAU": "xauusd", "XAG": "xagusd", "WTI": "wti",
    "DXY": "dollarindex", "SPX": "spx", "VIX": "vix",
}

_ITEMS_RE = re.compile(r'"ideas":\{"data":\{"total":\d+,"items":')
_MD_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL_RE = re.compile(r"https?://\S+")
_MD_MARK_RE = re.compile(r"[*_`>#|]+")


def tag_for(sym: str) -> str:
    """TradingView tag for an asset symbol ('BTC' -> 'btcusd')."""
    s = (sym or "").strip().upper()
    return TAG_BY_ASSET.get(s) or s.lower()


def _extract_items(html: str) -> list:
    """Pull the ideas items array out of the page's embedded JSON."""
    m = _ITEMS_RE.search(html)
    if not m:
        return []
    seg = html[m.end():]
    start = seg.find("[")
    if start < 0:
        return []
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(seg, start)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass
    return []


def _clean_text(md: str, limit: int = 420) -> str:
    """Markdown-ish idea body -> plain readable text (optionally truncated)."""
    t = md or ""
    t = _MD_IMG_RE.sub(" ", t)
    t = _MD_LINK_RE.sub(r"\1", t)
    t = _URL_RE.sub(" ", t)
    t = _MD_MARK_RE.sub(" ", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\s*\n\s*", " ", t).strip()
    if limit and len(t) > limit:
        cut = t[:limit]
        sp = cut.rfind(" ")
        t = (cut[:sp] if sp > limit * 0.6 else cut).rstrip() + "…"
    return t


def _image_url(it: dict) -> str:
    """Chart thumbnail — the payload carries big / middle / middle_webp."""
    img = it.get("image")
    if isinstance(img, dict):
        for key in ("big", "middle_webp", "middle", "url"):
            if img.get(key):
                return str(img[key])
    elif isinstance(img, str) and img:
        return img
    slug = it.get("image_url")
    return f"https://s3.tradingview.com/c/{slug}_big.png" if slug else ""


def _link(it: dict, tag: str) -> str:
    """Resolvable permalink. /idea/<numeric id>/ 404s, so prefer chart_url."""
    link = str(it.get("chart_url") or "").strip()
    if link:
        return link
    slug, short = str(it.get("image_url") or ""), ""
    sym = it.get("symbol") or {}
    if isinstance(sym, dict):
        short = str(sym.get("short_name") or "")
    if slug and short:
        return f"https://www.tradingview.com/chart/{short}/{slug}/"
    return _IDEAS_BASE + (tag or "") + "/"


def fetch_followers(username: str) -> int:
    """Follower count of one TradingView author (0 when unknown).

    The ideas payload carries no audience size, so the public profile page is
    read once per author and cached for a day — that is what lets the ideas
    tab rank the authors people actually follow above one-off posters.
    """
    username = (username or "").strip()
    if not username:
        return 0
    c = _FOLLOWERS.get(username)
    now = time.time()
    if c and now - c["ts"] < _FOLLOWERS_TTL:
        return c["count"]
    count = 0
    try:
        r = requests.get(_AUTHOR_BASE + username + "/",
                         headers=_UA, timeout=_PAGE_TIMEOUT)
        if r.status_code == 200:
            hits = [int(x) for x in _FOLLOWERS_RE.findall(r.text)]
            count = max(hits) if hits else 0
    except Exception:
        count = 0
    _FOLLOWERS[username] = {"ts": now, "count": count}
    return count


def fetch_followers_many(usernames) -> dict:
    """Followers for several authors at once, parallel ({username: count})."""
    todo = []
    now = time.time()
    for u in dict.fromkeys([(x or "").strip() for x in usernames]):
        if not u:
            continue
        c = _FOLLOWERS.get(u)
        if not c or now - c["ts"] >= _FOLLOWERS_TTL:
            todo.append(u)
    if todo:
        with ThreadPoolExecutor(max_workers=6) as ex:
            list(ex.map(fetch_followers, todo))
    return {u: _FOLLOWERS.get(u, {}).get("count", 0)
            for u in dict.fromkeys([(x or "").strip() for x in usernames]) if u}


def _parse_idea(it: dict, tag: str = "") -> dict | None:
    try:
        sym = (it.get("symbol") or {})
        if not isinstance(sym, dict):
            sym = {}
        user = (it.get("user") or {})
        if not isinstance(user, dict):
            user = {}
        ts = it.get("date_timestamp") or it.get("updated_date_timestamp")
        dt = (datetime.fromtimestamp(ts, timezone.utc) if ts is not None else None)
        created = it.get("created_at") or ""
        if not dt and created:
            dt = datetime.fromisoformat(created)
        body = _clean_text(it.get("description") or "", limit=0)
        snippet = _clean_text(it.get("description") or "", limit=420)
        direction = sym.get("direction")
        return {
            "id": str(it.get("id") or ""),
            "asset": tag,
            "title": re.sub(r"\s+", " ", (it.get("name") or "")).strip(),
            "snippet": snippet,
            "body": body,
            "link": _link(it, tag),
            "image": _image_url(it),
            "image_big": _image_url(it),
            "symbol": sym.get("full_name") or sym.get("short_name") or "",
            "symbol_short": sym.get("short_name") or "",
            "interval": sym.get("interval") or "",
            "symbol_dir": ({1: "Long", -1: "Short", 0: "Neutral"}.get(direction)
                           or ("Long" if direction is True else "Short" if direction is False else "")),
            "user": user.get("username") or "",
            "user_pro": bool(user.get("badges")),
            "user_avatar": user.get("mid_picture_url") or user.get("picture_url") or "",
            "followers": 0,                     # filled by fetch_ideas()
            "likes": int(it.get("likes_count") or 0),
            "views": int(it.get("views_count") or 0),
            "comments": int(it.get("comments_count") or 0),
            "hot": bool(it.get("is_hot")),
            "picked": bool(it.get("is_picked")),
            "video": bool(it.get("is_video")),
            "education": bool(it.get("is_education")),
            "script": bool(it.get("is_script")),
            "ts": int(dt.timestamp()) if dt else 0,
            "iso": dt.isoformat() if dt else "",
        }
    except Exception:
        return None


def popularity(x: dict) -> float:
    """TradingView-style popularity: engagement first, audience as tiebreak."""
    return (x.get("likes", 0) * 3.0 + x.get("comments", 0) * 2.0
            + math.log10((x.get("followers") or 0) + 1) * 4.0
            + (6.0 if x.get("picked") else 0.0)
            + (4.0 if x.get("hot") else 0.0))


def sort_items(items: list, mode: str = "popular") -> list:
    """mode: popular (TV 'Popular') · recent (TV chronological) · followers."""
    mode = (mode or "popular").lower()
    if mode == "recent":
        return sorted(items, key=lambda x: -x.get("ts", 0))
    if mode == "followers":
        return sorted(items, key=lambda x: (-x.get("followers", 0),
                                            -x.get("likes", 0), -x.get("ts", 0)))
    return sorted(items, key=lambda x: (-popularity(x), -x.get("ts", 0)))


def filter_items(items: list, kind: str = "all") -> list:
    """kind mirrors the badges TradingView puts on its cards."""
    kind = (kind or "all").lower()
    if kind == "picked":
        return [x for x in items if x.get("picked")]
    if kind == "video":
        return [x for x in items if x.get("video")]
    if kind == "education":
        return [x for x in items if x.get("education")]
    return items


def fetch_ideas(tag: str, limit: int = 12, asset: str = "") -> list:
    """Public ideas for one TradingView tag (e.g. 'btcusd'), newest first.

    Every idea is annotated with its author's follower count so the dashboard
    can rank predictable, well-followed analysts above one-off posters.
    """
    tag = (tag or "").strip().lower()
    if not tag:
        return []
    c = _CACHE.get(tag)
    now = time.time()
    if c and now - c["ts"] < _TTL:
        return c["items"][:limit]
    raw: list = []
    try:
        r = requests.get(f"{_IDEAS_BASE}{tag}/", headers=_UA, timeout=_PAGE_TIMEOUT)
        if r.status_code == 200:
            raw = _extract_items(r.text)
    except Exception:
        raw = []
    asset = (asset or tag).upper()
    items = [x for x in (_parse_idea(i, asset) for i in raw) if x and x["title"]]
    if items:
        try:
            reach = fetch_followers_many([x["user"] for x in items])
            for x in items:
                x["followers"] = reach.get(x["user"], 0)
        except Exception:
            pass
    items.sort(key=lambda x: -x["ts"])           # newest first
    if items:
        _CACHE[tag] = {"ts": now, "items": items}
    return items[:limit]


def find_idea(sym: str, idea_id: str) -> dict | None:
    """One cached idea by asset + id (used by the Persian translation route)."""
    tag = tag_for(sym)
    c = _CACHE.get(tag)
    if c:
        hit = next((x for x in c["items"] if str(x.get("id")) == str(idea_id)), None)
        if hit:
            return hit
    for c in _CACHE.values():                     # id is globally unique
        hit = next((x for x in c["items"] if str(x.get("id")) == str(idea_id)), None)
        if hit:
            return hit
    return None


def ideas_page_url(tag: str) -> str:
    return _IDEAS_BASE + (tag or "") + "/"


def fetch_asset(sym: str, limit: int = 30, sort: str = "popular",
                kind: str = "all") -> dict:
    """{ok, sym, tag, url, items} for one asset symbol ('BTC' / a custom one)."""
    sym = (sym or "BTC").strip().upper()
    tag = tag_for(sym)
    items = fetch_ideas(tag, limit=max(limit, 30), asset=sym)
    items = filter_items(items, kind)
    items = sort_items(items, sort)[:limit]
    return {"ok": bool(items), "sym": sym, "tag": tag, "sort": sort,
            "kind": kind, "url": ideas_page_url(tag), "items": items}


if __name__ == "__main__":
    import sys
    tag = sys.argv[1] if len(sys.argv) > 1 else "btcusd"
    got = fetch_ideas(tag, limit=8)
    print(f"{tag}: {len(got)} ideas")
    for x in sort_items(got, "popular")[:5]:
        print(f"  [{x['symbol_dir'] or '-'}|{x['interval'] or '?'}] {x['title'][:52]}"
              f"  ❤{x['likes']} 💬{x['comments']} 👥{x['followers']}"
              f"{' ⭐' if x['picked'] else ''}")
        print(f"      {x['link']}")
