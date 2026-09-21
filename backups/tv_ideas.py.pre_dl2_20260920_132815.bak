#!/usr/bin/env python3
"""
TradingView Ideas fetcher — parses the embedded JSON on public ideas pages
(no API key, no auth). One page per symbol tag, e.g. /ideas/btcusd/.
Fails independently and returns [] on any problem.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_CACHE: dict[str, dict] = {}          # tag -> {"ts": float, "items": [...]}
_TTL = 1800.0                         # ideas change slowly — 30 min cache
_PAGE_TIMEOUT = 12

# symbol tag per tracked asset (TradingView slug, lowercase)
TAG_BY_ASSET = {
    "BTC": "btcusd", "ETH": "ethusd", "SOL": "solusd", "XRP": "xrpusd",
    "XAU": "xauusd", "ADA": "adausd", "BNB": "bnbusd", "DOGE": "dogeusd",
    "XAG": "xagusd", "WTI": "wti", "DXY": "dxy", "SPX": "spx", "VIX": "vix",
}

_ITEMS_RE = re.compile(r'"ideas":\{"data":\{"total":\d+,"items":')


def _extract_items(html: str) -> list:
    """Pull the ideas items array out of the page's embedded JSON."""
    m = _ITEMS_RE.search(html)
    if not m:
        return []
    seg = html[m.end():]
    start = seg.find("[")
    if start < 0:
        return []
    depth = 0
    end = None
    for k in range(start, min(start + 300_000, len(seg))):
        c = seg[k]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    if not end:
        return []
    try:
        return json.loads(seg[start:end])
    except Exception:
        return []


def _parse_idea(it: dict) -> dict | None:
    try:
        sym = (it.get("symbol") or {})
        user = (it.get("user") or {})
        ts = it.get("date_timestamp") or it.get("updated_date_timestamp")
        dt = (datetime.fromtimestamp(ts, timezone.utc) if ts else None)
        created = it.get("created_at") or ""
        if not dt and created:
            dt = datetime.fromisoformat(created)
        img = it.get("image") or {}
        img_url = ""
        if isinstance(img, dict):
            img_url = img.get("url") or ""
        if not img_url and it.get("image_url"):
            img_url = f"https://s3.tradingview.com/s/{it['image_url']}.png"
        direction = sym.get("direction")
        return {
            "id": str(it.get("id") or ""),
            "title": (it.get("name") or "").strip(),
            "description": (it.get("description") or "").strip(),
            "link": f"https://www.tradingview.com/idea/{it.get('id')}/",
            "chart_url": it.get("chart_url") or "",
            "image": img_url,
            "symbol": sym.get("full_name") or sym.get("short_name") or "",
            "symbol_dir": ({1: "Long", -1: "Short", 0: "Neutral"}.get(direction, "")),
            "user": user.get("username") or "",
            "user_pro": bool(user.get("is_pro")),
            "likes": int(it.get("likes_count") or 0),
            "views": int(it.get("views_count") or 0),
            "comments": int(it.get("comments_count") or 0),
            "hot": bool(it.get("is_hot")),
            "ts": int(dt.timestamp()) if dt else 0,
            "iso": dt.isoformat() if dt else "",
        }
    except Exception:
        return None


def fetch_ideas(tag: str, limit: int = 12) -> list:
    """Public ideas for one TradingView tag (e.g. 'btcusd')."""
    tag = (tag or "").strip().lower()
    if not tag:
        return []
    c = _CACHE.get(tag)
    now = time.time()
    if c and now - c["ts"] < _TTL:
        return c["items"][:limit]
    try:
        r = requests.get(f"https://www.tradingview.com/ideas/{tag}/",
                         headers=_UA, timeout=_PAGE_TIMEOUT)
        raw = _extract_items(r.text) if r.status_code == 200 else []
    except Exception:
        raw = []
    items = [x for x in (_parse_idea(i) for i in raw) if x and x["title"]]
    items.sort(key=lambda x: -x["likes"])          # quality first, then recency
    items.sort(key=lambda x: -x["ts"])
    if items:
        _CACHE[tag] = {"ts": now, "items": items}
    return items[:limit]


def fetch_all(tags: list[str] | None = None, limit: int = 8) -> dict:
    """Ideas for several tags at once, parallel. Returns {tag: [items]}."""
    tags = tags or list(TAG_BY_ASSET.values())
    out: dict[str, list] = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch_ideas, t, limit): t for t in tags}
        for f, t in futs.items():
            try:
                out[t] = f.result()
            except Exception:
                out[t] = []
    return out


if __name__ == "__main__":
    import sys
    tag = sys.argv[1] if len(sys.argv) > 1 else "btcusd"
    got = fetch_ideas(tag, limit=5)
    print(f"{tag}: {len(got)} ideas")
    for x in got[:5]:
        print(f"  [{x['symbol_dir'] or '-'}] {x['title'][:60]} | likes={x['likes']} | {x['iso'][:16]}")
