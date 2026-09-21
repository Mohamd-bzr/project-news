#!/usr/bin/env python3
"""
News Engine — Parallel scraper with validation, translation & dedup
===================================================================
Pipeline per cycle:

    fetch (parallel, social sources serialized)  →  normalize
      →  attribute real publisher (Google News)  →  drop >72h old
      →  validate / score credibility  →  dedupe  →  translate to Persian

Every article carries both the English original title and a Persian
translation (`title_fa`, `summary_fa`) so the UI can show Persian while the
research report keeps English (as requested).
"""

import json
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

from sources import (SOURCES, MAX_ARTICLES_PER_FEED, MAX_AGE_HOURS, TOPICS,
                     MIN_CREDIBILITY, make_id, classify_topic, detect_assets,
                     validate_article, SPONSORED_MARKERS, publisher_trust,
                     is_relevant)
from translate import translate_many, save_cache

# ---------------------------------------------------------------------------
# FEED OVERRIDES — when deep recovery finds the variant that actually works
# (alternate URL, mirror, or a whitelisted bot UA), it is remembered here so
# every future cycle — and every restart — keeps the feed alive instead of
# re-breaking it with the original dead config.
# ---------------------------------------------------------------------------
_OVERRIDE_FILE = Path(__file__).with_name(".feed_overrides.json")
_OVERRIDES = {}


def _load_overrides():
    global _OVERRIDES
    try:
        if _OVERRIDE_FILE.exists():
            _OVERRIDES = json.loads(_OVERRIDE_FILE.read_text("utf-8"))
    except Exception:
        _OVERRIDES = {}


def _save_overrides():
    try:
        _OVERRIDE_FILE.write_text(
            json.dumps(_OVERRIDES, ensure_ascii=False, indent=1), "utf-8")
    except Exception:
        pass


def _remember_override(key: str, src2: dict, kw: dict):
    """Persist the winning variant. Relay URLs (proxies/wayback) are throttled
    by design so only their UA hint is kept; URL rewrites and search mirrors
    are kept as the feed's new address (mirrors get kind='search' so the
    ' - Publisher' suffix in titles is handled)."""
    url = src2.get("rss") or ""
    ov = {}
    if any(h in url for h in ("allorigins", "codetabs", "corsproxy",
                              "archive.org", "web.archive.org")):
        if kw.get("ua"):
            ov["ua"] = kw["ua"]
    elif url:
        ov["rss"] = url
        if "news.google.com/rss" in url or "bing.com/news" in url:
            ov["kind"] = "search"
        if kw.get("ua"):
            ov["ua"] = kw["ua"]
    if ov:
        _OVERRIDES[key] = ov
        _save_overrides()


_load_overrides()

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/128.0.0.0 Safari/537.36"),
    "Accept": "application/rss+xml, application/xml, text/xml, text/html, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    safe = str(msg).encode("ascii", "replace").decode("ascii")
    print(f"[{ts}] {safe}", flush=True)


# ---------------------------------------------------------------------------
# normalization helpers
# ---------------------------------------------------------------------------

def _clean_html(raw: str, limit: int = 900) -> str:
    if not raw:
        return ""
    try:
        txt = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    except Exception:
        txt = re.sub(r"<[^>]+>", " ", raw)
    txt = re.sub(r"\s+", " ", txt).strip()
    for junk in ("The post", "appeared first on", "Continue reading", "Read more"):
        idx = txt.find(junk)
        if idx > 0:
            txt = txt[:idx].strip()
    return txt[:limit].strip()


def _parse_date(entry):
    for field in ("published_parsed", "updated_parsed"):
        st = entry.get(field)
        if st:
            try:
                return datetime(*st[:6], tzinfo=timezone.utc).timestamp()
            except Exception:
                pass
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw).timestamp()
            except Exception:
                pass
    return None


def _entry_publisher(entry) -> str:
    """Google News / aggregator feeds name the real outlet in <source>."""
    try:
        src = entry.get("source")
        if src:
            title = src.get("title") if hasattr(src, "get") else None
            if title:
                return str(title).strip()
    except Exception:
        pass
    try:
        return str(entry.get("author_detail", {}).get("name") or "").strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# og:image fallback — feeds that ship no media (U.Today, CoinGape, ForexLive,
# WSJ, Kitco, ...): fetch the article page once and read its og:image.
# Cached per URL for the process lifetime; capped to a per-cycle budget so a
# boot cycle stays fast; never raises, returns '' on failure.
# ---------------------------------------------------------------------------
_OG_CACHE = {}
_OG_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"),
    "Accept-Language": "en-US,en;q=0.9",
}


def _og_image_fallback(link: str) -> str:
    if not link or not link.startswith(("http://", "https://")):
        return ""
    if link in _OG_CACHE:
        return _OG_CACHE[link]
    img = ""
    try:
        r = requests.get(link, headers={**_OG_HEADERS, "Referer": link.split("/")[2]},
                         timeout=6, allow_redirects=True)
        if r.status_code == 200:
            m = (re.search(r'property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)', r.text)
                 or re.search(r'name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)', r.text))
            if m:
                u = m.group(1).strip()
                if u.startswith(("http://", "https://")):
                    img = u
    except Exception:
        pass
    _OG_CACHE[link] = img
    return img


def _entry_image(entry) -> str:
    """Best-effort thumbnail from RSS media fields. Returns '' when absent.
    Checked in order: media:content (media:image), media:thumbnail,
    enclosures, inline <img> in the summary HTML."""
    try:
        mc = entry.get("media_content") or []
        for m in mc:
            if isinstance(m, dict) and (m.get("url") or "").startswith(("http://", "https://")):
                t = str(m.get("type") or "")
                if not t or t.startswith("image"):
                    return m["url"]
        mt = entry.get("media_thumbnail") or []
        for m in mt:
            if isinstance(m, dict) and (m.get("url") or "").startswith(("http://", "https://")):
                return m["url"]
        for enc in entry.get("enclosures") or []:
            if isinstance(enc, dict) and str(enc.get("type") or "").startswith("image"):
                u = str(enc.get("href") or "")
                if u.startswith(("http://", "https://")):
                    return u
        img = re.search(r'<img[^>]+src=["\']([^"\']+)', entry.get("summary") or "")
        if img and img.group(1).startswith(("http://", "https://")):
            return img.group(1)
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# single-feed fetch
# ---------------------------------------------------------------------------

# ── DL2: per-source circuit breaker ─────────────────────────────────────────
# A feed that fails several cycles in a row is parked for a growing cooldown
# instead of walking the entire recovery ladder on every single cycle. The
# state lives in memory (one process, one writer) and resets on success.
_FAILS = {}
_CIRCUIT_N = 4            # consecutive failed cycles before the breaker opens
_CIRCUIT_BASE = 900.0     # first cooldown: 15 minutes
_CIRCUIT_MAX = 6 * 3600.0
_COND = {}                # key -> {etag, modified, count} for conditional GETs


def _fetch_one(key: str, src: dict) -> tuple:
    """Fetch one feed through the multi-path recovery ladder. Never raises.
    Returns (key, [articles], status) — status carries the *reason* it broke
    and every recovery attempt that was made, for the monitoring panel."""
    parked = _FAILS.get(key)
    if parked and parked.get("open_until", 0.0) > time.time():
        return key, [], {
            "key": key, "ok": False, "count": 0, "recovered": False, "recovery": [],
            "reason": "circuit_open", "http": None, "at": time.time(),
            "error": ("circuit open — skipped after %d failed cycles (retry in %d min)"
                      % (parked.get("n", 0), int((parked["open_until"] - time.time()) / 60))),
        }
    arts, status = _fetch_attempt(key, src)
    if status["ok"]:
        _FAILS.pop(key, None)          # healthy again — close the breaker
        return key, arts, status

    diag = status
    ladder = []

    # rate-limited → back off briefly, then the reader/bot UAs that Reddit &
    # friends whitelist (these are what deep recovery usually wins with)
    if diag.get("http") in (429, 503) or diag.get("reason") == "rate_limited":
        time.sleep(4.0)
        arts2, st2 = _fetch_attempt(key, src)
        ladder.append("backoff-4s")
        if st2["ok"]:
            st2["recovered"] = True; st2["recovery"] = ladder
            return key, arts2, st2
        ladder.append(f"fail({st2.get('reason')})")
        for label, ua in (("feedfetcher", DEEP_UAS[10][1]),
                          ("telegrambot", DEEP_UAS[13][1])):
            arts2, st2 = _fetch_attempt(key, src, ua=ua)
            ladder.append(label)
            if st2["ok"]:
                st2["recovered"] = True; st2["recovery"] = ladder
                return key, arts2, st2

    # bot-block (403) → retry with plain feed readers first
    if diag.get("http") in (401, 403, 418) or diag.get("reason") in ("bot_blocked", "auth_required"):
        for label, ua in (("feedreader", "Feedly/1.0 (+https://feedly.com)"),
                          ("inoreader", "inoreader.com RSS reader")):
            arts2, st2 = _fetch_attempt(key, src, ua=ua)
            ladder.append(label)
            if st2["ok"]:
                st2["recovered"] = True; st2["recovery"] = ladder
                return key, arts2, st2

    # SSL problem → re-fetch trusting only this hop (older chains fail urllib/CA)
    if diag.get("reason") == "ssl_error":
        arts2, st2 = _fetch_attempt(key, src, insecure=True)
        ladder.append("ssl-lenient")
        if st2["ok"]:
            st2["recovered"] = True; st2["recovery"] = ladder
            return key, arts2, st2

    # dead URL (404/empty) → same-publisher Google News mirror as a lifeline
    if diag.get("reason") in ("not_found", "empty_feed"):
        arts2, st2 = _fetch_attempt(key, {**src, "rss": _mirror_url(src)}, ua=None)
        ladder.append("gn-mirror")
        if st2["ok"]:
            st2["recovered"] = True; st2["recovery"] = ladder
            st2["mirror"] = True
            return key, arts2, st2

    # generic failure → one plain retry with googlebot UA as the last resort
    arts2, st2 = _fetch_attempt(key, src,
                                ua="Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)")
    ladder.append("googlebot-UA")
    if st2["ok"]:
        st2["recovered"] = True; st2["recovery"] = ladder
        return key, arts2, st2

    status["recovered"] = False
    status["recovery"] = ladder
    entry = _FAILS.setdefault(key, {"n": 0, "open_until": 0.0})
    entry["n"] = entry.get("n", 0) + 1
    if entry["n"] >= _CIRCUIT_N:
        cooldown = min(_CIRCUIT_MAX, _CIRCUIT_BASE * (2 ** (entry["n"] - _CIRCUIT_N)))
        entry["open_until"] = time.time() + cooldown
    return key, arts, status


def _mirror_url(src: dict) -> str:
    """site-restricted Google News feed for a dead publisher RSS.
    Keeps the outlet in the pipeline while its own feed is broken."""
    from urllib.parse import quote_plus
    import re as _re
    host = ""
    m = _re.search(r"https?://([^/]+)/", src.get("rss") or "")
    if m:
        host = _re.sub(r"^www\.", "", m.group(1))
    q = f"when:48h site:{host}" if host else (src.get("name") or "news")
    return f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-US"


# ---------------------------------------------------------------------------
# DEEP RECOVERY — the manual "Recover all broken feeds" button tries every
# plausible way (60+ distinct attempts) to bring a dead feed back, then falls
# back to search-engine mirrors. Ordered cheap→expensive; stops at first hit.
# ---------------------------------------------------------------------------

DEEP_UAS = [
    ("chrome-win",      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    ("chrome-mac",      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    ("firefox",         "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0"),
    ("safari",          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"),
    ("edge",            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0"),
    ("googlebot-d",     "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("googlebot-m",     "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5 Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
    ("bingbot",         "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"),
    ("feedly",          "Feedly/1.0 (+https://feedly.com)"),
    ("inoreader",       "inoreader.com RSS reader"),
    ("feedfetcher",     "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)"),
    ("newsblur",        "NewsBlur/1.0 (http://www.newsblur.com)"),
    ("curl",            "curl/8.5.0"),
    ("telegrambot",     "TelegramBot (like TwitterBot)"),
]

DEEP_REFERERS = [
    ("ref-google",   "https://www.google.com/"),
    ("ref-gnews",    "https://news.google.com/"),
    ("ref-bing",     "https://www.bing.com/"),
    ("ref-facebook", "https://www.facebook.com/"),
    ("ref-tco",      "https://t.co/"),
    ("ref-linkedin", "https://www.linkedin.com/"),
]


def _feed_url_variants(src: dict) -> list[tuple[str, str]]:
    """(label, url) rewrites of the feed URL itself."""
    base = src.get("rss") or ""
    out = []
    if base.startswith("https://"):
        http = base.replace("https://", "http://", 1)
        out.append(("http-down", http))
        out.append(("http+nowww", http.replace("www.", "", 1)))
    if "//www." in base:
        out.append(("strip-www", base.replace("//www.", "//", 1)))
    else:
        out.append(("add-www", base.replace("//", "//www.", 1)))
    for suffix in ("/feed", "/rss", "/atom", "/rss.xml", "/feed/", "/feeds",
                   "/index.xml", "/feed/rss"):
        out.append(("path" + suffix.replace("/", "-"), base.rstrip("/") + suffix))
    out.append(("fmt-xml", base + ("&" if "?" in base else "?") + "format=xml"))
    return out


def _proxy_feed_urls(src: dict) -> list[tuple[str, str]]:
    from urllib.parse import quote_plus as _q
    u = src.get("rss") or ""
    return [
        ("proxy-allorigins", f"https://api.allorigins.win/raw?url={_q(u)}"),
        ("proxy-codetabs",   f"https://api.codetabs.com/v1/proxy?quest={_q(u)}"),
        ("proxy-corsproxy",  f"https://corsproxy.io/?url={_q(u)}"),
    ]


def _wayback_feed_urls(src: dict) -> list[tuple[str, str]]:
    """Latest archived snapshot of the feed via the Wayback availability API."""
    u = src.get("rss") or ""
    try:
        r = requests.get("https://archive.org/wayback/available",
                         params={"url": u}, timeout=8)
        snap = ((r.json() or {}).get("archived_snapshots") or {}).get("closest") or {}
        if snap.get("url"):
            return [("wayback-snap", snap["url"])]
    except Exception:
        pass
    return []


def _mirror_feed_urls(src: dict) -> list[tuple[str, str]]:
    """Search-engine RSS mirrors — same publisher, different pipe."""
    from urllib.parse import quote_plus as _q
    import re as _re
    host = ""
    m = _re.search(r"https?://([^/]+)/", src.get("rss") or "")
    if m:
        host = _re.sub(r"^www\.", "", m.group(1))
    name = src.get("name") or "news"
    urls = []
    if host:
        for when in ("", " when:24h", " when:7d", " when:30d"):
            urls.append((f"gn-site{when.strip().replace(' ', '-').replace(':', '') or '-all'}",
                         f"https://news.google.com/rss/search?q={_q('site:' + host + when)}&hl=en-US"))
        urls.append(("bing-site", f"https://www.bing.com/news/search?q={_q('site:' + host)}&format=RSS"))
    urls.append(("gn-name", f"https://news.google.com/rss/search?q={_q(name)}&hl=en-US"))
    urls.append(("gn-name-7d", f"https://news.google.com/rss/search?q={_q(name + ' when:7d')}&hl=en-US"))
    urls.append(("bing-name", f"https://www.bing.com/news/search?q={_q(name)}&format=RSS"))
    return urls


def deep_recover(key: str, src: dict, on_progress=None,
                 wall_budget: float = 430.0) -> tuple:
    """Exhaustive per-feed recovery: 60+ distinct attempts, ordered cheap to
    expensive. Returns (key, [articles], status). status carries every attempt
    label that was tried, how many ways were used, and how it ended."""
    t0 = time.monotonic()
    tried = []
    attempts_total = 0
    budget_hit = False

    def _plan():
        plan = []
        # 1) 14 different user-agents on the exact original URL
        for lbl, ua in DEEP_UAS:
            plan.append((lbl, src, {"ua": ua}))
        # 2) browser UA + realistic referers (some sites allow referrer traffic)
        for lbl, ref in DEEP_REFERERS:
            plan.append((lbl, src, {"ua": DEEP_UAS[0][1],
                                    "extra": {"Referer": ref}}))
        # 3) SSL-lenient fetches (broken publisher cert chains)
        for lbl, ua in (("ssl-lenient", None), ("ssl-chrome", DEEP_UAS[0][1]),
                        ("ssl-gbot", DEEP_UAS[5][1]), ("ssl-feedly", DEEP_UAS[8][1])):
            plan.append((lbl, src, {"ua": ua, "insecure": True}))
        # 4) URL rewrites: http downgrade, www toggle, common feed paths
        for lbl, u in _feed_url_variants(src):
            plan.append((lbl, {**src, "rss": u}, {"ua": DEEP_UAS[0][1]}))
        # 5) XML-preserving third-party proxies (beat IP blocks)
        for lbl, u in _proxy_feed_urls(src):
            plan.append((lbl, {**src, "rss": u}, {"ua": DEEP_UAS[0][1]}))
            plan.append((lbl + "+gbot", {**src, "rss": u}, {"ua": DEEP_UAS[5][1]}))
        # 6) Wayback Machine snapshot of the feed
        for lbl, u in _wayback_feed_urls(src):
            plan.append((lbl, {**src, "rss": u}, {"ua": DEEP_UAS[0][1]}))
        # 7) search-engine mirrors (Google News / Bing News RSS)
        for lbl, u in _mirror_feed_urls(src):
            plan.append((lbl, {**src, "rss": u}, {"ua": DEEP_UAS[0][1]}))
        # 8) patient retries — throttled servers usually reopen
        for delay in (3, 8, 15):
            plan.append((f"backoff-{delay}s", src, {"ua": None, "sleep": delay}))
        return plan

    plan = _plan()
    fixed = None
    for lbl, src2, kw in plan:
        if time.monotonic() - t0 > wall_budget:
            budget_hit = True
            tried.append(f"⏱ budget-stop ({lbl} skipped)")
            break
        if kw.get("sleep"):
            time.sleep(kw["sleep"])
        attempts_total += 1
        tried.append(lbl)
        if on_progress:
            try:
                on_progress(key, attempts_total, len(plan), lbl)
            except Exception:
                pass
        try:
            arts2, st2 = _fetch_attempt(key, src2, ua=kw.get("ua"),
                                        insecure=kw.get("insecure", False),
                                        timeout=7, extra_headers=kw.get("extra"))
            if st2.get("ok"):
                fixed = st2
                fixed["recovered"] = True
                fixed["recovery"] = tried
                fixed["ways"] = attempts_total
                _remember_override(key, src2, kw)
                wurl = (src2.get("rss") or "")
                if "news.google.com/rss" in wurl or "bing.com/news" in wurl:
                    fixed["mirror"] = True
                return key, arts2, fixed
        except Exception:
            pass

    st = {"key": key, "ok": False, "count": 0, "recovered": False,
          "recovery": tried, "ways": attempts_total,
          "error": (f"exhausted recovery — {attempts_total} ways tried"
                    + (" (time budget hit)" if budget_hit else "")),
          "reason": "exception", "at": time.time()}
    return key, [], st



def _classify_failure(http=None, exc=None, entries=0):
    """Turn a raw failure into a stable machine reason + English detail."""
    if exc is not None:
        s = f"{type(exc).__name__}: {exc}".lower()
        if "ssl" in s or "certificate" in s or "cert" in s:
            return "ssl_error", str(exc)
        if "timeout" in s or "timed out" in s:
            return "timeout", str(exc)
        if "connection" in s or "getaddrinfo" in s or "name or service" in s or "failed to resolve" in s:
            return "dns_or_network", str(exc)
        if "too many redirects" in s:
            return "redirect_loop", str(exc)
        return "exception", f"{type(exc).__name__}: {exc}"
    if http is not None:
        if http in (401,):
            return "auth_required", f"HTTP {http} — feed requires auth"
        if http in (403, 418):
            return "bot_blocked", f"HTTP {http} — bot/reader blocked"
        if http == 404:
            return "not_found", "HTTP 404 — feed URL gone"
        if http == 429:
            return "rate_limited", "HTTP 429 — rate limited (too many requests)"
        if http in (500, 502, 503, 504):
            return "server_error", f"HTTP {http} — server problem on their side"
        if http != 200:
            return "http_error", f"HTTP {http}"
    if not entries:
        return "empty_feed", "feed is alive but returned 0 items"
    return None, None


def _fetch_attempt(key: str, src: dict, ua: str | None = None,
                   insecure: bool = False, timeout: int = 15,
                   extra_headers: dict | None = None) -> tuple:
    """One real attempt at fetching a feed, with failure diagnosis."""
    arts = []
    status = {"key": key, "ok": False, "count": 0, "error": None,
              "reason": None, "reason_fa": None, "http": None, "at": time.time()}
    # a variant that deep recovery previously WON with beats the raw config —
    # but only when the caller did NOT explicitly pass a different variant
    # (deep recovery always probes the full ladder from scratch)
    ov = _OVERRIDES.get(key) or {}
    if ua is None and ov.get("ua"):
        ua = ov["ua"]
    reg_rss = (SOURCES.get(key) or {}).get("rss")
    src_rss, ov_rss = src.get("rss"), ov.get("rss")
    use_ov = bool(ov_rss) and (not src_rss or src_rss == reg_rss)
    if use_ov:
        eff_src = {**src, **{k: v for k, v in ov.items() if k != "ua"}}
        rss_url = ov_rss
    else:
        eff_src = src
        rss_url = src_rss or ov_rss or ""
    headers = dict(HEADERS)
    if ua:
        headers["User-Agent"] = ua
    if extra_headers:
        headers.update(extra_headers)
    try:
        # requests first — its bundled CA store handles sites whose cert
        # chain breaks urllib's (zycrypto, thecryptobasic, ...). Raw
        # feedparser.parse(url) stays as the fallback path.
        try:
            if insecure:
                import urllib3
                urllib3.disable_warnings()
            # ── DL2: conditional request. Publishers that honour ETag/Last-Modified
            # answer 304 (a few hundred bytes) instead of re-sending the whole feed;
            # with ~106 feeds per cycle this is the cheapest cycle-time win there is.
            cond = _COND.get(key) or {}
            if cond.get("etag"):
                headers["If-None-Match"] = cond["etag"]
            if cond.get("modified"):
                headers["If-Modified-Since"] = cond["modified"]
            resp = requests.get(rss_url or src["rss"], headers=headers, timeout=timeout,
                                verify=not insecure, allow_redirects=True)
            if resp.status_code == 304 and cond.get("count"):
                status.update({"ok": True, "count": cond["count"],
                               "not_modified": True, "reason": None, "http": 304})
                return [], status
            resp.raise_for_status()
            _COND[key] = {
                "etag": resp.headers.get("ETag") or cond.get("etag"),
                "modified": resp.headers.get("Last-Modified") or cond.get("modified"),
                "count": cond.get("count") or 0,
            }
            feed = feedparser.parse(resp.text)
        except Exception as ex:
            reason, detail = _classify_failure(exc=ex)
            # HTTP-level errors (403/404/5xx) are final — the feedparser
            # fallback would hit the SAME status and can block for minutes
            # (urllib has no default timeout). A dead-slow server (timeout)
            # is equally futile to re-try through urllib. Transport errors
            # where the fallback sometimes gets through: DNS / redirects:
            futile = ("ssl_error", "timeout", "exception")
            http_level = isinstance(ex, requests.exceptions.HTTPError) \
                or getattr(ex, "status", None)
            if reason not in futile and not http_level:
                import socket
                socket.setdefaulttimeout(12)   # guards feedparser's own fetch
                feed = feedparser.parse(rss_url, agent=headers["User-Agent"],
                                        request_headers=headers)
            else:
                raise
        status["http"] = getattr(feed, "status", None) or status["http"]
        entries = (feed.entries or [])[:MAX_ARTICLES_PER_FEED + 8]
        _og_budget = [12]     # max og:image page fetches per feed per cycle
        for e in entries:
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            if not title or not link:
                continue

            publisher = ""
            if src.get("kind") == "search":
                publisher = _entry_publisher(e)
                # Google News titles end with " - Publisher"
                if publisher and title.endswith(publisher):
                    title = title[: -len(publisher)].rstrip(" -–—|").strip()

            raw_summary = e.get("summary") or e.get("description") or ""
            if not raw_summary and e.get("content"):
                try:
                    raw_summary = e["content"][0].get("value", "")
                except Exception:
                    raw_summary = ""
            summary = _clean_html(raw_summary)
            # Google News descriptions end with the publisher name too
            if publisher and summary.endswith(publisher):
                summary = summary[: -len(publisher)].strip(" -–—|.").strip()
            pub_ts = _parse_date(e)
            author = (e.get("author") or "").strip()
            if SPONSORED_MARKERS.search(author):
                continue

            trust = src["trust"]
            display_name = src["name"]
            if publisher:
                # score the actual outlet, and display it as the source
                trust = max(trust, publisher_trust(publisher))
                display_name = publisher

            media_img = _entry_image(e)
            # feeds with no media fields: pull og:image from the article page
            # (budget: only for the freshest entries so boot stays fast)
            if not media_img and _og_budget[0] > 0:
                _og_budget[0] -= 1
                media_img = _og_image_fallback(link)
            arts.append({
                "title": re.sub(r"\s+", " ", title),
                "link": link,
                "base_link": link.split("?")[0],
                "summary": summary,
                "published_ts": pub_ts,
                "published_str": (datetime.fromtimestamp(pub_ts, timezone.utc)
                                  .strftime("%Y-%m-%d %H:%M UTC") if pub_ts else ""),
                "author": author,
                "source_key": key,
                "source_name": display_name,
                "source_kind": src.get("kind", "crypto"),
                "source_trust": round(trust, 2),
                "tier": src["tier"],
                "via": src["name"] if publisher else "",
                "image": media_img,
            })
        status["ok"] = bool(arts)
        status["count"] = len(arts)
        if arts and key in _COND:
            _COND[key]["count"] = len(arts)
        if not arts:
            reason, detail = _classify_failure(http=status.get("http"), entries=0)
            status["reason"] = reason
            status["error"] = detail
        else:
            status["reason"] = None
    except Exception as ex:
        reason, detail = _classify_failure(exc=ex, http=status.get("http"))
        status["reason"] = reason
        status["error"] = detail or f"{type(ex).__name__}: {ex}"
        log(f"  x {src['name']}: {type(ex).__name__}")
    return arts, status


# ---------------------------------------------------------------------------
# main entry
# ---------------------------------------------------------------------------

def scrape_all(max_workers: int = 14, now=None, enabled=None, custom=None,
               custom_assets=None, translate: bool = True,
               max_age_hours: float = MAX_AGE_HOURS) -> dict:
    """
    enabled:   set of enabled builtin source keys (None = all)
    custom:    {key: {name, rss, trust}} user-added feeds
    custom_assets: {SYM: {fa, name, keywords, yahoo, coingecko}}
    max_age_hours: hard freshness cutoff — older news is dropped outright
    Returns {"articles": [...], "stats": {...}, "sources": {key: status}}
    """
    from sources import build_custom_patterns
    now = now or datetime.now(timezone.utc)
    custom_patterns = build_custom_patterns(custom_assets or {})

    run_sources = {}
    for k, s in SOURCES.items():
        if enabled is None or k in enabled:
            run_sources[k] = s
    for k, s in (custom or {}).items():
        run_sources[k] = {"name": s.get("name", k), "rss": s["rss"],
                          "trust": s.get("trust", 0.6), "tier": 4,
                          "kind": s.get("kind", "crypto")}

    parallel = {k: s for k, s in run_sources.items() if not s.get("sequential")}
    serial = {k: s for k, s in run_sources.items() if s.get("sequential")}

    log(f"Scraping {len(run_sources)} sources "
        f"({len(parallel)} parallel, {len(serial)} serialized, "
        f"cutoff {max_age_hours:g}h)...")
    t0 = time.time()

    raw, statuses = {}, {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_fetch_one, k, s): k for k, s in parallel.items()}
        for f in as_completed(futs):
            try:
                key, arts, st = f.result()
                statuses[key] = st
                if arts:
                    raw[key] = arts
            except Exception as ex_:
                log(f"  x worker crashed: {ex_}")

    # social sources: politely serialized, Reddit throttles parallel bursts
    for i, (k, s) in enumerate(serial.items()):
        key, arts, st = _fetch_one(k, s)
        statuses[key] = st
        if arts:
            raw[key] = arts
        if i < len(serial) - 1:
            time.sleep(1.6)

    fetched = sum(len(v) for v in raw.values())
    log(f"Fetched {fetched} raw entries from {len(raw)}/{len(run_sources)} feeds "
        f"in {time.time()-t0:.1f}s")

    # ---- normalize + validate + dedupe ----
    articles, rejected, stale, irrelevant = [], 0, 0, 0
    seen_titles, seen_links = set(), set()

    for key, arts in raw.items():
        src = run_sources[key]
        for art in arts:
            th = re.sub(r"[^a-z0-9]", "", art["title"].lower())[:64]
            if th in seen_titles or art["base_link"] in seen_links:
                continue
            seen_titles.add(th)
            seen_links.add(art["base_link"])

            verdict = validate_article(art, art.get("source_trust", src["trust"]),
                                       now=now, max_age=max_age_hours)
            if not verdict["valid"]:
                rejected += 1
                if "stale" in verdict["reasons"]:
                    stale += 1
                continue
            if verdict["credibility"] < MIN_CREDIBILITY:
                rejected += 1
                continue

            assets = detect_assets(art["title"], art["summary"], custom_patterns)
            if not is_relevant(assets, art["title"], art["summary"]):
                irrelevant += 1
                continue
            topic = classify_topic(art["title"], art["summary"])
            art.update({
                "id": make_id(art["title"], art["link"]),
                "assets": assets,
                "topic": topic,
                "topic_fa": TOPICS[topic]["fa"],
                "topic_icon": TOPICS[topic]["icon"],
                "credibility": verdict["credibility"],
                "flags": verdict["reasons"],
                "age_hours": (round((now.timestamp() - art["published_ts"]) / 3600, 1)
                              if art["published_ts"] else None),
                "title_fa": "",
                "summary_fa": "",
            })
            articles.append(art)

    articles.sort(key=lambda a: (-(a["published_ts"] or 0), -a["credibility"]))

    # ---- Persian translation (cached; failure keeps the English text) ----
    if translate and articles:
        t1 = time.time()
        texts = []
        for a in articles:
            texts.append(a["title"])
            if len(a.get("summary") or "") >= 40:
                texts.append(a["summary"][:400])
        try:
            table = translate_many(texts)
            hit = 0
            for a in articles:
                fa = table.get(a["title"])
                if fa:
                    a["title_fa"] = fa
                    hit += 1
                summ = a.get("summary") or ""
                if summ and len(summ) >= 40:
                    a["summary_fa"] = table.get(summ[:400], "")
            save_cache()
            log(f"Translated {hit}/{len(articles)} titles to Persian "
                f"in {time.time()-t1:.1f}s")
        except Exception as ex:
            log(f"  x translation failed (non-fatal): {ex}")

    ok_feeds = sum(1 for s in statuses.values() if s["ok"])
    log(f"Validated {len(articles)} articles in the last {max_age_hours:g}h "
        f"(scored out {rejected}, of which {stale} stale; "
        f"off-topic skipped {irrelevant}) from {ok_feeds} feeds")

    return {
        "articles": articles,
        "sources": statuses,
        "stats": {
            "total": len(articles),
            "rejected": rejected,
            "stale_rejected": stale,
            "irrelevant": irrelevant,
            "raw_fetched": fetched,
            "feeds_ok": ok_feeds,
            "feeds_total": len(run_sources),
            "duration_s": round(time.time() - t0, 1),
            "last_update": now.isoformat(),
            "max_age_hours": max_age_hours,
        },
    }


if __name__ == "__main__":
    data = scrape_all()
    from collections import Counter
    print("\nTop sources:", Counter(a["source_name"] for a in data["articles"]).most_common(12))
    print("Kinds:", dict(Counter(a["source_kind"] for a in data["articles"])))
    print("Topics:", dict(Counter(a["topic"] for a in data["articles"])))
    print("Assets:", dict(Counter(x for a in data["articles"] for x in a["assets"])))
    fa = sum(1 for a in data["articles"] if a["title_fa"])
    print(f"Persian titles: {fa}/{len(data['articles'])}")
    for a in data["articles"][:5]:
        print(f"  [{a['source_name']}] {a['title_fa'] or a['title']}")
