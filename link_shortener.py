#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Short news links so channel readers actually tap them.

Providers, tried in order when `provider` is "auto":
  1. opizo  — Iranian; short links OPEN for readers inside Iran. Needs a free
              API key (opizo.com → dashboard → API key).
  2. tinyurl / is.gd — keyless but foreign: creation and clicks only work
              when the network path allows them (VPN / custom gateway).
  3. original URL — a dead shortener must never break a send.

A `custom` provider accepts any endpoint that answers
`GET {endpoint}?url=<link>` with a plain short URL in the body.
Mappings are cached on disk per provider, matching the app's other
root dot-cache files.
"""

import json
import threading
from pathlib import Path
from urllib.parse import quote

import requests

CACHE_FILE = Path(__file__).resolve().parent / ".link_shortener_cache.json"
_TIMEOUT = 6

_LOCK = threading.Lock()
_CACHE = None
_CACHE_LOADED = False

# a provider that just timed out stays dead for a while — without this, a
# filtered shortener taxes EVERY item with its full connect timeout
_PROVIDER_BLOCKED = {}
_PROVIDER_COOLDOWN = 600.0


def _load_cache():
    global _CACHE, _CACHE_LOADED
    if _CACHE_LOADED:
        return _CACHE
    try:
        _CACHE = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        _CACHE = {}
    _CACHE_LOADED = True
    return _CACHE


def _save_cache():
    try:
        CACHE_FILE.write_text(
            json.dumps(_CACHE, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass  # the cache is an optimization, never a failure


def _tinyurl(url, cfg):
    r = requests.get("https://tinyurl.com/api-create.php",
                     params={"url": url}, timeout=_TIMEOUT)
    short = (r.text or "").strip()
    if r.status_code == 200 and short.startswith("http"):
        return short
    raise ValueError(f"tinyurl bad response: {r.status_code}")


def _isgd(url, cfg):
    r = requests.get("https://is.gd/create.php",
                     params={"format": "simple", "url": url}, timeout=_TIMEOUT)
    short = (r.text or "").strip()
    if r.status_code == 200 and short.startswith("http"):
        return short
    raise ValueError(f"is.gd bad response: {r.status_code} {short[:60]}")


def _opizo(url, cfg):
    """Iranian shortener — opizo.com, free account, X-API-KEY header.

    The response shape is parsed defensively: the documented body carries the
    short link under `url`, but the parser also accepts `short`/`link` or a
    bare URL in the text so a minor API change degrades instead of failing.
    """
    key = str((cfg or {}).get("api_key") or "").strip()
    if not key:
        raise ValueError("opizo needs an api_key")
    r = requests.post("https://opizo.com/api/v1/links",
                      json={"url": url},
                      headers={"X-API-KEY": key,
                               "Content-Type": "application/json"},
                      timeout=_TIMEOUT)
    if r.status_code not in (200, 201):
        raise ValueError(f"opizo bad status: {r.status_code} {r.text[:80]}")
    try:
        data = r.json()
        for k in ("url", "short", "link", "short_url", "result"):
            v = str((data or {}).get(k) or "").strip()
            if v.startswith("http"):
                return v
    except Exception:
        pass
    text = (r.text or "").strip()
    if text.startswith("http"):
        return text
    raise ValueError("opizo could not parse a short link from the response")


def _custom(url, cfg):
    endpoint = str((cfg or {}).get("custom_endpoint") or "").strip()
    if not endpoint:
        raise ValueError("custom provider needs custom_endpoint")
    r = requests.get(endpoint, params={"url": url}, timeout=_TIMEOUT)
    short = (r.text or "").strip()
    if r.status_code == 200 and short.startswith("http"):
        return short
    raise ValueError(f"custom bad response: {r.status_code}")


_PROVIDERS = {"tinyurl": _tinyurl, "isgd": _isgd, "opizo": _opizo, "custom": _custom}


def _chain(cfg):
    """Providers to try, honouring the operator's choice and key availability."""
    cfg = cfg or {}
    want = str(cfg.get("provider") or "auto").strip().lower()
    if want == "none":
        return []   # the operator switched shortening off
    if want in _PROVIDERS:
        return [want]
    chain = []
    if str(cfg.get("api_key") or "").strip():
        chain.append("opizo")     # Iranian-open links win when a key exists
    chain += ["tinyurl", "isgd"]
    return chain


def shorten(url, cfg=None):
    """A short link for `url`, or the original when shortening is unavailable.

    Never raises: the caller is mid-message-render and a dead shortener must
    degrade to the plain link, not kill the send.
    """
    url = str(url or "").strip()
    if not url.startswith(("http://", "https://")):
        return url
    cfg = cfg or {}
    chain = _chain(cfg)
    if not chain:
        return url
    cache_key = f"{chain[0]}|{url}"
    with _LOCK:
        cache = _load_cache()
        if cache_key in cache:
            return cache[cache_key]
    import time as _time
    for name in chain:
        blocked_at = _PROVIDER_BLOCKED.get(name)
        if blocked_at and (_time.time() - blocked_at) < _PROVIDER_COOLDOWN:
            continue   # known-dead provider — do not pay its timeout again
        try:
            short = _PROVIDERS[name](url, cfg)
        except Exception:
            _PROVIDER_BLOCKED[name] = _time.time()
            continue
        with _LOCK:
            cache = _load_cache()
            cache[cache_key] = short
            _save_cache()
        return short
    return url
