#!/usr/bin/env python3
"""
News Dashboard — Flask backend
==============================
Ties the whole pipeline together:

  cycle (every 30 min by default):
      scrape 71+ free sources  →  drop >72h old  →  validate & score
        →  translate titles/summaries to Persian  →  market data
        →  institutional reports (English) with Persian citations

  • JSON APIs for the SPA frontend
  • Persian RTL dashboard (dark, clean) served from dashboard_html.py

Run:   python app.py [--port 5055] [--once]
"""

import base64
import json
import atexit
import logging
import os
import queue
import re
import signal
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path

import psutil
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, redirect, request, Response, send_file

from logging_config import setup_logging, get_logger
setup_logging(log_dir=str(Path(__file__).parent / "logs"), level=logging.INFO)
logger = get_logger('freebuff')

from database import hidden_ids as _hidden_ids
from sources import (SOURCES, ASSETS, TOPICS, TOPIC_ORDER, KIND_LABELS,
                     MAX_AGE_HOURS, REPORT_MIN_CREDIBILITY, PUBLISHER_TRUST)
from collections import deque
from scraper import scrape_all, _fetch_one, deep_recover
from market_data import fetch_market_data, yahoo_candidates
from calendar_data import market_context, _macro_quotes, _fng, market_sessions
from tv_ideas import (fetch_ideas, fetch_asset as fetch_idea_asset, find_idea,
                      ideas_page_url, sort_items, filter_items, TAG_BY_ASSET)
from report_generator import build_all_reports, build_report
from indicators import chart_payload
from translate import (translate_many, translate_one, translate_paragraphs,
                       cache_stats, save_cache)
from fa_format import fa_datetime, fa_date, fa_time, fa_ago, fa_digits
from dashboard_html import APP_HTML
from news_intelligence import (
    dedup_articles, record_news_events, update_correlation_prices,
    get_intelligence_summary, _anomaly
)
from middleware import require_tier

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "settings.json"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

TG_TEMPLATE_DEFAULT = ("{market_emoji} <b>{title}</b>\n\n"
                       "{summary_fa}"
                       "{key_point}"
                       "📰 {source} · ⭐ {cred}% · 🕒 {time_fa}\n"
                       "{link_line}")

BALE_TEMPLATE_DEFAULT = ("{market_emoji} **{title}**\n\n"
                         "{summary_fa}"
                         "{key_point}"
                         "📰 {source} · ⭐ {cred}% · 🕒 {time_fa}\n"
                         "{link_line}")

DEFAULT_CONFIG = {
    "interval": 1800,                 # 30 minutes
    "assets": list(ASSETS.keys()),
    "custom_assets": {},              # SYM -> {fa, name, icon, yahoo, coingecko, keywords}
    "auto_reports": True,
    "sources_enabled": {k: True for k in SOURCES},
    "custom_sources": {},             # key -> {name, rss, trust}
    "report_max_age_hours": 24,      # default news window (24h) — selectable in settings
    # News hygiene (settings tab). Social feeds are Reddit-style sentiment posts
    # and the short ones are mostly stubs ("$BTC to the moon"); both pollute a
    # feed that is meant to be readable analysis.
    "news_min_chars": 120,           # title+summary shorter than this never enters
    "news_hide_social": False,
    # Social popularity gate (2026-09-28): Reddit RSS carries no score field,
    # so live upvote counts come from the arctic-shift archive (reddit_scores.py)
    # and posts below the minimum are dropped before the feed is built.
    "social_score_filter": False,    # master switch for the whole gate
    "social_score_min": 2000,        # minimum upvotes ("likes") — user default
    "social_comments_min": 0,        # minimum comments (0 = off)
    "telegram": {
        "enabled": False,
        "token": "",
        "chat": "",
        "min_credibility": 0.70,
        "max_items": 10,
        "max_age_hours": 24,
        "language": "fa",
        "include_link": True,
        "link_on_own_line": False,
        "include_summary": True,
        "hashtags": True,
        "emoji": True,
        "show_stars": True,
        "silent": False,
        "pin": False,
        "quiet_hours": True,
        "template": TG_TEMPLATE_DEFAULT,
    },
    "bale": {
        "enabled": False,
        "token": "",
        "chat": "",
        "min_credibility": 0.70,
        "max_items": 10,
        "max_age_hours": 24,
        "language": "fa",
        "include_link": True,
        "link_on_own_line": False,
        "include_summary": True,
        "hashtags": True,
        "emoji": True,
        "show_stars": True,
        "silent": False,
        "quiet_hours": True,
        "template": BALE_TEMPLATE_DEFAULT,
    },
    "discord": {
        "enabled": False,
        "token": "",
        "channel_id": 0,
        "webhook_url": "",
    },
    "email": {
        "enabled": False,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_pass": "",
        "from_addr": "",
        "to_addrs": [],
        "use_tls": True,
        "send_day": "sunday",
        "send_hour": 8,
    },
    "tv_webhook_secret": "change-me-to-a-random-string",
    # Content studio (tab «استودیو محتوا»). Credibility is a gate, virality a
    # booster: a loud story under the gate never reaches the list.
    "content_studio": {
        "enabled": True,
        "credibility_gate": 0.6,
        "half_life_hours": 6,
        "repeat_penalty": 0.35,
        "repeat_penalty_hours": 48,   # lookback window for "already posted" dedupe
        "min_score": 0,
        "weights": {"credibility": 1.0, "coverage": 0.9, "audience": 1.1,
                    "freshness": 1.0, "youtube": 0.9, "telegram": 1.0, "reddit": 0.5},
        "asset_weights": {"XAU": 1.4, "DXY": 1.3, "BTC": 1.25, "WTI": 1.2,
                          "XAG": 1.1, "ETH": 1.1, "VIX": 1.05},
        "youtube_queries_fa": ["قیمت طلا", "قیمت دلار", "قیمت بیت کوین", "بورس تهران", "قیمت نفت"],
        "youtube_queries_en": ["gold price today", "bitcoin price", "oil price", "fed rate decision"],
        "youtube_channels": [],
        "telegram_channels": ["akhbarefori", "bourse24", "eghtesadonline",
                              "donya_eqtesad", "TehranStockExchange"],
        "reddit_subs": ["wallstreetbets", "CryptoCurrency", "investing", "economics", "gold"],
        "youtube_key": "",              # optional: free Data API key
        "instagram_token": "",          # optional: Graph API token (own account)
        "instagram_user_id": "",
        "auto_post": {"telegram": True, "require_confirm": False},
    },
    "ai": {
        "enabled": False,
        "openai_key": "",
        "openai_model": "gpt-4o-mini",
        "summary_assets": ["BTC", "ETH", "SOL", "XAU"],
        "summary_interval": 3600,
    },
}

# source kinds that count as "social" for the hygiene filter
SOCIAL_KINDS = {"social"}

# Secrets are never shipped to the browser: every config view goes through
# _mask_secrets() and every settings-merge ignores values equal to the mask,
# so a round-tripped form field can never overwrite a stored credential.
_SECRET_MASK = "••••••"

def _mask_secrets(cfg: dict) -> dict:
    """Deep copy of CONFIG with secret values replaced by _SECRET_MASK."""
    out = json.loads(json.dumps(cfg))
    def _m(d, keys):
        if isinstance(d, dict):
            for k in keys:
                if d.get(k):
                    d[k] = _SECRET_MASK
    _m(out.get("telegram"), ("token",))
    _m(out.get("bale"), ("token",))
    _m(out.get("discord"), ("token", "webhook_url"))
    _m(out.get("email"), ("smtp_pass",))
    _m(out.get("content_studio"), ("youtube_key", "instagram_token"))
    _m(out.get("ai"), ("openai_key",))
    if out.get("tv_webhook_secret") and out["tv_webhook_secret"] != "change-me-to-a-random-string":
        out["tv_webhook_secret"] = _SECRET_MASK
    return out

def _is_secret_mask(v) -> bool:
    return isinstance(v, str) and v.strip() == _SECRET_MASK


def apply_news_filter(articles: list) -> tuple[list, int, int]:
    """Drop stubs and (optionally) social posts. Returns (kept, dropped_short,
    dropped_social). Pure, cheap, and applied before anything else touches the
    list so the feed, the counters and the reports all agree."""
    try:
        min_chars = int(CONFIG.get("news_min_chars") or 0)
    except Exception:
        min_chars = 0
    hide_social = bool(CONFIG.get("news_hide_social"))
    if min_chars <= 0 and not hide_social:
        return list(articles or []), 0, 0
    kept, short, social = [], 0, 0
    for a in (articles or []):
        if hide_social and (a.get("source_kind") in SOCIAL_KINDS):
            social += 1
            continue
        if min_chars > 0:
            text = ((a.get("title") or "") + " " + (a.get("summary") or "")).strip()
            if len(text) < min_chars:
                short += 1
                continue
        kept.append(a)
    return kept, short, social

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# Optional network routing / keys (env only, never in the repo)
# ---------------------------------------------------------------------------
# MOHMD_PROXY reroutes *every* rung at once: requests, and therefore also
# curl_cffi and cloudscraper inside news_bypass, honour the standard proxy
# environment variables. This is the one-line fix for hosts that reject this
# machine (IP/ASN level) rather than bots — e.g. investing.com answers 403 with
# a 3-byte body even to a real Chrome TLS fingerprint.
_PROXY = (os.environ.get("MOHMD_PROXY") or "").strip()
if _PROXY:
    for _v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.setdefault(_v, _PROXY)

# r.jina.ai used to be free and unauthenticated; it now answers 401 without a
# key and 403 with a browser UA, which silently killed the strongest rung of
# the extraction ladder. With MOHMD_JINA_KEY set the rung comes back to life.
_JINA_KEY = (os.environ.get("MOHMD_JINA_KEY") or "").strip()
_MOHMD_TOKEN = os.environ.get("MOHMD_TOKEN", "").strip()

# The news window the whole app shares: the scraper's cutoff, the feed and the
# fear/greed gauge. Kept as one pair of numbers so a value accepted by
# /api/settings is always a value load_config keeps.
NEWS_WINDOW_MIN_HOURS = 6
NEWS_WINDOW_MAX_HOURS = 168

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
STATE = {
    "start_time": time.time(),
    "articles": [],
    "archive": [],           # older-than-window items kept for the Archive tab
    "market": {},
    "reports": {},
    "sentiment": {
        "BTC": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "ETH": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "SOL": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "XRP": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "ADA": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "BNB": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "DOGE": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "XAU": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "XAG": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
        "_overall": {"avg_score": 0.0, "positive_count": 0, "negative_count": 0, "neutral_count": 0, "total": 0, "trend": "mixed"},
    },
    "sources_status": {},
    "src_hist": {},          # key -> [1/0 per recent cycle] for health sparklines
    "stats": {
        "start_time": time.time(),
        "shutdown": False,
        "cycle_running": False,
        "cycles_run": 0,
        "last_update": None,
        "last_duration": None,
        "last_success": None,
        "last_error": None,
        "next_cycle_ts": None,
        "cycle_stats": {},
        "total_articles": 0,
        "ok_sources": 0,
        "err_sources": 0,
    },
    "anomalies": [],
    "predictions": {},
    "ai_summaries": {},
}
CONFIG = json.loads(json.dumps(DEFAULT_CONFIG))
STATE_LOCK = threading.Lock()
CYCLE_LOCK = threading.Lock()
CYCLE_EVENT = threading.Event()
_CONTENT_LOCK = threading.Lock()
_FA_CONTENT_LOCK = threading.Lock()
_FA_REPORT_LOCK = threading.Lock()
_CONFIG_LOCK = threading.Lock()
_LIVE_LOCK = threading.Lock()
_last_refresh = [0.0]
_CANDLES_MAX = 200
warming_thread = None

CONTENT_CACHE = {}
FA_CONTENT_CACHE = {}      # article id -> list of Persian paragraphs
FA_REPORT_CACHE = {}
_ART_INFLIGHT = set()      # extraction / translation jobs currently running
# manual deep-recovery job state (the Source Health button polls this)
RECOVERY_JOB = {"running": False, "done": 0, "total": 0, "fixed": 0,
                "attempts": 0, "current": "", "log": [],
                "started": 0, "finished": 0}
_RECOVER_LOCK = threading.Lock()

# Subscriber registry
_sse_subscribers = {}  # id -> queue
_sse_lock = threading.Lock()
_sse_counter = [0]


def _sse_broadcast(event_type, data):
    """Send event to all connected SSE clients."""
    msg = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    dead = []
    with _sse_lock:
        for client_id, q in list(_sse_subscribers.items()):
            if str(client_id).startswith("price_") and event_type != "prices":
                continue
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(client_id)
            except Exception:
                dead.append(client_id)
        for cid in dead:
            _sse_subscribers.pop(cid, None)


# ---------------------------------------------------------------------------
# Server-side push — the other half of the client's StreamManager
# ---------------------------------------------------------------------------
# The dashboard used to be the clock: every open tab polled /api/live on its own
# 15-second timer, and that request is what refreshed the price cache and fanned
# it out to the other tabs. Ten tabs meant ten upstream fetches of the same
# numbers, and a fresh poll always re-rendered the whole ticker.
#
# The clock moves here: while at least one client is attached to the stream,
# prices are refreshed and pushed on a fixed cadence. With nobody attached the
# loop does nothing at all — the quote APIs are free and rate-limited, so an
# idle terminal has to cost nothing.
STREAM_PUSH_SECONDS = max(5.0, float(os.environ.get("MOHMD_PUSH_SECONDS", "12")))
CAL_SCAN_SECONDS = max(15.0, float(os.environ.get("MOHMD_CAL_SCAN_SECONDS", "60")))
CAL_ANNOUNCE_WINDOW = max(300.0, float(os.environ.get("MOHMD_CAL_WINDOW", "1800")))
# a WebSocket needs a server that can upgrade the connection. Werkzeug cannot,
# so this deployment pushes over SSE and advertises ws only when a fronting
# proxy is configured to provide one (/api/stream/info is what the client reads).
STREAM_WS_URL = os.environ.get("MOHMD_WS_URL", "").strip()
_CAL_SEEN = {}          # event key -> actual value already announced
_CAL_NEXT = 0.0         # epoch of the next calendar scan


def _cal_key(e):
    """Same shape as the dashboard's own row key (see `e._key` in
    dashboard_html.py): `<epoch>_<title, alphanumerics, 20 chars>`. Sending the
    key the renderer already uses means a release frame can be dropped straight
    onto its row instead of the client searching for it."""
    return "%s_%s" % (e.get("ts") or 0,
                      re.sub(r"[^a-zA-Z0-9]", "", str(e.get("title") or ""))[:20])


def cal_scan_and_broadcast(now=None):
    """Announce freshly released indicators on the `calendar` channel.

    Reads the cached bundle only — the monthly/weekly calendar page is fetched
    on a TTL, and a release scanner must not turn that cache into a poll.
    Returns the announced events (also used by the tests, which is why the work
    is a function and not just a loop body).
    """
    now = now or time.time()
    try:
        ctx = market_context() or {}
    except Exception as e:
        logger.error(f"calendar scan: {e}")
        return []
    events = ((ctx.get("calendar") or {}) or {}).get("events") or []
    out = []
    for e in events:
        if not isinstance(e, dict):
            continue
        actual = str(e.get("actual") or "").strip()
        if not actual:
            continue
        key = _cal_key(e)
        prev = _CAL_SEEN.get(key)
        if prev == actual:
            continue
        _CAL_SEEN[key] = actual
        ts = e.get("ts") or 0
        # One announcement per release, and never a burst of history: on the
        # first scan after a restart only releases inside the window go out
        # (otherwise every figure of the past week would flash at once).
        if prev is None and ts and (now - ts) > CAL_ANNOUNCE_WINDOW:
            continue
        item = {k: v for k, v in e.items()
                if k not in ("doc", "doc_fa", "doc_sections", "doc_fa_sections")}
        item["key"] = key
        out.append(item)
    for item in out:
        try:
            _sse_broadcast("calendar", item)
        except Exception:
            pass
    return out


def stream_push_once(now=None):
    """One pass of the pusher. Returns the number of attached clients.

    live_prices() is left to do the broadcasting itself: it dedupes the upstream
    fetch (LIVE_TTL) and only fans out when it actually refreshed, so two tabs
    never cause two frames.
    """
    global _CAL_NEXT
    now = now or time.time()
    with _sse_lock:
        attached = len(_sse_subscribers)
    if not attached:
        return 0
    try:
        live_prices()
    except Exception as e:
        logger.error(f"stream price push: {e}")
    if now >= _CAL_NEXT:
        _CAL_NEXT = now + CAL_SCAN_SECONDS
        cal_scan_and_broadcast(now)
    return attached


def stream_ticker_loop():
    """The server's clock: push prices while anybody is listening."""
    logger.info(f"stream ticker: prices every {STREAM_PUSH_SECONDS:.0f}s, "
                f"calendar release scan every {CAL_SCAN_SECONDS:.0f}s "
                f"({'ws advertised' if STREAM_WS_URL else 'sse only'})")
    while True:
        if STATE.get("stats", {}).get("shutdown"):
            logger.info("Stream ticker exiting (shutdown)")
            break
        try:
            stream_push_once()
        except Exception as e:
            logger.error(f"stream ticker: {e}")
        time.sleep(STREAM_PUSH_SECONDS)


def load_config():
    global CONFIG
    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            CONFIG.update(saved)
        except Exception as e:
            print(f"[config] load failed: {e}", flush=True)
    for k, v in DEFAULT_CONFIG.items():
        CONFIG.setdefault(k, v)
    # clamp the news window to sane values (24h default — user-selectable).
    # /api/settings clamps to the same band, so an accepted value can no longer
    # be silently reduced on the next restart.
    try:
        CONFIG["report_max_age_hours"] = max(
            NEWS_WINDOW_MIN_HOURS,
            min(NEWS_WINDOW_MAX_HOURS, float(CONFIG.get("report_max_age_hours", 24))))
    except Exception:
        CONFIG["report_max_age_hours"] = 24
    # normalise user-added tickers so Yahoo can resolve them
    for meta in (CONFIG.get("custom_assets") or {}).values():
        if meta.get("yahoo"):
            meta["yahoo"] = str(meta["yahoo"]).strip().upper()
    # never ship a silently empty asset list
    if not CONFIG.get("assets"):
        CONFIG["assets"] = list(ASSETS.keys())
    # make sure every builtin source has an entry
    for k in SOURCES:
        CONFIG["sources_enabled"].setdefault(k, True)
    # an unknown source key (from an older version) must not disable anything
    CONFIG["sources_enabled"] = {k: bool(v) for k, v in CONFIG["sources_enabled"].items()
                                 if k in SOURCES or k in CONFIG["custom_sources"]}
    _init_discord_bot()
    _init_ai_config()


DISCORD_CONFIG = CONFIG.get('discord', {})
_discord_bot = None

def _init_discord_bot():
    global _discord_bot, DISCORD_CONFIG
    DISCORD_CONFIG = CONFIG.get('discord', {})
    if DISCORD_CONFIG.get('enabled'):
        try:
            from integrations.discord_bot import DiscordBot
            _discord_bot = DiscordBot(
                token=DISCORD_CONFIG.get('token'),
                channel_id=DISCORD_CONFIG.get('channel_id'),
                webhook_url=DISCORD_CONFIG.get('webhook_url'),
            )
            log("Discord bot enabled")
        except Exception as e:
            log(f"Discord bot init failed: {e}")
    else:
        _discord_bot = None


def _init_ai_config():
    ai_cfg = CONFIG.get('ai', {})
    key = (ai_cfg.get('openai_key') or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = (ai_cfg.get('base_url') or os.environ.get("OPENAI_BASE_URL") or "").strip()
    if key:
        try:
            from ai_features import _init_openai
            _init_openai(key, ai_cfg.get('openai_model'), base_url=base_url or None)
            provider = "OpenRouter" if (key.startswith("sk-or-") or "openrouter" in base_url.lower()) else "OpenAI"
            log(f"AI client initialized ({provider})")
        except Exception as e:
            log(f"AI init failed: {e}")




def save_config():
    """Write settings.json atomically.

    A crash or a power cut halfway through write_text() left a truncated file,
    and load_config() then swallowed the JSON error and silently started from
    defaults — the whole configuration, not just the edit in flight. Every
    other cache in the project already writes tmp + os.replace; this one did
    not.
    """
    try:
        tmp = CONFIG_FILE.with_suffix(CONFIG_FILE.suffix + ".tmp")
        tmp.write_text(json.dumps(CONFIG, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        os.replace(tmp, CONFIG_FILE)
    except Exception as e:
        print(f"[config] save failed: {e}", flush=True)


def log(msg):
    logger.info(msg)
    ts = datetime.now().strftime("%H:%M:%S")
    safe = str(msg).encode("ascii", "replace").decode("ascii")
    print(f"[{ts}] {safe}", flush=True)


# ---------------------------------------------------------------------------
# asset helpers
# ---------------------------------------------------------------------------

BUILTIN_CRYPTO = {"BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "DOGE"}
BUILTIN_MACRO = {"WTI", "DXY", "SPX", "VIX"}   # tradable-macro assets with reports


def _looks_crypto(sym: str, meta: dict) -> bool:
    """Decide whether a user-added asset is a crypto pair (drives report sections)."""
    if sym in BUILTIN_CRYPTO or meta.get("coingecko"):
        return True
    yahoo = str(meta.get("yahoo") or "").strip().upper().replace("/", "-")
    if yahoo.endswith("USDT") or yahoo.endswith("USDC"):
        return True
    return any(yahoo.endswith(q) for q in ("-USD", "-EUR", "-BTC", "-ETH", "-PERP"))


def all_assets_meta() -> dict:
    """Builtin assets + user-added ones, with the flags the UI needs."""
    out = {}
    for sym, meta in ASSETS.items():
        out[sym] = {**meta, "custom": False, "is_crypto": sym in BUILTIN_CRYPTO}
    for sym, meta in (CONFIG.get("custom_assets") or {}).items():
        out[sym] = {
            "fa": meta.get("fa") or sym,
            "name": meta.get("name") or sym,
            "icon": meta.get("icon") or "★",
            "yahoo": meta.get("yahoo"),
            "coingecko": meta.get("coingecko"),
            "keywords": meta.get("keywords"),
            "custom": True,
            "is_crypto": _looks_crypto(sym, meta),
        }
    return out


def market_maps():
    """Yahoo / CoinGecko symbol maps including the user's custom assets."""
    symbols, cg = {}, {}
    for sym, meta in (CONFIG.get("custom_assets") or {}).items():
        if meta.get("yahoo"):
            symbols[sym] = meta["yahoo"]
        if meta.get("coingecko"):
            cg[sym] = meta["coingecko"]
    return symbols, cg


# ---------------------------------------------------------------------------
# The cycle
# ---------------------------------------------------------------------------

def run_cycle(reason="scheduled"):
    """One full pipeline pass. Serialized by CYCLE_LOCK."""
    global warming_thread
    if not CYCLE_LOCK.acquire(blocking=False):
        log("cycle already running — skip")
        return False
    t0 = time.time()
    with STATE_LOCK:
        STATE["stats"]["cycle_running"] = True
    try:
        log(f"=== cycle start ({reason}) ===")
        meta = all_assets_meta()

        with _CONFIG_LOCK:
            enabled_map = dict(CONFIG["sources_enabled"])
            custom_sources = CONFIG.get("custom_sources")
            custom_assets = CONFIG.get("custom_assets")
            max_age_h = CONFIG.get("report_max_age_hours", MAX_AGE_HOURS)
            score_filter = CONFIG.get("social_score_filter")
            score_min = CONFIG.get("social_score_min", 2000)
            comm_min = CONFIG.get("social_comments_min", 0)
            assets_cfg = list(CONFIG["assets"])
            auto_rep = CONFIG.get("auto_reports", True)

        enabled = {k for k, on in enabled_map.items() if on}
        news = scrape_all(enabled=enabled or None,
                          custom=custom_sources,
                          custom_assets=custom_assets,
                          max_age_hours=max_age_h,
                          social_score_min=(score_min if score_filter else 0),
                          social_comments_min=(comm_min if score_filter else 0),
                          translate=False)   # translated AFTER the feed is published

        # ── news hygiene, before anything reads the list ────────────────────
        _kept, _short, _social = apply_news_filter(news["articles"])
        if _short or _social:
            log(f"[filter] dropped {_short} short, {_social} social of "
                f"{len(news['articles'])} scraped")
        news["articles"] = _kept
        try:
            news["stats"]["filtered_short"] = _short
            news["stats"]["filtered_social"] = _social
        except Exception:
            pass
        _gone = _hidden_ids()
        if _gone:
            news["articles"] = [a for a in news["articles"] if a.get("id") not in _gone]

        want = [s for s in assets_cfg if s in meta]
        for s in BUILTIN_MACRO:            # macro assets always get price + report
            if s not in want:
                want.append(s)
        symbols, cg = market_maps()
        market = fetch_market_data(assets=want, symbols=symbols, coingecko=cg)
        market = {k: v for k, v in market.items() if k in want}

        # ── Publish FIRST ──────────────────────────────────────────────────
        # The feed used to go live only after translation + report building,
        # so every cycle kept the dashboard on the previous snapshot for an
        # extra ~40s. Fresh (still English) news is now visible the moment
        # the scrape lands; the Persian titles fill in on the next poll.
        # (`dur` is measured once, at the end of the cycle — an early copy here
        # was dead: it was overwritten before anything read it.)
        now = time.time()
        with STATE_LOCK:
            prev = {a["id"]: a for a in STATE["articles"] if a.get("id")}
            merged = STATE.get("archive") or []
            seen = {a["id"] for a in merged if a.get("id")}
            def _fingerprint(a) -> tuple:
                """Same story re-published across cycles must not duplicate."""
                import re as _re
                base = (a.get("base_link") or a.get("link") or "").split("?")[0]
                norm = _re.sub(r"[^a-z0-9]", "", (a.get("title") or "").lower())[:90]
                return (base, norm)

            # sanitize: drop duplicates that accumulated before fingerprint dedupe existed
            _san, _seen_ids, _seen_fps = [], set(), set()
            for a in merged:
                aid, fp = a.get("id"), _fingerprint(a)
                if aid in _seen_ids or fp in _seen_fps:
                    continue
                _seen_ids.add(aid); _seen_fps.add(fp)
                _san.append(a)
            merged = _san

            seen_fp = {_fingerprint(a) for a in merged}
            for a in news["articles"]:
                fp = _fingerprint(a)
                if a.get("published_ts") and a.get("published_ts") < now - 3600:
                    if a["id"] not in seen and fp not in seen_fp:
                        merged.append(a); seen.add(a["id"]); seen_fp.add(fp)
            for aid, a in prev.items():          # keep id -> article lookups alive
                fp = _fingerprint(a)
                if aid not in seen and fp not in seen_fp:
                    merged.append(a); seen.add(aid); seen_fp.add(fp)
            del merged[:-1200]
            STATE["archive"] = merged

            # Feeds that answer HTTP 304 (conditional GET) contribute ZERO
            # entries this cycle — their headlines are still fresh, they just
            # were not re-sent. Without this carry-forward they silently fell
            # out of the live feed into the archive and the feed shrank after
            # every other cycle ("news disappears").
            window_sec = float(max_age_h) * 3600.0
            fresh_ids = {a.get("id") for a in news["articles"]}
            fresh_fps = {_fingerprint(a) for a in news["articles"]}
            live = list(news["articles"])
            carried = 0
            for aid, a in prev.items():
                if aid in fresh_ids or _fingerprint(a) in fresh_fps:
                    continue
                if (a.get("published_ts") or 0) < now - window_sec:
                    continue          # already out of the news window
                live.append(a)
                carried += 1
            live.sort(key=lambda x: -(x.get("published_ts") or 0))
            if carried:
                log(f"carried forward {carried} still-fresh headlines "
                    f"from feeds that answered 304/not-modified")

            # Deduplicate
            try:
                live, dup_count = dedup_articles(live)
                if dup_count > 0:
                    log(f"  ↳ {dup_count} duplicate articles removed")
                _anomaly.record_cycle(live)
            except Exception as _ie:
                log(f"[intelligence] dedup error: {_ie}")

            live = [json.loads(json.dumps(a)) for a in live]
            # Publish detached dicts. The cycle keeps working on `live` below
            # (Persian translation, sentiment) without STATE_LOCK, while Flask
            # handlers serialise STATE["articles"] concurrently — handing them
            # the same objects produced half-translated cards and sentiment
            # that changed in the middle of a payload. Both enrichment steps
            # only write top-level scalar keys, so one shallow copy per article
            # is enough here.
            STATE["articles"] = [dict(a) for a in live]
            STATE["market"] = market
            for key, st in (news.get("sources") or {}).items():
                STATE["sources_status"][key] = st
                hist = STATE["src_hist"].setdefault(key, [])
                hist.append(1 if st.get("ok") else 0)
                del hist[:-30]      # keep last 30 cycles for the health sparkline
            STATE["stats"].update({
                "cycles_run": STATE["stats"]["cycles_run"] + 1,
                "last_update": datetime.now(timezone.utc).isoformat(),
                "cycle_stats": news["stats"],
            })
        # Purge only what is genuinely stale — the derived caches (blurbs and
        # reports) and bodies of articles that dropped out of the window. A
        # blind clear() here threw away thousands of completed extractions
        # every 3.5 minutes, which is why the same article kept showing a
        # spinner again and again.
        with STATE_LOCK:
            keep_ids = {a["id"] for a in STATE["articles"] if a.get("id")}
            keep_ids |= {a["id"] for a in (STATE.get("archive") or []) if a.get("id")}
        with _CONTENT_LOCK:
            for _k in list(CONTENT_CACHE):
                if _k.startswith("blurb|") or _k not in keep_ids:
                    CONTENT_CACHE.pop(_k, None)
        with _FA_CONTENT_LOCK:
            for _k in list(FA_CONTENT_CACHE):
                if _k.split("|")[0] not in keep_ids:
                    FA_CONTENT_CACHE.pop(_k, None)

        # ── Persian titles/summaries (disk-cached: only NEW text costs time) ─
        _translate_articles_inplace(live)

        # ── Sentiment analysis & aggregation ──
        try:
            from sentiment import analyze_batch, get_aggregate_sentiment
            live = analyze_batch(live)
            with STATE_LOCK:
                STATE["articles"] = live
                sents = dict(STATE.get("sentiment", {}))
                for sym in ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'BNB', 'DOGE', 'XAU', 'XAG']:
                    sents[sym] = get_aggregate_sentiment(live, symbol=sym)
                sents['_overall'] = get_aggregate_sentiment(live)
                STATE['sentiment'] = sents
        except Exception as _se:
            log(f"[sentiment] analysis failed: {_se}")

        # ── Phase 11: AI features (anomalies, summaries, predictions) ──
        try:
            from ai_features import detect_anomalies, get_ai_summary, get_all_predictions
            anomalies = detect_anomalies(live)
            if anomalies:
                with STATE_LOCK:
                    STATE['anomalies'] = anomalies
                log(f"  ⚠ {len(anomalies)} volume anomalies detected")
                if _discord_bot:
                    try:
                        _discord_bot.send_anomaly_alert(anomalies)
                    except Exception:
                        pass
            
            ai_cfg = CONFIG.get('ai', {})
            if ai_cfg.get('enabled') and ai_cfg.get('openai_key'):
                for sym in ai_cfg.get('summary_assets', ['BTC', 'ETH', 'SOL', 'GOLD']):
                    summary = get_ai_summary(sym, live)
                    if summary:
                        with STATE_LOCK:
                            STATE.setdefault('ai_summaries', {})[sym] = summary
            
            preds = get_all_predictions(live)
            with STATE_LOCK:
                STATE['predictions'] = preds
        except Exception as _aie:
            log(f"  x AI processing error: {_aie}")

        # ── Reports last, so every citation already carries its Persian title ─
        reports = {}
        if auto_rep:
            reports = build_all_reports(market, live, want, meta=meta,
                                        max_age=max_age_h)
            for sym, rep in reports.items():
                try:
                    (REPORTS_DIR / f"{sym}.json").write_text(
                        json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as e:
                    log(f"  x report save failed: {e}")
            with STATE_LOCK:
                STATE["reports"] = reports
        else:
            with STATE_LOCK:
                STATE["reports"] = {}

        dur = round(time.time() - t0, 1)
        try:
            from database import save_articles
            save_articles(live)
        except Exception as _dbe:
            log(f"[db] save failed: {_dbe}")
        try:
            _post_cycle_alerts(news["articles"])
            _studio_autopost(news["articles"])
        except Exception:
            pass
        if _discord_bot:
            try:
                _discord_bot.send_digest(reports, len(live))
            except Exception as e:
                log(f"  x Discord digest failed: {e}")
        # Keep the full-text warm: whatever is new in this cycle gets extracted
        # now, so no reader ever sits in front of a spinner again.
        if warming_thread is not None and warming_thread.is_alive():
            pass  # skip, previous warming still running
        else:
            warming_thread = threading.Thread(target=warm_article_bodies, daemon=True)
            warming_thread.start()
        with STATE_LOCK:
            srcs = STATE["sources_status"]
            ok_cnt = sum(1 for s in srcs.values() if s.get("ok"))
            STATE["stats"].update({
                "cycle_running": False,
                "last_update": datetime.now(timezone.utc).isoformat(),
                "last_success": datetime.now(timezone.utc).isoformat(),
                "last_duration": dur,
                "last_error": None,
                "total_articles": len(live),
                "ok_sources": ok_cnt,
                "err_sources": len(srcs) - ok_cnt,
            })
        log(f"=== cycle done in {dur}s — {news['stats']['total']} new "
            f"({len(live)} live) articles (<{news['stats'].get('max_age_hours')}h), "
            f"{len(market)} assets, {len(reports)} reports ===")
        try:
            _sse_broadcast("update", _get_stream_payload())
        except Exception as _sse_err:
            logger.error(f"SSE cycle broadcast error: {_sse_err}")
        return True
    except Exception as e:
        traceback.print_exc()
        with STATE_LOCK:
            STATE["stats"].update({"cycle_running": False, "last_error": str(e),
                                   "last_duration": round(time.time() - t0, 1)})
        return False
    finally:
        with _CONFIG_LOCK:
            cfg_interval = CONFIG["interval"]
        with STATE_LOCK:
            STATE["stats"]["next_cycle_ts"] = time.time() + cfg_interval
        CYCLE_LOCK.release()


def scheduler_loop():
    while True:
        if STATE.get('stats', {}).get('shutdown'):
            logger.info("Scheduler loop exiting (shutdown)")
            break
        run_cycle("scheduled")
        if STATE.get('stats', {}).get('shutdown'):
            logger.info("Scheduler loop exiting (shutdown)")
            break
        with _CONFIG_LOCK:
            cfg_interval = CONFIG["interval"]
        CYCLE_EVENT.wait(cfg_interval)
        CYCLE_EVENT.clear()


def _translate_articles_inplace(articles):
    """Fill title_fa / summary_fa on the article dicts that are already live in
    STATE. Runs after the feed is published so a slow or unreachable translate
    endpoint can never hold the dashboard back — worst case the cards keep
    their English titles until the next poll."""
    if not articles:
        return
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


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _ser_article(a):
    # .get() everywhere: this serialises whatever the scrapers handed over, and
    # one malformed record (a feed entry without a link, say) used to raise
    # KeyError inside /api/data and take the whole payload down with a 500.
    ts = a.get("published_ts")
    return {
        "id": a.get("id", ""),
        "title": a.get("title", ""),
        "title_fa": a.get("title_fa") or "",
        "summary": (a.get("summary") or "")[:260],
        "summary_fa": (a.get("summary_fa") or "")[:260],
        "link": a.get("link", ""),
        "source": a.get("source_name", ""),
        "source_key": a.get("source_key", ""),
        "source_kind": a.get("source_kind", "crypto"),
        "via": a.get("via", ""),
        "topic": a.get("topic"),
        "topic_fa": a.get("topic_fa"),
        "topic_icon": a.get("topic_icon"),
        "assets": a.get("assets", []),
        "credibility": a.get("credibility", 0.5),
        "age_hours": a.get("age_hours"),
        "age_fa": fa_ago(a.get("age_hours")),
        "published_str": a.get("published_str", ""),
        "published_ts": ts,
        "date_fa": fa_date(ts),
        "time_fa": fa_time(ts),
        "datetime_fa": fa_datetime(ts),
        "reddit_score": a.get("reddit_score"),
        "reddit_comments": a.get("reddit_comments"),
        "author": a.get("author", ""),
        "flags": a.get("flags", []),
        "image": a.get("image") or "",
    }


def _news_window_sec() -> float:
    """The user-selected news window in seconds — one source of truth.

    The feed, the fear/greed gauge and the scraper all use this. `/api/data`
    used to hardcode 24 h in two places, so choosing 72 h in settings changed
    what was scraped but not what the feed showed.
    """
    try:
        hours = float(CONFIG.get("report_max_age_hours") or MAX_AGE_HOURS)
    except (TypeError, ValueError):
        hours = float(MAX_AGE_HOURS)
    return max(1.0, hours) * 3600.0


def all_sources_view():
    out = []
    for key, s in SOURCES.items():
        st = STATE["sources_status"].get(key, {})
        out.append({
            "key": key, "name": s["name"], "url": s["rss"],
            "type": "builtin", "kind": s.get("kind", "crypto"),
            "kind_fa": KIND_LABELS.get(s.get("kind"), "عمومی"),
            "tier": s.get("tier"), "trust": s["trust"],
            "enabled": CONFIG["sources_enabled"].get(key, True),
            "last_count": st.get("count"), "last_ok": st.get("ok"),
            "error": st.get("error"),
        })
    for key, s in CONFIG["custom_sources"].items():
        st = STATE["sources_status"].get(key, {})
        out.append({
            "key": key, "name": s["name"], "url": s["rss"],
            "type": "custom", "kind": "custom", "kind_fa": "منبع دلخواه",
            "tier": 4, "trust": s.get("trust", 0.6), "enabled": True,
            "last_count": st.get("count"), "last_ok": st.get("ok"),
            "error": st.get("error"),
        })
    return out


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)

# flask-compress: the dashboard ships as a ~570 KB single page and /api/data
# is a ~1.7 MB JSON bundle — every poll. gzip drops both ~4x; any client that
# cannot gzip just sends Accept-Encoding without gzip and gets plain bytes.
# SSE (text/event-stream) is not in the default mimetype list — streams stay
# uncompressed, which is exactly right for event streams.
from flask_compress import Compress as _Compress
_Compress(app)
app.config["COMPRESS_MIMETYPES"] = ["text/html", "application/json", "text/css",
                                    "application/javascript", "image/svg+xml"]
app.config["COMPRESS_MIN_SIZE"] = 860


@app.after_request
def _no_store(resp):
    """The dashboard and its JSON must never be served from the browser's cache:
    a heuristically cached /api/data is what makes a feed look like it is stuck on
    old news while fresh cycles are landing. The image proxy keeps its own."""
    p = request.path or ""
    if p.startswith("/api/") and ("image" in p or "proxy" in p):
        return resp
    if p == "/" or p.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


# Paths that keep answering without the shared secret while the gate is armed.
# The first group authenticates itself (an API key or the webhook's own secret).
# The second group is exempt only because the dashboard has no way to send the
# token yet — the page never puts it on a request header or query string — so
# tightening these would lock the operator out of their own dashboard. They are
# reported by /api/health and logged at boot instead of being silently open.
TOKEN_GATE_EXEMPT = (
    "/api/v1/",        # _check_api_key
    "/api/docs",       # spec only
    "/api/admin/keys", # own token check
    "/webhook/",       # own secret
)
TOKEN_GATE_OPEN = (
    "/api/alerts",
    "/api/ai/",
    "/api/billing/",
    "/api/candles/",
)


@app.before_request
def _dl2_token_guard():
    """Optional shared-secret gate — active only when MOHMD_TOKEN is set.
    The dashboard stays open on localhost; on a LAN/internet bind this keeps
    one accidental exposure from turning the feed into a public endpoint."""
    need = os.environ.get("MOHMD_TOKEN", "").strip() or _MOHMD_TOKEN
    if not need:
        return None
    if (request.path.startswith(TOKEN_GATE_EXEMPT)
            or request.path in TOKEN_GATE_EXEMPT
            or request.path.startswith(TOKEN_GATE_OPEN)
            or request.path in TOKEN_GATE_OPEN):
        return None
    if request.path == "/" or request.path.startswith("/api/"):
        auth_hdr = request.headers.get("Authorization", "")
        bearer = auth_hdr.replace("Bearer ", "").strip() if auth_hdr.startswith("Bearer ") else ""
        given = request.args.get("token") or request.headers.get("X-Auth-Token", "") or bearer
        if given != need:
            return Response("unauthorized", status=401)
    return None



@app.route("/")
def index():
    return Response(APP_HTML, mimetype="text/html")


# ---------------------------------------------------------------------------
# PWA assets (web/)
# ---------------------------------------------------------------------------
# Served from disk rather than Flask's static folder, because a service worker
# is scoped to its own directory: /sw.js must sit at the root no matter where
# the files live. These four URLs are the whole offline contract — the shell
# itself is still the Python string in dashboard_html.py.
WEB_DIR = BASE_DIR / "web"
_ICON_FILES = {"icon-192.png", "icon-512.png", "icon-maskable-512.png"}


def _web_response(name, mimetype, cache):
    path = WEB_DIR / name
    if not path.is_file():
        return Response(f"missing web asset: {name}", status=404, mimetype="text/plain")
    resp = send_file(path, mimetype=mimetype, conditional=True)
    resp.headers["Cache-Control"] = cache
    return resp


@app.route("/sw.js")
def pwa_service_worker():
    """The worker must always be revalidated: a cached sw.js is a terminal
    that never receives the next build. `Service-Worker-Allowed` keeps the
    scope at / even if the file is ever served from a subdirectory."""
    resp = _web_response("sw.js", "application/javascript", "no-cache, must-revalidate")
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp


@app.route("/storage-engine.js")
def pwa_storage_engine():
    return _web_response("storage_engine.js", "application/javascript", "no-cache, must-revalidate")


@app.route("/channel.js")
def channel_client():
    """The gold/coin page board's client half — same reasoning as /studio.js."""
    return _web_response("channel.js", "application/javascript", "no-cache, must-revalidate")


@app.route("/manifest.webmanifest")
def pwa_manifest():
    return _web_response("manifest.webmanifest", "application/manifest+json", "no-cache")


_FONT_FILES = {
    "Vazirmatn-var.woff2", "IBMPlexMono-Regular.woff2", "IBMPlexMono-SemiBold.woff2",
    "IBMPlexMono-Bold.woff2", "IBMPlexSans-Regular.woff2", "IBMPlexSans-SemiBold.woff2",
    "IBMPlexSans-Bold.woff2",
}

@app.route("/fonts/<name>")
def pwa_font(name):
    """Self-hosted webfonts (Vazirmatn + IBM Plex, both OFL). The PWA promises
    an offline read — a Google-Fonts link broke exactly that promise: with the
    network down, the whole page fell back to system fonts. Whitelisted names
    and week-long caching, like the icons."""
    if name not in _FONT_FILES:
        return Response("unknown font", status=404, mimetype="text/plain")
    return _web_response(f"fonts/{name}", "font/woff2", "public, max-age=604800")


@app.route("/icons/<name>")
def pwa_icon(name):
    """Whitelisted: the icons are content-addressed by size and never change,
    so they can be cached hard — and the name never reaches the filesystem
    unfiltered."""
    if name not in _ICON_FILES:
        return Response("unknown icon", status=404, mimetype="text/plain")
    return _web_response(f"icons/{name}", "image/png", "public, max-age=604800")


def _get_stream_payload():
    """Build the initial payload for SSE clients."""
    with STATE_LOCK:
        raw_arts = list(STATE.get('articles', [])[:50])
        stats = dict(STATE.get('stats', {}))
    arts = []
    for a in raw_arts:
        try:
            if callable(globals().get('_ser_article')):
                arts.append(_ser_article(a))
            else:
                arts.append(a)
        except Exception:
            arts.append(a)
    return {
        "articles": arts,
        "stats": stats,
        "macro": _macro_cached() if callable(globals().get('_macro_cached')) else STATE.get('macro_summary', {}),
        "calendar": _stream_calendar(),
    }


def _stream_calendar():
    """Calendar slice of the SSE hello frame.

    This read STATE['calendar'], a key nothing in the project ever writes, so
    the first frame always carried an empty calendar. It now serves whatever
    the econ bundle has already cached — deliberately without calling
    market_context(), because that would make a cold cache block the stream
    handshake on a TradingView fetch.
    """
    try:
        from calendar_data import CACHE as _CAL_CACHE
        bundle = (_CAL_CACHE.get("data") or {}).get("calendar") or {}
        if isinstance(bundle, dict):
            return list(bundle.get("events") or [])
        return list(bundle or [])
    except Exception:
        return []


@app.route("/api/stream/info")
def api_stream_info():
    """What the client needs to choose a transport — never guess, ask.

    The dashboard's StreamManager reads this once per connect: a ws endpoint is
    used when the server can offer one, SSE otherwise, and the polling cadences
    below are the fallback rates it uses only while no stream is alive.
    """
    return jsonify({
        "ok": True,
        "ws": STREAM_WS_URL or None,
        "sse": "/api/stream",
        "channels": {"prices": "prices", "news": "update", "calendar": "calendar"},
        "init_event": "init",
        "heartbeat_seconds": 30,
        "push_seconds": STREAM_PUSH_SECONDS,
        "poll_seconds": {"prices": int(STREAM_PUSH_SECONDS * 2), "data": 120, "calendar": 300},
        "subscribers": len(_sse_subscribers),
    })


@app.route("/api/stream")
def api_stream():
    """SSE endpoint for real-time updates."""
    def event_stream():
        with _sse_lock:
            client_id = _sse_counter[0]
            _sse_counter[0] += 1
            q = queue.Queue(maxsize=50)
            _sse_subscribers[client_id] = q
        try:
            # Send initial state
            yield f"event: init\ndata: {json.dumps(_get_stream_payload(), ensure_ascii=False)}\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except queue.Empty:
                    # Send heartbeat every 30s
                    yield f": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                _sse_subscribers.pop(client_id, None)

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            # no "Connection" header: it is hop-by-hop and PEP 3333 forbids
            # WSGI apps from setting it — waitress rejects the whole response
            # (Werkzeug happened to tolerate it; waitress is the real server now)
            "X-Accel-Buffering": "no",
        }
    )


@app.route("/api/stream/prices")
def api_stream_prices():
    """SSE endpoint for price-only updates (lightweight, fast)."""
    def price_stream():
        with _sse_lock:
            client_id = f"price_{_sse_counter[0]}"
            _sse_counter[0] += 1
            q = queue.Queue(maxsize=20)
            _sse_subscribers[client_id] = q
        try:
            # Send current prices
            prices = LIVE_CACHE.get('data', {})
            yield f"event: prices\ndata: {json.dumps(prices, ensure_ascii=False)}\n\n"
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield msg
                except queue.Empty:
                    yield f": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                _sse_subscribers.pop(client_id, None)

    return Response(
        price_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache"}   # Connection is hop-by-hop — see /api/stream
    )


@app.route("/api/data")
def api_data():
    now = time.time()
    with STATE_LOCK:
        recent, older = [], []
        win = _news_window_sec()
        for a in STATE["articles"]:
            (recent if (a.get("published_ts") or 0) >= now - win else older).append(a)
        older = older + [x for x in (STATE.get("archive") or [])
                         if (x.get("published_ts") or 0) < now - win]
        seen_ids, uniq = set(), []
        for x in older:
            if x.get("id") in seen_ids:
                continue
            seen_ids.add(x.get("id"))
            uniq.append(x)
        older = uniq
        # both lists go out newest-first — the client sorts again defensively, but the
        # payload itself must never be able to look "old news first"
        recent.sort(key=lambda x: -(x.get("published_ts") or 0))
        older.sort(key=lambda x: -(x.get("published_ts") or 0))
        del older[250:]
        archive_total = len(STATE.get("archive") or [])
        articles = [_ser_article(a) for a in recent]
        archive = [_ser_article(a) for a in older]
        market = {}
        for sym, md in STATE["market"].items():
            market[sym] = {
                "price": md.get("price"),
                "change_24h": md.get("change_24h"),
                "volume_24h": md.get("volume_24h"),
                "market_cap": md.get("market_cap"),
                "spark": (md.get("closes") or [])[-30:],
                "stale": bool(md.get("stale")),
            }
        reports_meta = {sym: {"generated_at": r.get("generated_at"),
                              "error": r.get("error"),
                              "news_used": r.get("news_used")}
                        for sym, r in STATE["reports"].items()}
        stats = json.loads(json.dumps(STATE["stats"]))
        try:
            hidden_count = len(_hidden_ids())
        except Exception:
            hidden_count = 0
        assets_meta = all_assets_meta()
        with _CONFIG_LOCK:
            safe_cfg = _mask_secrets(CONFIG)
            cfg = dict(safe_cfg)
            cfg["assets"] = list(CONFIG["assets"]) + [s for s in BUILTIN_MACRO if s not in CONFIG["assets"]]
            interval = CONFIG["interval"]
            rules_max_age = CONFIG.get("report_max_age_hours", MAX_AGE_HOURS)
            rules_score_filter = bool(CONFIG.get("social_score_filter"))
            rules_score_min = CONFIG.get("social_score_min", 2000)

    topic_counts, asset_counts, kind_counts = {}, {}, {}
    for a in articles:
        # .get with a default: a missing topic used to become a literal None
        # key (serialized as "null" by the stdlib, rejected by orjson)
        t_key = a.get("topic") or "?"
        k_key = a.get("source_kind") or "?"
        topic_counts[t_key] = topic_counts.get(t_key, 0) + 1
        kind_counts[k_key] = kind_counts.get(k_key, 0) + 1
        for s in a["assets"]:
            asset_counts[s] = asset_counts.get(s, 0) + 1

    now_iran = datetime.now(timezone.utc).astimezone(IRAN_TZ)
    return _fast_json({
        "ok": True,
        "articles": articles,
        "archive": archive,
        "archive_total": archive_total,
        "market": market,
        "reports_meta": reports_meta,
        "sources": all_sources_view(),
        "topic_counts": topic_counts,
        "asset_counts": asset_counts,
        "kind_counts": kind_counts,
        "kind_labels": KIND_LABELS,
        "config": cfg,
        "assets_meta": assets_meta,
        "macro": _macro_cached(),
        "topics_meta": {t: TOPICS[t] for t in TOPIC_ORDER},
        "stats": stats,
        "hidden_count": hidden_count,
        "translate": cache_stats(),
        "rules": {"max_age_hours": rules_max_age,
                  "min_report_credibility": REPORT_MIN_CREDIBILITY,
                  "social_score_filter": rules_score_filter,
                  "social_score_min": rules_score_min},
        "server_time": now_iran.strftime("%Y-%m-%d %H:%M"),
        "server_time_fa": fa_datetime(now_iran),
        "interval_fa": fa_digits(round(interval / 60)),
    })


# ---------------------------------------------------------------------------
# News hygiene: delete an item, or bring the deleted ones back
# ---------------------------------------------------------------------------
def refilter_state():
    """Re-apply the hygiene rules to what is already in memory."""
    with STATE_LOCK:
        arts, s1, s2 = apply_news_filter(STATE["articles"])
        arch, s3, s4 = apply_news_filter(STATE.get("archive") or [])
        # social popularity gate — retroactive for what is already in memory
        if CONFIG.get("social_score_filter"):
            from reddit_scores import attach_scores as _as
            smin = int(CONFIG.get("social_score_min", 2000) or 0)
            cmin = int(CONFIG.get("social_comments_min", 0) or 0)
            _pool = arts + arch
            _social = [a for a in _pool if a.get("source_kind") in SOCIAL_KINDS]
            _kept, _d = _as(_social, min_score=smin, min_comments=cmin)
            _ok = {id(a) for a in _kept}
            arts = [a for a in arts if a.get("source_kind") not in SOCIAL_KINDS
                    or id(a) in _ok]
            arch = [a for a in arch if a.get("source_kind") not in SOCIAL_KINDS
                    or id(a) in _ok]
        STATE["articles"] = arts
        STATE["archive"] = arch
    return (s1 + s3, s2 + s4)


@app.route("/api/article/hide", methods=["POST"])
def api_article_hide():
    """Delete one news item from the dashboard, everywhere, for good.

    Persisted in its own table so a later scrape of the same story cannot bring
    it back; the bodies/reports caches drop it on the next cycle."""
    data = request.get_json(silent=True) or {}
    aid = str(data.get("id") or "").strip()
    if not aid:
        return jsonify({"ok": False, "error": "missing_id"}), 400
    try:
        from database import hide_article
        hide_article(aid)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    with STATE_LOCK:
        STATE["articles"] = [a for a in STATE["articles"] if a.get("id") != aid]
        STATE["archive"] = [a for a in (STATE.get("archive") or []) if a.get("id") != aid]
        hidden_count = None
    for cid in (aid, aid + "|fa"):
        with _CONTENT_LOCK:
            CONTENT_CACHE.pop(cid, None)
        with _FA_CONTENT_LOCK:
            FA_CONTENT_CACHE.pop(cid, None)
    try:
        from database import hidden_ids
        hidden_count = len(hidden_ids())
    except Exception:
        pass
    return jsonify({"ok": True, "id": aid, "hidden_count": hidden_count})


@app.route("/api/article/restore", methods=["POST"])
def api_article_restore():
    """Bring every deleted news item back (next poll re-reads SQLite)."""
    try:
        from database import unhide_all
        n = unhide_all()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    try:
        from database import load_articles_for_state
        window_sec = float(CONFIG.get("report_max_age_hours", 24)) * 3600.0
        rec, arch = load_articles_for_state(window_sec)
        with STATE_LOCK:
            STATE["articles"], STATE["archive"] = rec, arch
    except Exception:
        pass
    return jsonify({"ok": True, "restored": n})


@app.route("/api/stats")
def api_stats():
    with STATE_LOCK:
        s = dict(STATE["stats"])
        s["total_articles"] = len(STATE["articles"])
    s["interval"] = CONFIG["interval"]
    return jsonify(s)


@app.route("/api/chart/<symbol>")
def api_chart_data(symbol):
    """Get chart payload with candles + indicators.
    This is what the chart widget consumes.
    """
    tf = request.args.get('tf', '1D')
    payload = chart_payload(symbol, tf=tf)
    if payload:
        return jsonify({"ok": True, "symbol": symbol, "data": payload})
    return jsonify({"ok": False, "error": "no data"}), 404


@app.route("/api/sentiment")
def api_sentiment():
    """Get sentiment data for all assets or a specific one."""
    symbol = request.args.get('symbol')

    if symbol:
        articles = STATE.get('articles', [])
        from sentiment import _normalize_sym, get_aggregate_sentiment
        agg = get_aggregate_sentiment(articles, symbol=symbol)

        # Recent sentiment trend (last 20 articles by date)
        sym_set = _normalize_sym(symbol)
        filtered = []
        for a in articles:
            a_syms = set(a.get('symbols', []) or []) | set(a.get('assets', []) or [])
            if a.get('symbol'):
                a_syms.add(a['symbol'].upper())
            if any(s.upper() in sym_set for s in a_syms):
                filtered.append(a)

        recent = sorted(filtered, key=lambda a: a.get('published_ts', 0) or 0, reverse=True)[:20]
        trend = [a.get('sentiment_score', 0) for a in recent]

        return jsonify({
            'ok': True,
            'symbol': symbol,
            'aggregate': agg,
            'recent_trend': trend,
            'articles': [{
                'title': a.get('title', ''),
                'score': a.get('sentiment_score', 0),
                'label': a.get('sentiment_label', 'neutral'),
            } for a in recent[:10]],
        })

    # Return all asset sentiments
    return jsonify({
        'ok': True,
        'sentiment': STATE.get('sentiment', {}),
        'overall': STATE.get('sentiment', {}).get('_overall', {}),
    })


@app.route("/api/intelligence")
def api_intelligence():
    """News intelligence: anomalies, correlations, dedup stats."""
    return jsonify({"ok": True, **get_intelligence_summary()})


@app.route("/manifest.json")
def manifest():
    """Legacy URL for the web app manifest.

    There used to be a second, older manifest at the project root (branded
    "FreeBuff", pointing at /static/icons) that the page linked while the real
    one — web/manifest.webmanifest, Persian, RTL, maskable icon — was linked
    nowhere. The page and the install metadata disagreed, and the two files
    could drift apart with nothing to catch it. There is now one manifest; this
    URL redirects to it so an older bookmark or installed app still resolves.
    """
    return redirect("/manifest.webmanifest", code=301)


# NOTE: a second `/sw.js` (+`/static/sw.js`) rule used to be declared here. It
# was dead code — werkzeug resolves the first matching rule, and that is the
# PWA one further up — and it served the retired worker from static/, which is
# the file the page must never be handed again. `/static/sw.js` still answers
# 200 from Flask's own static handler (it is the tombstone that unregisters
# itself), so the stale registration in older browsers can be retired.

# ---------------------------------------------------------------------------
# live prices — free, key-less endpoints polled from the browser every 15s
# ---------------------------------------------------------------------------
LIVE_CACHE = {"ts": 0.0, "data": {}}
LIVE_TTL = 12.0          # seconds; browsers poll every ~15s, this dedupes them
LIVE_TIMEOUT = 6


def _live_yahoo_quote(yh_symbol: str):
    """Yahoo v8 chart meta — regularMarketPrice/ChangePercent (v7 quote needs a crumb)."""
    for cand in yahoo_candidates(yh_symbol):
        for host in ("query1", "query2"):
            try:
                r = requests.get(
                    f"https://{host}.finance.yahoo.com/v8/finance/chart/{cand}",
                    params={"range": "1d", "interval": "1d"},
                    headers=HEADERS, timeout=LIVE_TIMEOUT)
                if r.status_code != 200:
                    continue
                meta = ((r.json().get("chart") or {}).get("result") or [{}])[0].get("meta", {})
                price = meta.get("regularMarketPrice")
                if price is not None:
                    return {"price": price,
                            "change_24h": meta.get("regularMarketChangePercent")}
            except Exception:
                continue
    return None


def _live_binance(symbol: str):
    """Binance 24h ticker — deepest free crypto quotes, updates every second."""
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                         params={"symbol": f"{symbol}USDT"},
                         headers=HEADERS, timeout=LIVE_TIMEOUT)
        if r.status_code != 200:
            return None
        d = r.json()
        last = float(d.get("lastPrice") or 0)
        if last <= 0:
            return None
        return {"price": last, "change_24h": float(d.get("priceChangePercent") or 0)}
    except Exception:
        return None


def live_prices() -> dict:
    """{SYM: {price, change_24h, ts, src}} for every enabled asset, cached 12s."""
    now = time.time()
    with _LIVE_LOCK:
        if now - LIVE_CACHE["ts"] < LIVE_TTL and LIVE_CACHE["data"]:
            return LIVE_CACHE["data"]
        if LIVE_CACHE.get("busy"):
            return LIVE_CACHE.get("data", {})
        LIVE_CACHE["busy"] = True

    def _job():
        try:
            _refresh_live()
        finally:
            with _LIVE_LOCK:
                LIVE_CACHE["busy"] = False
    threading.Thread(target=_job, daemon=True).start()
    with _LIVE_LOCK:
        return LIVE_CACHE.get("data") or {}


def _live_gold_api(sym: str):
    """gold-api.com — free, key-less SPOT metals quote (XAU/XAG).

    Yahoo only carries the *futures* contract (GC=F/SI=F), which prints a few
    dollars above the spot price every site the reader compares against shows.
    No 24h-change field here — the caller keeps the Yahoo change percent."""
    try:
        r = requests.get(f"https://api.gold-api.com/price/{sym}",
                         headers=HEADERS, timeout=LIVE_TIMEOUT)
        if r.status_code == 200:
            p = (r.json() or {}).get("price")
            if p:
                return {"price": float(p), "change_24h": None}
    except Exception:
        pass
    return None


_PAPRIKA_IDS = {"BTC": "btc-bitcoin", "ETH": "eth-ethereum", "SOL": "sol-solana",
                "XRP": "xrp-xrp", "ADA": "ada-cardano", "BNB": "bnb-binance-coin",
                "DOGE": "doge-dogecoin"}

def _live_paprika(symbol: str):
    """CoinPaprika — free, key-less crypto fallback (no rate-limit cliff)."""
    pid = _PAPRIKA_IDS.get(symbol)
    if not pid:
        return None
    try:
        r = requests.get(f"https://api.coinpaprika.com/v1/tickers/{pid}",
                         headers=HEADERS, timeout=LIVE_TIMEOUT)
        if r.status_code == 200:
            usd = ((r.json() or {}).get("quotes") or {}).get("USD") or {}
            p = usd.get("price")
            if p:
                return {"price": float(p),
                        "change_24h": usd.get("percent_change_24h")}
    except Exception:
        pass
    return None


def _refresh_live() -> dict:
    now = time.time()
    meta = all_assets_meta()
    out = {}
    cg_ids, yahoo_syms = {}, {}
    with _CONFIG_LOCK:
        configured_assets = list(CONFIG["assets"])
    for sym, m in meta.items():
        if configured_assets and sym not in configured_assets:
            continue
        if m.get("coingecko"):
            cg_ids[m["coingecko"]] = sym
        elif m.get("yahoo"):
            yahoo_syms[sym] = m["yahoo"]

    # 1) CoinPaprika — key-less crypto quotes (price + true 24h change);
    #    api.binance.com times out from this network, so it demotes to a
    #    fallback rung rather than eating a timeout per symbol every refresh.
    for sym in set(cg_ids.values()):
        if sym in BUILTIN_CRYPTO or meta.get(sym, {}).get("is_crypto"):
            got = _live_paprika(sym)
            if got:
                got.update(ts=now, src="paprika")
                out[sym] = got

    # 2) Binance for whatever Paprika missed
    for sym in set(cg_ids.values()) - set(out):
        if sym in BUILTIN_CRYPTO or meta.get(sym, {}).get("is_crypto"):
            got = _live_binance(sym)
            if got:
                got.update(ts=now, src="binance")
                out[sym] = got

    # 3) CoinGecko fills the rest (batched, one call)
    missing_cg = {cid: sym for cid, sym in cg_ids.items() if sym not in out}
    if missing_cg:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                             params={"ids": ",".join(missing_cg), "vs_currencies": "usd",
                                     "include_24hr_change": "true"},
                             headers=HEADERS, timeout=LIVE_TIMEOUT)
            r.raise_for_status()
            for cg_id, vals in r.json().items():
                sym = missing_cg.get(cg_id)
                if sym and vals.get("usd") is not None:
                    out[sym] = {"price": vals["usd"],
                                "change_24h": vals.get("usd_24h_change"),
                                "ts": now, "src": "coingecko"}
        except Exception:
            pass

    # 4) Yahoo for every remaining (macro) symbol
    for sym in list((set(cg_ids.values()) | set(yahoo_syms)) - set(out)):
        if sym in BUILTIN_CRYPTO or meta.get(sym, {}).get("is_crypto"):
            yh = meta.get(sym, {}).get("yahoo")
            if yh:
                got = _live_yahoo_quote(yh)
                if got:
                    got.update(ts=now, src="yahoo")
                    out[sym] = got
        elif sym in yahoo_syms:
            got = _live_yahoo_quote(yahoo_syms[sym])
            if got:
                got.update(ts=now, src="yahoo")
                out[sym] = got

    # 5) gold-api spot overrides the futures price for gold/silver — the
    #    displayed number then matches spot quotes everywhere else; the Yahoo
    #    futures change percent (≈ the spot move) is kept when present.
    for sym in ("XAU", "XAG"):
        if configured_assets and sym not in configured_assets:
            continue
        if not (meta.get(sym) or {}).get("yahoo"):
            continue
        spot = _live_gold_api(sym)
        if not spot:
            continue
        prev = out.get(sym) or {}
        if prev.get("change_24h") is not None:
            spot["change_24h"] = prev["change_24h"]
        spot.update(ts=now, src="gold-api")
        out[sym] = spot

    with _LIVE_LOCK:
        LIVE_CACHE["ts"] = now
        LIVE_CACHE["data"] = out
    try:
        _sse_broadcast("prices", out)
    except Exception:
        pass
    try:
        record_news_events(STATE.get("articles", []), out)
        update_correlation_prices(out)
    except Exception:
        pass
    return out


@app.route("/api/etf")
def api_etf_quotes():
    """Live spot-ETF quotes (BTC/ETH ETF symbols) via Yahoo public quote API."""
    try:
        return jsonify({"ok": True, "quotes": _etf_quotes()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "quotes": {}})


ETF_QUOTES_CACHE = {"ts": 0.0, "data": {}}
# The major listed vehicles, not just the first-wave spot funds. Order is the
# order they render in (dict order is preserved through the executor).
# Every fund the board can quote. Names here are only a FALLBACK — the live
# name comes from Yahoo's own meta (longName), so a fund that has been renamed
# can never show a stale label ("ETH" used to be labelled as ProShares).
ETF_YAHOO = {
    # ── spot Bitcoin (all US issuers) ──────────────────────────────────────
    "IBIT": "iShares Bitcoin Trust", "FBTC": "Fidelity Wise Origin Bitcoin",
    "BITB": "Bitwise Bitcoin ETF",   "ARKB": "ARK 21Shares Bitcoin",
    "GBTC": "Grayscale Bitcoin Trust", "BTC": "Grayscale Bitcoin Mini Trust",
    "BTCO": "Invesco Galaxy Bitcoin", "HODL": "VanEck Bitcoin ETF",
    "BRRR": "CoinShares Valkyrie Bitcoin", "EZBC": "Franklin Bitcoin ETF",
    "BTCW": "WisdomTree Bitcoin Fund", "DEFI": "Hashdex Bitcoin ETF",
    # ── Bitcoin futures / short ───────────────────────────────────────────
    "BITO": "ProShares Bitcoin ETF", "BITI": "ProShares Short Bitcoin",
    # ── leveraged & inverse crypto ────────────────────────────────────────
    "BITX": "Volatility Shares 2x Bitcoin", "BITU": "ProShares Ultra Bitcoin",
    "SBIT": "ProShares UltraShort Bitcoin",
    "ETHU": "ProShares Ultra Ether", "ETHT": "ProShares Ultra Ether (alt)",
    "ETHD": "ProShares UltraShort Ether",
    # ── spot Ethereum (all US issuers) ────────────────────────────────────
    "ETHA": "iShares Ethereum Trust",  "FETH": "Fidelity Ethereum Fund",
    "ETHW": "Bitwise Ethereum ETF",    "ETHV": "VanEck Ethereum ETF",
    "QETH": "Invesco Galaxy Ethereum", "EZET": "Franklin Ethereum ETF",
    "ETHE": "Grayscale Ethereum Staking ETF", "ETH": "Grayscale Ethereum Mini Trust",
    "TETH": "21Shares Ethereum ETF", "ETHB": "iShares Staked Ethereum Trust",
    # ── spot Solana ───────────────────────────────────────────────────────
    "SSK": "REX-Osprey SOL + Staking", "FSOL": "Fidelity Solana Fund",
    "SOLZ": "Solana ETF", "SOEZ": "Franklin Solana ETF",
    # ── spot XRP ──────────────────────────────────────────────────────────
    "XRPR": "REX-Osprey XRP ETF", "XRPI": "XRP ETF",
    # ── blended crypto strategies ─────────────────────────────────────────
    "BETH": "ProShares Bitcoin & Ether Market Cap Weight",
    "BITC": "Bitwise Trendwise BTC & Treasuries",
    "BTCI": "NEOS Bitcoin High Income",
    "AETH": "Bitwise Trendwise ETH & Treasuries",
    # ── crypto equity / miners ────────────────────────────────────────────
    "WGMI": "CoinShares Bitcoin Miners", "BITQ": "Bitwise Crypto Innovators",
    "BLOK": "Amplify Blockchain Technology", "BKCH": "Global X Blockchain",
    "DAPP": "VanEck Digital Transformation",
    # ── metals & commodities ──────────────────────────────────────────────
    "GLD": "SPDR Gold Shares",   "IAU": "iShares Gold Trust",
    "SLV": "iShares Silver Trust", "GDX": "VanEck Gold Miners",
    "USO": "United States Oil Fund", "UNG": "United States Natural Gas",
    # ── broad market & rates ──────────────────────────────────────────────
    "SPY": "SPDR S&P 500", "QQQ": "Invesco QQQ Trust", "DIA": "SPDR Dow Jones Industrial",
    "IWM": "iShares Russell 2000", "TLT": "iShares 20+ Year Treasury",
}
ETF_GROUP = {}
for _s in "IBIT FBTC BITB ARKB GBTC BTC BTCO HODL BRRR EZBC BTCW DEFI".split():
    ETF_GROUP[_s] = "Bitcoin"
for _s in "BITO BITI".split():
    ETF_GROUP[_s] = "BTC futures"
for _s in "BITX BITU SBIT ETHU ETHT ETHD".split():
    ETF_GROUP[_s] = "Leveraged"
for _s in "ETHA FETH ETHW ETHV QETH EZET ETHE ETH TETH ETHB".split():
    ETF_GROUP[_s] = "Ethereum"
for _s in "SSK FSOL SOLZ SOEZ".split():
    ETF_GROUP[_s] = "Solana"
for _s in "XRPR XRPI".split():
    ETF_GROUP[_s] = "XRP"
for _s in "BETH BITC BTCI AETH".split():
    ETF_GROUP[_s] = "Crypto blends"
for _s in "WGMI BITQ BLOK BKCH DAPP".split():
    ETF_GROUP[_s] = "Crypto equity"
for _s in "GLD IAU SLV GDX USO UNG".split():
    ETF_GROUP[_s] = "Commodities"
for _s in "SPY QQQ IWM TLT DIA".split():
    ETF_GROUP[_s] = "Markets"


def _etf_quotes():
    """Per-symbol Yahoo v8 chart meta — free, no key/crumb; cached 60 s."""
    now = time.time()
    if ETF_QUOTES_CACHE["data"] and now - ETF_QUOTES_CACHE["ts"] < 120:
        return ETF_QUOTES_CACHE["data"]
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    def one(sym):
        try:
            r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                             params={"range": "1d", "interval": "1d"}, headers=hdrs, timeout=8)
            res = (r.json() or {}).get("chart", {}).get("result") or []
            if not res:
                return None
            m = res[0].get("meta", {})
            price, prev = m.get("regularMarketPrice"), m.get("chartPreviousClose")
            chg = ((price - prev) / prev * 100.0) if (price and prev) else None
            name = (m.get("longName") or m.get("shortName")
                    or ETF_YAHOO.get(sym, sym))
            return sym, {"name": name, "price": price,
                         "change_pct": round(chg, 2) if chg is not None else None,
                         "prev_close": prev, "market_state": m.get("marketState"),
                         "currency": m.get("currency"),
                         "group": ETF_GROUP.get(sym, "Other")}
        except Exception:
            return None
    out = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for res in ex.map(one, list(ETF_YAHOO)):
            if res:
                out[res[0]] = res[1]
    if out:
        ETF_QUOTES_CACHE["data"] = out
        ETF_QUOTES_CACHE["ts"] = now
    return out


# ---------------------------------------------------------------------------
# per-asset sentiment: local, explainable keyword polarity (no API, no model)
# ---------------------------------------------------------------------------
# The old formula multiplied every headline by a["sentiment"], a field nothing
# in the pipeline ever set — so every asset collapsed to 50 + a freshness bonus
# and the whole board printed the same number. These regexes read the English
# headline + summary directly, which is what makes the per-asset gauges differ.
_BULL_RE = re.compile(
    r"\b(?:surge\w*|rall(?:y|ies|ied|ying)|soar\w*|jump\w*|gain\w*|ris(?:e|es|ing)|rose|"
    r"breakout|record high\w*|all-time high|bullish|inflow\w*|adopt\w*|approv\w*|"
    r"upgrad\w*|beat\w*|boost\w*|accumulat\w*|rebound\w*|recover\w*|demand|"
    r"partnership\w*|launch\w*|milestone\w*|buy\w*|strong\w*|optimis\w*|outperform\w*)\b",
    re.I)
_BEAR_RE = re.compile(
    r"\b(?:plung\w*|crash\w*|slump\w*|drop\w*|fall\w*|fell|declin\w*|sell-?off\w*|"
    r"bearish|outflow\w*|hack\w*|exploit\w*|lawsuit\w*|ban(?:ned|s|ning)?|fine[sd]?|"
    r"penalt\w*|liquidat\w*|downgrad\w*|fear\w*|panic\w*|warn\w*|fraud\w*|"
    r"delist\w*|dump\w*|loss(?:es)?|weak\w*|pressure|investigat\w*|sue[sd]?|"
    r"subpoena\w*|bankrupt\w*|halt\w*|reject\w*|delay\w*|risk\w*|concern\w*|"
    r"crackdown|sell\w*|slid\w*|tumble\w*|shrink\w*)\b",
    re.I)


def headline_polarity(*texts) -> float:
    """-1..1 keyword polarity of one item (0.0 when nothing is directional)."""
    t = " ".join(x for x in texts if x)
    if not t:
        return 0.0
    up, dn = len(_BULL_RE.findall(t)), len(_BEAR_RE.findall(t))
    if not up and not dn:
        return 0.0
    return max(-1.0, min(1.0, (up - dn) / float(up + dn)))


def asset_sentiment(arts, now=None) -> dict:
    """Credibility- and freshness-weighted mood of one asset's headlines.

    Returns the 0-100 gauge plus the bullish/bearish item counts, so the UI can
    show what the number is actually made of.
    """
    if now is None:
        now = time.time()
    weighted = wsum = 0.0
    pos = neg = 0
    for a in arts:
        w = float(a.get("credibility") or 0.5)
        age = now - (a.get("published_ts") or 0)
        w *= 1.0 if age <= 6 * 3600 else (0.75 if age <= 24 * 3600 else 0.5)
        p = a.get("sentiment")
        if p is None:
            p = headline_polarity(a.get("title"), a.get("summary"))
        if p > 0.15:
            pos += 1
        elif p < -0.15:
            neg += 1
        weighted += w * p
        wsum += w
    s = (weighted / wsum) if wsum else 0.0
    s = max(-1.0, min(1.0, s))
    return {"now": int(round(50.0 + 42.0 * s)), "sent": round(s, 3),
            "pos": pos, "neg": neg}


FNG_SYM_CACHE = {}   # sym -> {"ts": float, "data": dict} — 15-min per-asset cache


@app.route("/api/fng/<sym>")
def api_fng_symbol(sym):
    """Per-asset fear/greed — the last 24 h of headlines for one symbol, scored
    locally (keyword polarity weighted by source credibility and freshness)."""
    sym = (sym or "").upper()
    now = time.time()
    c = FNG_SYM_CACHE.get(sym)
    if c and now - c["ts"] < 900:
        return jsonify({"ok": True, "sym": sym, **c["data"]})
    with STATE_LOCK:
        arts = [a for a in STATE["articles"]
                if sym in (a.get("assets") or [])
                and (a.get("published_ts") or 0) >= now - _news_window_sec()]
    m = asset_sentiment(arts, now)
    score = max(0, min(100, m["now"]))
    label = ("Extreme Fear" if score < 25 else "Fear" if score < 45 else
             "Neutral" if score < 55 else "Greed" if score < 75 else "Extreme Greed")
    data = {"now": score, "label": label, "count": len(arts),
            "pos": m["pos"], "neg": m["neg"], "sent": m["sent"]}
    FNG_SYM_CACHE[sym] = {"ts": now, "data": data}
    return jsonify({"ok": True, "sym": sym, **data})


@app.route("/api/live")
def api_live():
    try:
        return jsonify({"ok": True, "prices": live_prices(),
                        "fng": _fng_cached(),
                        "server_time": fa_datetime(datetime.now(timezone.utc))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "prices": {}})


FNG_CACHE = {"ts": 0.0, "data": None}


def _fng_cached():
    """Fear & Greed, refreshed at most every 30 min (it updates daily anyway)."""
    now = time.time()
    if FNG_CACHE["data"] is None or now - FNG_CACHE["ts"] > 1800:
        FNG_CACHE["data"] = _fng()
        FNG_CACHE["ts"] = now
    return FNG_CACHE["data"]


MACRO_CACHE = {"ts": 0.0, "data": []}


def _macro_cached():
    """DXY/SPX/VIX/WTI strip quotes, 5-minute cache (market hours only move slowly)."""
    now = time.time()
    if MACRO_CACHE["data"] is None or now - MACRO_CACHE["ts"] > 300:
        MACRO_CACHE["data"] = _macro_quotes()
        MACRO_CACHE["ts"] = now
    return MACRO_CACHE["data"]


# ---------------------------------------------------------------------------
# live intraday candles — Yahoo v8 chart endpoint (free, key-less)
# powers the TradingView-style candlestick chart in the report panel
# ---------------------------------------------------------------------------
CANDLE_TTL = 60.0
CANDLES_CACHE = {}               # (sym, tf) -> {"ts": float, "data": dict}


def _candles_cached(cache_key):
    """Cache lookup, honouring CANDLE_TTL.

    The TTL constant existed but was never read, so once a (symbol, timeframe)
    was fetched its series was served for the life of the process — the chart
    showed the same candles for days. An entry written without a timestamp (as
    tests do) counts as fresh.
    """
    entry = CANDLES_CACHE.get(cache_key)
    if not isinstance(entry, dict):
        return None
    ts = entry.get("ts")
    if ts is not None:
        try:
            if time.time() - float(ts) > CANDLE_TTL:
                CANDLES_CACHE.pop(cache_key, None)
                return None
        except (TypeError, ValueError):
            pass
    return entry.get("data") or None


def _candles_store(cache_key, candles):
    """Store a series and keep the cache bounded (_CANDLES_MAX).

    The key includes the caller-supplied symbol, so without a cap the dict grew
    with every distinct ticker anyone asked for.
    """
    CANDLES_CACHE[cache_key] = {"ts": time.time(), "data": candles}
    if len(CANDLES_CACHE) > _CANDLES_MAX:
        oldest = sorted(CANDLES_CACHE,
                        key=lambda k: float((CANDLES_CACHE[k] or {}).get("ts") or 0))
        for k in oldest[:len(CANDLES_CACHE) - _CANDLES_MAX]:
            CANDLES_CACHE.pop(k, None)


@app.route("/api/candles/<symbol>")
def api_candles(symbol):
    """Get OHLCV candle data for a symbol.
    Query params: tf=1D (default), limit=100 (default), max=500
    """
    tf = request.args.get('tf', '1D')
    if tf not in ('1D', '1W'):  # advanced timeframes
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        from billing import check_feature
        if not check_feature(api_key, 'advanced_charts'):
            return jsonify({"error": "Pro required for this timeframe", "upgrade": "Upgrade to Pro: /api/billing/upgrade"}), 403

    try:
        limit = min(int(request.args.get('limit', 100)), 500)
    except (ValueError, TypeError):
        limit = 100

    # Try to get from cache first
    cache_key = f"{symbol}_{tf}"
    cache_hit = _candles_cached(cache_key)
    if cache_hit:
        candles = cache_hit[-limit:]
        if candles:
            return jsonify({"ok": True, "symbol": symbol, "tf": tf, "candles": candles})

    # Fetch from Yahoo Finance
    try:
        from indicators import yahoo_candles
        candles = yahoo_candles(symbol, tf, limit)
        if candles:
            _candles_store(cache_key, candles)
            return jsonify({"ok": True, "symbol": symbol, "tf": tf, "candles": candles})
    except Exception as e:
        logger.error(f"Failed to fetch candles for {symbol}: {e}")

    return jsonify({"ok": False, "error": "no data"}), 404


@app.route("/api/assets")
def api_assets_list():
    """Get list of all tracked assets with metadata."""
    from sources import ASSETS
    assets = []
    for sym, meta in ASSETS.items():
        cat = meta.get('category')
        if not cat:
            cat = 'metals' if sym in ('XAU', 'XAG') else ('macro' if sym in ('WTI', 'DXY', 'SPX', 'VIX') else 'crypto')
        tier = meta.get('tier', 1 if sym in ('BTC', 'ETH') else 2 if sym in ('SOL', 'XRP', 'XAU') else 3)
        assets.append({
            "symbol": sym,
            "name": meta.get('name', sym),
            "category": cat,
            "tier": tier,
        })
    return jsonify({"ok": True, "assets": assets})


# ---------------------------------------------------------------------------
# Phase 9 — REST API Key System & /api/v1/ Endpoints
# ---------------------------------------------------------------------------
import secrets
import hashlib
from functools import wraps

_api_keys = {}  # key_hash -> {name, created, rate_limit, requests_today, last_reset}
_default_key = ""  # raw value of the auto-generated default key (persisted on disk)
_KEYSTORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "api_keys.json")

def _hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]

def _save_api_keys():
    """Persist key metadata so keys survive restarts. Only the *default* key's
    raw value is stored (the owner needs it to call the API); everything else
    keeps just its hash, like an auth system should."""
    try:
        os.makedirs(os.path.dirname(_KEYSTORE_PATH), exist_ok=True)
        payload = {
            "default_key": _default_key,
            "keys": {
                h: {k: v[k] for k in ("name", "created", "rate_limit") if k in v}
                for h, v in _api_keys.items()
            },
        }
        tmp = _KEYSTORE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _KEYSTORE_PATH)
    except Exception:
        pass

def _load_api_keys():
    try:
        with open(_KEYSTORE_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        for h, meta in (payload.get("keys") or {}).items():
            _api_keys[h] = {
                'name': meta.get('name', 'unnamed'),
                'created': meta.get('created', time.time()),
                'rate_limit': int(meta.get('rate_limit', 100)),
                'requests_today': 0,
                'last_reset': time.time(),
            }
        return payload.get("default_key") or ""
    except Exception:
        return ""

def _generate_api_key() -> str:
    """Generate a new API key. Call once per user."""
    key = f"fb_{secrets.token_hex(24)}"
    key_hash = _hash_api_key(key)
    _api_keys[key_hash] = {
        'name': 'default',
        'created': time.time(),
        'rate_limit': 100,  # requests per hour
        'requests_today': 0,
        'last_reset': time.time(),
    }
    _save_api_keys()
    return key

def _check_api_key(f):
    """Decorator for API key authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # API key from header or query param
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        key_hash = _hash_api_key(api_key)
        key_data = _api_keys.get(key_hash)
        if not key_data:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Rate limiting (simple hourly window)
        now = time.time()
        if now - key_data['last_reset'] > 3600:
            key_data['requests_today'] = 0
            key_data['last_reset'] = now
        
        if key_data['requests_today'] >= key_data['rate_limit']:
            return jsonify({"error": "Rate limit exceeded"}), 429
        
        key_data['requests_today'] += 1
        return f(*args, **kwargs)
    return decorated

# Generate a default API key on startup — persisted in data/api_keys.json so it
# survives restarts; the raw key is never printed to shared logs.
_default_key = _load_api_keys()
if not _default_key or _hash_api_key(_default_key) not in _api_keys:
    _default_key = _generate_api_key()
    _save_api_keys()
print(f"[API] Default API key stored in data/api_keys.json — use header: X-API-Key")


# === V1 PUBLIC API (requires API key) ===

@app.route("/api/v1/articles")
@_check_api_key
def api_v1_articles():
    """GET /api/v1/articles?symbol=BTC&limit=50&offset=0
    
    Returns paginated articles with sentiment scores.
    """
    symbol = request.args.get('symbol')
    try:
        limit = min(int(request.args.get('limit', 50)), 200)
    except (ValueError, TypeError):
        limit = 50
    try:
        offset = int(request.args.get('offset', 0))
    except (ValueError, TypeError):
        offset = 0
    
    articles = STATE.get('articles', [])
    
    if symbol:
        sym_u = symbol.upper()
        # union, not "symbols or assets": with both keys present the old form
        # silently ignored assets and dropped half the matches
        articles = [a for a in articles
                    if sym_u in (set(a.get('symbols') or []) | set(a.get('assets') or []))]
    
    total = len(articles)
    page = articles[offset:offset + limit]
    
    return jsonify({
        "ok": True,
        "total": total,
        "offset": offset,
        "limit": limit,
        "articles": [{
            "id": a.get("id"),
            "title": a.get("title", ""),
            "title_fa": a.get("title_fa", ""),
            "summary": a.get("summary", ""),
            "summary_fa": a.get("summary_fa", ""),
            "source": a.get("source_name", ""),
            "source_key": a.get("source_key", ""),
            "link": a.get("link", ""),
            "published": a.get("published_ts"),
            "symbols": sorted(set(a.get("symbols") or []) | set(a.get("assets") or [])),
            "topic": a.get("topic", ""),
            "topic_fa": a.get("topic_fa", ""),
            "sentiment": {
                "score": a.get("sentiment_score", 0),
                "label": a.get("sentiment_label", "neutral"),
                "confidence": a.get("sentiment_confidence", 0),
            },
            "tier": a.get("tier", 3),
        } for a in page],
    })


@app.route("/api/v1/indicators/<symbol>")
@_check_api_key
def api_v1_indicators(symbol):
    """GET /api/v1/indicators/BTC-USD?tf=1D
    
    Returns technical indicators for a symbol.
    """
    from indicators import snapshot, yahoo_candles
    tf = request.args.get('tf', '1D')
    snap = None
    try:
        cache_key = f"{symbol}_{tf}"
        candles = _candles_cached(cache_key) or []
        if not candles:
            candles = yahoo_candles(symbol, tf, 100) or []
        if candles:
            closes = [c.get('close') for c in candles if c.get('close') is not None]
            highs = [c.get('high') for c in candles if c.get('high') is not None]
            lows = [c.get('low') for c in candles if c.get('low') is not None]
            volumes = [c.get('volume') for c in candles if c.get('volume') is not None]
            if closes:
                snap = snapshot(closes, volumes=volumes, highs=highs, lows=lows)
    except Exception as e:
        logger.error(f"Failed to compute indicators for {symbol}: {e}")

    if not snap:
        # Fallback: the live market series for this symbol, if we have one.
        # This used to call snapshot(symbol) with the ticker *string*, but
        # snapshot() reads its first argument as a list of closes — so the
        # endpoint answered 200 with spot="C" (the first letter of the ticker)
        # and every indicator null, instead of saying it had no data.
        try:
            with STATE_LOCK:
                md = (STATE.get("market") or {}).get(symbol.upper()) or {}
            closes = [c for c in (md.get("closes") or []) if c is not None]
            if closes:
                snap = snapshot(closes, volumes=md.get("volumes") or None)
        except Exception:
            pass

    if snap:
        return jsonify({"ok": True, "symbol": symbol, "indicators": snap})
    return jsonify({"ok": False, "error": "no data"}), 404


@app.route("/api/v1/sentiment")
@_check_api_key
def api_v1_sentiment():
    """GET /api/v1/sentiment?symbol=BTC
    
    Returns sentiment analysis for an asset or overall.
    """
    symbol = request.args.get('symbol')
    sentiment_data = STATE.get('sentiment', {})
    
    if symbol:
        data = sentiment_data.get(symbol.upper(), {})
        return jsonify({"ok": True, "symbol": symbol.upper(), **data})
    
    return jsonify({"ok": True, "sentiment": sentiment_data})


@app.route("/api/v1/calendar")
@_check_api_key
def api_v1_calendar():
    """GET /api/v1/calendar?days=7
    
    Returns economic calendar events.
    """
    from calendar_data import market_context
    try:
        days = max(1, min(31, int(request.args.get('days', 7))))
    except (TypeError, ValueError):
        days = 7
    ctx = market_context()
    week = ctx.get('calendar') or {}
    # `ctx.get('events') or ctx.get('calendar')` returned the whole week bundle
    # ({events, range, source}) under a key the spec documents as the event
    # list, and `days` — declared in /api/docs — was ignored entirely.
    events = week.get('events') if isinstance(week, dict) else (week or [])
    events = list(events or [])
    if days < 14:
        horizon = time.time() + days * 86400
        events = [e for e in events if (e.get('ts') or 0) <= horizon]
    return jsonify({"ok": True, "calendar": events, "count": len(events), "days": days})


@app.route("/api/v1/reports/<symbol>")
@_check_api_key
def api_v1_reports(symbol):
    """GET /api/v1/reports/BTC
    
    Returns technical analysis report for a symbol.
    """
    report = STATE.get('reports', {}).get(symbol.upper())
    if report:
        return jsonify({"ok": True, "symbol": symbol.upper(), "report": report})
    return jsonify({"ok": False, "error": "no report"}), 404


@app.route("/api/v1/health")
def api_v1_health():
    """GET /api/v1/health — public, no API key needed."""
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.time(),
    })


@app.route("/api/v1/assets")
@_check_api_key
def api_v1_assets():
    """GET /api/v1/assets — list all tracked assets."""
    from sources import ASSETS
    return jsonify({
        "ok": True,
        "assets": [
            {"symbol": sym, **meta}
            for sym, meta in ASSETS.items()
        ],
    })


@app.route("/api/docs")
def api_docs():
    """Interactive API documentation page."""
    try:
        from api_docs import get_swagger_html
        return get_swagger_html()
    except Exception:
        return """<!DOCTYPE html>
<html>
<head>
    <title>FreeBuff API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>body { margin: 0; padding: 0; background: #0a0a1a; }</style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
    SwaggerUIBundle({
        spec: {
            openapi: "3.0.0",
            info: { title: "FreeBuff API", version: "1.0.0",
                    description: "Real-time financial news, sentiment, and technical analysis API" },
            servers: [{ url: "/" }],
            components: {
                securitySchemes: {
                    ApiKeyAuth: { type: "apiKey", in: "header", name: "X-API-Key" }
                }
            },
            security: [{ ApiKeyAuth: [] }],
            paths: {
                "/api/v1/health": { get: { summary: "Health check", security: [], responses: { "200": { description: "OK" } } } },
                "/api/v1/assets": { get: { summary: "List all assets", responses: { "200": { description: "Asset list" } } } },
                "/api/v1/articles": { get: { summary: "Get articles", responses: { "200": { description: "Article list" } } } },
                "/api/v1/indicators/{symbol}": { get: { summary: "Technical indicators", responses: { "200": { description: "Indicator data" } } } },
                "/api/v1/sentiment": { get: { summary: "Sentiment analysis", responses: { "200": { description: "Sentiment data" } } } },
                "/api/v1/calendar": { get: { summary: "Economic calendar", responses: { "200": { description: "Calendar events" } } } },
                "/api/v1/reports/{symbol}": { get: { summary: "Technical report", responses: { "200": { description: "Report" } } } },
            }
        },
        dom_id: "#swagger-ui",
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
        layout: "StandaloneLayout"
    });
    </script>
</body>
</html>"""


@app.route("/api/admin/keys", methods=["GET", "POST"])
def api_admin_keys():
    """Manage API keys. Protected by MOHMD_TOKEN."""
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        token = request.headers.get("X-Auth-Token", "").strip() or request.args.get("token", "").strip()
    expected = os.environ.get("MOHMD_TOKEN", "").strip() or _MOHMD_TOKEN
    if not expected or token != expected:
        return jsonify({"error": "unauthorized"}), 403
    
    if request.method == "POST":
        data = request.get_json() or {}
        name = data.get("name", "unnamed")
        rate_limit = int(data.get("rate_limit", 100))
        key = _generate_api_key()
        key_hash = _hash_api_key(key)
        _api_keys[key_hash]['name'] = name
        _api_keys[key_hash]['rate_limit'] = rate_limit
        _save_api_keys()
        return jsonify({"ok": True, "key": key, "name": name, "rate_limit": rate_limit})
    
    # GET: list keys (without revealing full keys)
    return jsonify({
        "ok": True,
        "keys": [
            {"hash": k, "name": v['name'], "rate_limit": v['rate_limit'],
             "requests_today": v['requests_today']}
            for k, v in _api_keys.items()
        ],
    })


# ---------------------------------------------------------------------------
# Phase 10 — TradingView Webhook Receiver & Alerts
# ---------------------------------------------------------------------------
from integrations.tv_webhook import process_webhook, get_recent_alerts, get_alerts_for_ticker

TV_WEBHOOK_SECRET = CONFIG.get('tv_webhook_secret', '')

@app.route("/webhook/tv", methods=["POST"])
def webhook_tv():
    """Receive TradingView webhook alerts."""
    payload = request.get_json(silent=True) or {}
    secret = CONFIG.get('tv_webhook_secret', '') or TV_WEBHOOK_SECRET
    result = process_webhook(payload, secret)
    
    if result.get('ok') and _discord_bot:
        # Forward to Discord
        action_emoji = '🟢' if str(payload.get('action', '')).lower() == 'buy' else '🔴' if str(payload.get('action', '')).lower() == 'sell' else 'ℹ️'
        _discord_bot.send_alert(
            f"TradingView: {payload.get('ticker')}",
            f"{action_emoji} {payload.get('action', 'N/A')} @ {payload.get('price', 'N/A')}\n{payload.get('message', '')}",
        )
    
    status = 200 if result.get('ok') else 400
    return jsonify(result), status


@app.route("/api/alerts")
def api_alerts():
    """Get recent TradingView alerts."""
    ticker = request.args.get('ticker')
    if ticker:
        alerts = get_alerts_for_ticker(ticker)
    else:
        alerts = get_recent_alerts()
    return jsonify({"ok": True, "alerts": alerts})


# ---------------------------------------------------------------------------
# Phase 11 — AI Features (Summaries, Predictions, Anomalies)
# ---------------------------------------------------------------------------
@app.route("/api/ai/summary/<symbol>")
@require_tier("ai_summaries_daily")
def api_ai_summary(symbol):
    """Get AI summary for an asset."""
    sym = symbol.upper()
    with STATE_LOCK:
        summary = STATE.get('ai_summaries', {}).get(sym)
    if not summary:
        try:
            from ai_features import get_ai_summary
            with STATE_LOCK:
                live = list(STATE.get('articles', []))
            summary = get_ai_summary(sym, live)
            if summary:
                with STATE_LOCK:
                    STATE.setdefault('ai_summaries', {})[sym] = summary
        except Exception:
            pass
    if summary:
        return jsonify({"ok": True, "symbol": sym, **summary})
    return jsonify({"ok": False, "error": "no summary available"}), 404


@app.route("/api/ai/predictions")
@require_tier("ai_predictions")
def api_ai_predictions():
    """Get sentiment predictions for all assets."""
    with STATE_LOCK:
        preds = STATE.get('predictions', {})
    if not preds:
        try:
            from ai_features import get_all_predictions
            with STATE_LOCK:
                live = list(STATE.get('articles', []))
            preds = get_all_predictions(live)
            with STATE_LOCK:
                STATE['predictions'] = preds
        except Exception:
            pass
    return jsonify({"ok": True, "predictions": preds or {}})


@app.route("/api/ai/anomalies")
def api_ai_anomalies():
    """Get current anomalies."""
    with STATE_LOCK:
        anomalies = STATE.get('anomalies', [])
    return jsonify({"ok": True, "anomalies": anomalies})


# ---------------------------------------------------------------------------
# Content studio — which story is worth making, and in what shape
# ---------------------------------------------------------------------------
# Ranking runs over the live corpus; the demand half comes from social_signals,
# whose providers refresh themselves in their own thread. Nothing here waits on
# the network, and a missing provider lowers the score rather than raising an
# error — a studio that cannot rank is worse than one that ranks on less.

_STUDIO_CACHE = {"ts": 0.0, "payload": None}
_STUDIO_LOCK = threading.Lock()
STUDIO_FEED_TTL = 90.0


def _studio_config():
    with _CONFIG_LOCK:
        cfg = CONFIG.get("content_studio")
        return dict(cfg) if isinstance(cfg, dict) else {}


def _studio_feed(force: bool = False, limit: int = 25):
    import content_studio, social_signals
    social_signals.set_config(CONFIG)
    now = time.time()
    with _STUDIO_LOCK:
        cached_payload = _STUDIO_CACHE.get("payload")
        if (not force and cached_payload and (now - _STUDIO_CACHE.get("ts", 0)) < STUDIO_FEED_TTL):
            return cached_payload

    with STATE_LOCK:
        articles = list(STATE.get("articles") or [])
    signals = social_signals.all_signals()
    if force:
        social_signals.warm(CONFIG, force=True)
    try:
        import database
        recent = database.studio_recent_keys(float(_studio_config().get("repeat_penalty_hours") or 48))
    except Exception:
        recent = set()
    result = content_studio.rank(articles, CONFIG, signals, now=now, recent_keys=recent)
    result["items"] = result["items"][:max(1, int(limit))]
    result["corpus"] = len(articles)
    result["status"] = content_studio.status(CONFIG)
    result["providers"] = [
        {"key": k, "label": v["label"], "source": v["source"],
         "age": v["age"], "error": v["error"], "ready": bool(v["value"])}
        for k, v in social_signals.snapshot_all().items()
    ]
    with _STUDIO_LOCK:
        _STUDIO_CACHE["ts"], _STUDIO_CACHE["payload"] = now, result
    return result


@app.route("/api/studio/feed")
def api_studio_feed():
    """The ranked board: what to make today, and why each item ranks where it does."""
    if request.args.get("refresh") in ("1", "true", "yes"):
        with _STUDIO_LOCK:
            _STUDIO_CACHE["ts"] = 0.0
    try:
        limit = max(1, min(60, int(request.args.get("limit") or 25)))
    except (TypeError, ValueError):
        limit = 25
    try:
        payload = _studio_feed(force=False, limit=limit)
    except Exception as e:
        log(f"studio feed failed: {e}")
        return jsonify({"ok": True, "items": [], "notes": [f"ساخت فهرست با خطا مواجه شد: {e}"],
                        "providers": [], "warming": True})
    return jsonify({"ok": True, **payload})


@app.route("/api/studio/item/<aid>")
def api_studio_item(aid):
    """One ranked item on its own (used when the tab is reopened on a link)."""
    payload = _studio_feed(limit=60)
    for item in payload.get("items") or []:
        if item.get("id") == aid:
            return jsonify({"ok": True, "item": item, "status": payload.get("status")})
    return jsonify({"ok": False, "error": "not found", "hint": "خبر از فهرست امروز بیرون رفته است."}), 404


@app.route("/api/studio/draft", methods=["POST"])
def api_studio_draft():
    """Draft one story: caption + carousel + video script."""
    import content_studio
    data = request.get_json(silent=True) or {}
    aid = str(data.get("article_id") or data.get("id") or "").strip()
    if not aid:
        return jsonify({"ok": False, "error": "article_id required"}), 400
    with STATE_LOCK:
        article = next((a for a in (STATE.get("articles") or []) if a.get("id") == aid), None)
    if not article:
        return jsonify({"ok": False, "error": "article not in the live corpus"}), 404
    payload = _studio_feed(limit=60)
    item = next((i for i in payload.get("items") or [] if i.get("id") == aid), None)
    fmt = (item or {}).get("format") or content_studio.format_scores(article, {})
    use_ai = data.get("use_ai")
    use_ai = True if use_ai is None else bool(use_ai)
    result = content_studio.draft(article, fmt, use_ai=use_ai)
    row_id = 0
    try:
        import database
        row_id = database.save_studio_content(aid, article.get("title_fa") or article.get("title") or "",
                                             content_studio._title_key(article),
                                             float((item or {}).get("score") or 0),
                                             (item or {}).get("factors") or {}, fmt, result,
                                             result.get("method") or "template")
    except Exception as e:
        log(f"studio draft persist failed: {e}")
    return jsonify({"ok": True, "id": row_id, "article_id": aid, "format": fmt,
                    "title": article.get("title_fa") or article.get("title") or aid,
                    "score": (item or {}).get("score"), "draft": result,
                    "source": article.get("source_name") or article.get("source_key") or "",
                    "credibility": article.get("credibility"), "link": article.get("link")})


@app.route("/api/studio/drafts")
def api_studio_drafts():
    """What was drafted before, newest first, with where it went."""
    try:
        import database
        return jsonify({"ok": True, "drafts": database.studio_content_list(40),
                        "posted": database.studio_posted_stats(30)})
    except Exception as e:
        log(f"studio drafts failed: {e}")
        return jsonify({"ok": True, "drafts": [], "posted": []})


# ---------------------------------------------------------------------------
# Channel board — what belongs on the gold/coin page
# ---------------------------------------------------------------------------
# Deliberately separate from /api/studio/feed even though both read the same
# corpus. The studio answers "what is worth making anywhere"; this answers the
# narrower "would this page run it", and a page's identity is mostly a refusal.
# It is a pure function over the live articles, so the payload is cached for a
# short window and never touches the network.

_CHANNEL_CACHE = {"ts": 0.0, "payload": None}
_CHANNEL_LOCK = threading.Lock()
CHANNEL_FEED_TTL = 60.0
_CHANNEL_MAX = 80          # the endpoint clamp; the cache always holds this width


def _channel_board(force: bool = False):
    """The whole ranked board, cached for CHANNEL_FEED_TTL seconds.

    Ranked once at the full width and cached whole. Storing whichever ``limit``
    the first caller happened to ask for would let a small probe (a health
    check, another tab) shrink everyone else's board for the rest of the
    minute — a lens must not reshape what the next reader sees.
    """
    import channel_profile
    now = time.time()
    with _CHANNEL_LOCK:
        cached = _CHANNEL_CACHE.get("payload")
        if (not force and cached and (now - _CHANNEL_CACHE.get("ts", 0)) < CHANNEL_FEED_TTL):
            return cached

    with STATE_LOCK:
        articles = list(STATE.get("articles") or [])
        market = dict(STATE.get("market") or {})

    with _CONFIG_LOCK:
        cfg = dict(CONFIG.get("channel_board") or {})
    result = channel_profile.rank_for_channel(
        articles, now=now, limit=_CHANNEL_MAX,
        min_credibility=float(cfg.get("min_credibility") or 0.55),
        market=market,
    )
    result["status"] = {
        "min_credibility": float(cfg.get("min_credibility") or 0.55),
        "corpus": len(articles),
    }
    with _CHANNEL_LOCK:
        _CHANNEL_CACHE["ts"], _CHANNEL_CACHE["payload"] = now, result
    return result


def _channel_feed(limit: int = 40, force: bool = False):
    import channel_profile
    return channel_profile.slice_board(_channel_board(force=force), limit)


try:
    import orjson as _orjson          # 3-5x faster than the stdlib on the
except ImportError:                   # ~1.4 MB /api/data bundle; optional
    _orjson = None

def _fast_json(payload):
    """orjson-backed JSON response for the big poll payloads; falls back to
    Flask's jsonify when orjson is not installed."""
    if _orjson is not None:
        try:
            return Response(_orjson.dumps(payload), mimetype="application/json")
        except TypeError:
            pass          # something orjson refuses — the stdlib path is lenient
    return jsonify(payload)

_WHALE_CACHE = {"ts": 0.0, "data": None}

@app.route("/api/whales/live")
def api_whales_live():
    """Real on-chain whale moves — mempool.space public API (free, key-less).

    The mempool *is* the whale wire: every large transfer sits there for the
    ~10 minutes it takes to confirm, with its exact satoshi value. Big BTC
    moves only (>= 1 BTC); USD via the live BTC quote when available.
    60s cache — the mempool churns every second, the tab does not need to.
    """
    now = time.time()
    if _WHALE_CACHE["data"] and now - _WHALE_CACHE["ts"] < 60:
        return jsonify({"ok": True, **_WHALE_CACHE["data"]})
    try:
        r = requests.get("https://mempool.space/api/mempool/recent",
                         headers=HEADERS, timeout=10)
        r.raise_for_status()
        txs = r.json() or []
        btc_price = ((live_prices() or {}).get("BTC") or {}).get("price")
        sats_btc = 1e8
        whales = []
        for t in txs:
            val_btc = (t.get("value") or 0) / sats_btc
            if val_btc < 1.0:
                continue
            whales.append({
                "id": "live-" + str(t.get("txid", ""))[:12],
                "asset": "BTC",
                "amount": round(val_btc, 2),
                "usd": round(val_btc * btc_price) if btc_price else None,
                "fee_sat": t.get("fee"),
                "hash": str(t.get("txid", ""))[:10],
                "tag": "میم‌پول — در انتظار تأیید",
            })
        whales.sort(key=lambda x: -x["amount"])
        whales = whales[:12]
        data = {"whales": whales, "count": len(whales), "ts": now}
        _WHALE_CACHE["ts"], _WHALE_CACHE["data"] = now, data
        return jsonify({"ok": True, **data})
    except Exception as e:
        if _WHALE_CACHE["data"]:
            return jsonify({"ok": True, **_WHALE_CACHE["data"], "stale": True})
        return jsonify({"ok": False, "whales": [], "error": str(e)})


@app.route("/api/studio/card")
def api_studio_card():
    """The story as a ready-to-post Persian PNG (1080×1350, DL6 palette).

    Drawn server-side from the article's own fields — shaped with
    arabic_reshaper, direction-fixed with python-bidi, set in the self-hosted
    Vazirmatn. 503 (never a broken image) when the shaping stack or the font
    is missing."""
    aid = (request.args.get("aid") or "").strip()
    art = None
    with STATE_LOCK:
        pool = list(STATE.get("articles") or []) + list(STATE.get("archive") or [])
        art = next((a for a in pool if a.get("id") == aid), None)
    if not art:
        return jsonify({"ok": False, "error": "article_not_found"}), 404
    try:
        from card_render import render_news_card, CardUnavailable
        png = render_news_card(art)
    except CardUnavailable as e:
        return jsonify({"ok": False, "error": str(e)}), 503
    except Exception as e:
        log(f"card render failed: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    return Response(png, mimetype="image/png",
                    headers={"Cache-Control": "no-cache"})


@app.route("/api/channel/feed")
def api_channel_feed():
    """The page's board: every story that fits it, with its lane and its card.

    ``limit`` is clamped; ``refresh=1`` bypasses the 60 s cache. A failure here
    returns an empty board with a note instead of a 500 — an empty tab that says
    why is better than a dead request the client cannot distinguish from an
    empty corpus.
    """
    if request.args.get("refresh") in ("1", "true", "yes"):
        with _CHANNEL_LOCK:
            _CHANNEL_CACHE["ts"] = 0.0
    try:
        limit = max(1, min(80, int(request.args.get("limit") or 40)))
    except (TypeError, ValueError):
        limit = 40
    try:
        payload = _channel_feed(limit=limit)
    except Exception as e:
        log(f"channel feed failed: {e}")
        return jsonify({"ok": True, "items": [], "notes": [f"ساخت فهرست با خطا مواجه شد: {e}"],
                        "warming": True})
    # The board is explainable server-side, but the client asked for *news
    # only* — the ranking internals (viral factors, fit, why-text, captions)
    # stop at the server and never ship to the browser.
    slim = [{
        "id": it.get("id", ""),
        "title": it.get("title", ""),
        "title_fa": it.get("title_fa", ""),
        "summary_fa": it.get("summary_fa", ""),
        "source": it.get("source", ""),
        "link": it.get("link", ""),
        "age_hours": it.get("age_hours"),
        "published_ts": it.get("published_ts"),
        "primary_bucket": it.get("primary_bucket", ""),
        "bucket_label": it.get("bucket_label", ""),
    } for it in (payload.get("items") or [])]
    return jsonify({"ok": True, "items": slim,
                    "scanned": payload.get("scanned"),
                    "generated_ts": payload.get("generated_ts")})


def _tg_send_photo(token, chat, png_bytes, caption=""):
    """Send one PNG to a Telegram chat. Used for carousel slides."""
    try:
        files = {"photo": ("slide.png", png_bytes, "image/png")}
        payload = {"chat_id": chat, "disable_notification": "true"}
        if caption:
            payload["caption"] = caption[:1000]
        r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                          data=payload, files=files, timeout=30)
        return r.status_code == 200, (r.text or "")[:400]
    except Exception as e:
        return False, str(e)[:200]


@app.route("/api/studio/publish/telegram", methods=["POST"])
def api_studio_publish_telegram():
    """Send a drafted piece to the configured Telegram channel.

    Guarded twice: the bot token/chat must exist in settings, and unless
    ``confirm`` is true this only reports what it *would* send. Publishing to a
    real channel is not something a stray click should do.
    """
    import base64
    import binascii
    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()
    photos = data.get("photos") or []
    content_id = int(data.get("content_id") or 0)
    confirm = bool(data.get("confirm"))
    if not text and not photos:
        return jsonify({"ok": False, "error": "nothing to send"}), 400
    token, chat = _telegram_cfg()
    if not token or not chat:
        return jsonify({"ok": False, "error": "telegram not configured",
                        "hint": "توکن ربات و شناسهٔ چت را در تنظیمات وارد کنید."}), 400
    limit = 3
    blobs = []
    for raw in photos[:limit]:
        raw = str(raw or "")
        if raw.startswith("data:"):
            raw = raw.split(",", 1)[-1]
        try:
            blobs.append(base64.b64decode(raw, validate=False))
        except (binascii.Error, ValueError):
            return jsonify({"ok": False, "error": "bad image payload"}), 400
    if not confirm:
        return jsonify({"ok": True, "dry_run": True, "text_chars": len(text),
                        "images": len(blobs),
                        "preview": text[:600],
                        "hint": "پیش‌نمایش است؛ برای ارسال واقعی confirm بفرستید."})
    sent = []
    ok_text = True
    if text:
        res_text = _tg_send(token, chat, text)
        ok_text = bool(res_text)
        sent.append({"kind": "message", "ok": ok_text, "info": "" if ok_text else getattr(res_text, "error", "")})
    for blob in blobs:
        ok, info = _tg_send_photo(token, chat, blob)
        sent.append({"kind": "photo", "ok": bool(ok), "info": "" if ok else info})
    try:
        import database
        if content_id:
            database.mark_studio_posted(content_id, "telegram", "", json.dumps(sent, ensure_ascii=False))
    except Exception as e:
        log(f"studio publish record failed: {e}")
    return jsonify({"ok": True, "dry_run": False, "sent": sent,
                    "ok_all": all(s["ok"] for s in sent) if sent else False})


@app.route("/api/studio/publish/bale", methods=["POST"])
def api_studio_publish_bale():
    """Send a drafted piece to the configured Bale channel or chat.

    Guarded twice: the bot token and chat must exist in settings, and unless
    ``confirm`` is true this only reports what it *would* send.
    """
    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()
    content_id = int(data.get("content_id") or 0)
    confirm = bool(data.get("confirm"))
    if not text:
        return jsonify({"ok": False, "error": "nothing to send"}), 400
    token, chat = _bale_cfg()
    if not token or not chat:
        return jsonify({"ok": False, "error": "bale not configured",
                        "hint": "توکن ربات و شناسهٔ چت پیام‌رسان بله را در تنظیمات وارد کنید."}), 400
    if not confirm:
        return jsonify({"ok": True, "dry_run": True, "text_chars": len(text),
                        "preview": text[:600],
                        "hint": "پیش‌نمایش است؛ برای ارسال واقعی confirm بفرستید."})
    res = _bale_send(token, chat, text)
    is_ok = bool(res)
    err = "" if is_ok else getattr(res, "error", "ارسال ناموفق بود")
    sent = [{"kind": "message", "ok": is_ok, "info": err}]
    try:
        import database
        if content_id and is_ok:
            database.mark_studio_posted(content_id, "bale", "", json.dumps(sent, ensure_ascii=False))
    except Exception as e:
        log(f"studio bale publish record failed: {e}")
    return jsonify({"ok": is_ok, "dry_run": False, "sent": sent,
                    "error": err if not is_ok else None,
                    "ok_all": is_ok})


@app.route("/api/studio/signals/refresh", methods=["POST"])
def api_studio_signals_refresh():
    """Ask the demand providers to re-fetch now (they answer from cache meanwhile)."""
    try:
        import social_signals
        social_signals.warm(CONFIG, force=True)
        with _STUDIO_LOCK:
            _STUDIO_CACHE["ts"] = 0.0
        return jsonify({"ok": True, "providers": [
            {"key": k, "label": v["label"], "age": v["age"], "error": v["error"]}
            for k, v in social_signals.snapshot_all().items()]})
    except Exception as e:
        log(f"studio signals refresh failed: {e}")
        return jsonify({"ok": False, "error": str(e)[:200]}), 500


@app.route("/api/studio/config", methods=["GET", "POST"])
def api_studio_config():
    """Read or update the studio's settings (gates, weights, sources, keys)."""
    import social_signals
    if request.method == "POST":
        incoming = request.get_json(silent=True) or {}
        if not isinstance(incoming, dict):
            return jsonify({"ok": False, "error": "body must be an object"}), 400
        numeric = {"credibility_gate", "half_life_hours", "repeat_penalty", "min_score"}
        listy = {"youtube_queries_fa", "youtube_queries_en", "youtube_channels",
                 "telegram_channels", "reddit_subs"}
        with _CONFIG_LOCK:
            cur = CONFIG.setdefault("content_studio", {})
            if not isinstance(cur, dict):
                cur = CONFIG["content_studio"] = {}
            for key, val in incoming.items():
                if key in numeric:
                    try:
                        cur[key] = float(val)
                    except (TypeError, ValueError):
                        continue
                elif key in listy:
                    if isinstance(val, str):
                        val = [v.strip() for v in val.split(",") if v.strip()]
                    if isinstance(val, list):
                        cur[key] = [str(v)[:120] for v in val][:30]
                elif key in ("weights", "asset_weights"):
                    if isinstance(val, dict):
                        # only the factors the scorer actually reads: an unknown
                        # key would sit in the config looking meaningful and
                        # changing nothing
                        import content_studio
                        known = (set(content_studio.DEFAULT_WEIGHTS) if key == "weights"
                                 else set(content_studio.DEFAULT_ASSET_WEIGHTS))
                        cur[key] = {str(k)[:8].upper() if key == "asset_weights" else str(k)[:16]: float(v)
                                    for k, v in val.items()
                                    if isinstance(v, (int, float))
                                    and (str(k).lower() in known if key == "weights"
                                         else str(k).upper() in known)}
                elif key in ("youtube_key", "instagram_token", "instagram_user_id",
                             "enabled"):
                    cur[key] = val if isinstance(val, bool) else str(val)[:400]
                elif key == "auto_post" and isinstance(val, dict):
                    cur[key] = {k: bool(v) for k, v in val.items()}
        save_config()
        social_signals.set_config(CONFIG)
        with _STUDIO_LOCK:
            _STUDIO_CACHE["ts"] = 0.0
    cfg = _studio_config()
    masked = dict(cfg)
    for secret in ("youtube_key", "instagram_token"):
        if masked.get(secret):
            masked[secret] = "***set***"
    return jsonify({"ok": True, "config": masked,
                    "has_youtube_key": bool(cfg.get("youtube_key")),
                    "has_instagram": bool(cfg.get("instagram_token") and cfg.get("instagram_user_id"))})





 
 
@app.route("/api/ai/config", methods=["GET", "POST"])
def api_ai_config():
    """Inspect or update AI configuration (OpenAI / OpenRouter API key and model)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        key = (data.get("openai_key") or data.get("openrouter_key") or data.get("api_key") or "").strip()
        model = (data.get("openai_model") or data.get("model") or "").strip()
        base_url = (data.get("base_url") or "").strip()
        with _CONFIG_LOCK:
            ai_cfg = CONFIG.setdefault("ai", {})
            if _is_secret_mask(key):
                pass  # round-tripped masked field — keep the stored key
            elif "openai_key" in data or "openrouter_key" in data or "api_key" in data:
                ai_cfg["openai_key"] = key
                ai_cfg["enabled"] = bool(key)
            if model:
                ai_cfg["openai_model"] = model
            if "base_url" in data:
                ai_cfg["base_url"] = base_url
            save_config()
            _init_ai_config()
        key_eff = (CONFIG.get("ai", {}).get("openai_key") or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
        base_eff = CONFIG.get("ai", {}).get("base_url") or os.environ.get("OPENAI_BASE_URL") or ""
        provider = "OpenRouter" if (key_eff.startswith("sk-or-") or "openrouter" in base_eff.lower()) else ("OpenAI" if key_eff else "None")
        return jsonify({
            "ok": True,
            "has_key": bool(key_eff),
            "provider": provider,
            "model": CONFIG.get("ai", {}).get("openai_model", "gpt-4o-mini")
        })

    ai_cfg = CONFIG.get("ai", {})
    key = (ai_cfg.get("openai_key") or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    base_url = ai_cfg.get("base_url") or os.environ.get("OPENAI_BASE_URL") or ""
    masked = (key[:8] + "..." + key[-4:]) if len(key) > 14 else ("***" if key else "")
    provider = "OpenRouter" if (key.startswith("sk-or-") or "openrouter" in base_url.lower()) else ("OpenAI" if key else "None")
    return jsonify({
        "ok": True,
        "has_key": bool(key),
        "key_masked": masked,
        "provider": provider,
        "model": ai_cfg.get("openai_model", "gpt-4o-mini")
    })


# ---------------------------------------------------------------------------
# Phase 12 — Freemium & Billing APIs
# ---------------------------------------------------------------------------
@app.route("/api/billing/tier")
def api_billing_tier():
    """Check current user tier."""
    from billing import get_user_tier
    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    tier = get_user_tier(api_key)
    return jsonify({"ok": True, **tier})


@app.route("/api/billing/upgrade", methods=["POST"])
def api_billing_upgrade():
    """Upgrade to Pro.

    Self-service only on loopback — the single-user, self-hosted case this was
    written for. It used to mint a full Pro key (rate_limit 1000 plus
    ai_predictions, rag_qa, advanced_charts and export) for anyone who could
    POST an email address, with no payment and no confirmation, and the whole
    /api/billing/ prefix is exempt from the shared-secret gate, so on a LAN or
    public bind that was an open door.

    Everywhere else it needs the operator's token: MOHMD_UPGRADE_TOKEN when set,
    otherwise the same shared secret that guards the rest of the API. That
    header is the hook a real payment provider or an admin script would carry;
    wiring Stripe means replacing this check, not the key minting below.
    """
    from billing import register_user
    import secrets
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    if not email:
        return jsonify({"error": "email required"}), 400

    remote = (request.remote_addr or "")
    loopback = remote in ("127.0.0.1", "::1", "localhost") or remote.startswith("127.")
    if not loopback:
        expected = (os.environ.get("MOHMD_UPGRADE_TOKEN") or _MOHMD_TOKEN or "").strip()
        given = (request.headers.get("X-Upgrade-Token") or data.get("upgrade_token") or "").strip()
        if not expected or given != expected:
            return jsonify({
                "ok": False,
                "error": "payment required",
                "hint": "upgrade is self-service on localhost only; otherwise send "
                        "X-Upgrade-Token with the operator's MOHMD_UPGRADE_TOKEN",
            }), 403

    api_key = f"fb_pro_{secrets.token_hex(24)}"
    result = register_user(email, api_key, tier='pro')

    if result['ok']:
        key_hash = _hash_api_key(api_key)
        _api_keys[key_hash] = {
            'name': email,
            'created': time.time(),
            'rate_limit': 1000,
            'requests_today': 0,
            'last_reset': time.time(),
        }
        _save_api_keys()
        result['api_key'] = api_key  # Only shown once
        result['message'] = "Save this API key — it won't be shown again"

    return jsonify(result)


@app.route("/api/billing/usage")
def api_billing_usage():
    """Check current usage stats."""
    from billing import get_user_tier, _get_conn, _lock
    import hashlib

    api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
    tier = get_user_tier(api_key)

    if not api_key:
        return jsonify({"ok": True, "usage": {}, "tier": "free"})

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]

    with _lock:
        conn = _get_conn()
        try:
            row = conn.execute("SELECT id FROM users WHERE api_key_hash = ?", (key_hash,)).fetchone()
            if not row:
                return jsonify({"ok": True, "usage": {}, "tier": "free"})

            today = time.strftime('%Y-%m-%d')
            usage = conn.execute(
                "SELECT feature, COUNT(*) as count FROM usage_log WHERE user_id = ? AND timestamp >= ? GROUP BY feature",
                (row['id'], today)
            ).fetchall()

            return jsonify({
                "ok": True,
                "tier": tier['tier'],
                "usage": {r['feature']: r['count'] for r in usage},
                "limits": {
                    'api': tier.get('api_limit', 100),
                    'alerts': tier.get('alerts_limit', 3),
                },
            })
        finally:
            conn.close()



def _article_blurb_fa(art, content):
    """One short Persian paragraph: what this news actually is.
    Built from the Persian summary when present, else translated from the
    first full-text paragraph, else from the RSS summary. Cached per article."""
    aid = art.get("id")
    if not aid:
        return ""
    key = "blurb|" + aid
    with _CONTENT_LOCK:
        if key in CONTENT_CACHE:
            return CONTENT_CACHE[key]
    parts = []
    topic_fa = art.get("topic_fa") or ""
    assets = " و ".join((art.get("assets") or [])[:3])
    lead = ""
    paras = (content or {}).get("paragraphs") or []
    base = (art.get("summary_fa") or (paras[0] if paras else art.get("summary") or "")).strip()
    if base:
        # first 1–2 sentences, capped ~280 chars
        sents = re.split(r"(?<=[.!?؟])\s+", base)
        lead = " ".join(sents[:2])[:280]
    if lead:
        scope = f"خبری از دسته «{topic_fa}»" + (f" درباره {assets}" if assets else "")
        parts.append(f"{scope}.")
        parts.append(lead)
        if (content or {}).get("partial"):
            parts.append("متن کامل به‌دلیل پی‌وال ناقص دریافت شده است.")
        cred = int(round((art.get("credibility") or 0) * 100))
        parts.append(f"اعتبار محتوایی این خبر {fa_digits(cred)}٪ برآورد شده و منبع آن {art.get('source_name','')} است.")
    out = " ".join(parts)
    # never freeze a blurb built while the body was still pending — the next
    # poll should get the paragraph-based version
    if out and not (content or {}).get("pending"):
        with _CONTENT_LOCK:
            CONTENT_CACHE[key] = out
    return out


@app.route("/api/article/<art_id>")
def api_article(art_id):
    with STATE_LOCK:
        art = next((a for a in STATE["articles"] if a["id"] == art_id), None)
        arts = list(STATE["articles"])
    if not art:
        return jsonify({"error": "not_found"}), 404

    want_fa = request.args.get("fa") in ("1", "true", "yes")
    content = article_content_cached(art)
    pending = bool(content.get("pending"))

    # Fallback to article summary if content has 0 paragraphs so users never see an empty screen
    if not content.get("paragraphs") and (art.get("summary") or art.get("summary_fa")):
        s_text = art.get("summary") or art.get("summary_fa") or ""
        s_paras = [p.strip() for p in re.split(r'\n+|\.\s+', s_text) if len(p.strip()) > 15]
        if s_paras:
            content = dict(content)
            content["paragraphs"] = s_paras
            content["word_count"] = sum(len(p.split()) for p in s_paras)
            content["partial"] = True
            content["via"] = "summary-fallback"

    # full Persian body: served from cache, otherwise translated in the
    # background and picked up by the client's next poll
    content_fa = None
    if want_fa:
        with _FA_CONTENT_LOCK:
            cached_fa = FA_CONTENT_CACHE.get(art["id"] + "|fa")
        if cached_fa:
            content_fa = cached_fa
        elif pending or not content.get("paragraphs"):
            pending = True           # body still extracting -> FA follows it
        elif _schedule_fa(art, content):
            pending = True

    # short Persian blurb: what this news is about (one compact paragraph)
    blurb_fa = _article_blurb_fa(art, content)

    # Related stories, but ranked by *readability*: when this article is
    # paywalled or bot-walled and no text could be extracted, the same story is
    # usually also covered by outlets whose body we already have. Those lead the
    # list so the reader has something real to read instead of a dead end.
    rel, seen_titles = [], set()
    for a in arts:
        if a["id"] == art_id:
            continue
        overlap = set(a.get("assets", [])) & set(art.get("assets", []))
        if not (overlap or a.get("topic") == art.get("topic")):
            continue
        # the same wire story is republished by several outlets word for word;
        # five copies of one headline is not a reading list
        norm = re.sub(r"[^a-z0-9\u0600-\u06ff]", "", (a.get("title_fa") or a.get("title") or "").lower())[:70]
        if norm and norm in seen_titles:
            continue
        seen_titles.add(norm)
        with _CONTENT_LOCK:
            c_entry = CONTENT_CACHE.get(a["id"])
        rel.append({"id": a["id"], "title": a.get("title_fa") or a["title"],
                    "source": a.get("source_name", ""), "score": len(overlap),
                    "full": bool(_content_fresh(c_entry)) and
                            (c_entry.get("word_count") or 0) >= 120})
    rel.sort(key=lambda x: (-int(x["full"]), -x["score"]))

    return jsonify({
        **_ser_article(art),
        "summary_full": art.get("summary", ""),
        "summary_full_fa": art.get("summary_fa", ""),
        "content": content,
        "content_fa": content_fa,
        "pending": pending,
        "blurb_fa": blurb_fa,
        "related": rel[:5],
    })


IMAGE_CACHE_DIR = BASE_DIR / ".cache" / "images"
IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/api/proxy-image")
def api_proxy_image():
    """Proxy and disk-cache external news thumbnails to bypass hotlink protection (403)."""
    raw_url = request.args.get("url", "").strip()
    if not raw_url or not (raw_url.startswith("http://") or raw_url.startswith("https://")):
        return Response("bad_url", status=400)
    import hashlib
    url_hash = hashlib.sha256(raw_url.encode("utf-8")).hexdigest()
    cached_file = IMAGE_CACHE_DIR / url_hash
    meta_file = IMAGE_CACHE_DIR / (url_hash + ".meta")

    if cached_file.exists() and meta_file.exists():
        try:
            mime = meta_file.read_text(encoding="utf-8").strip()
            data = cached_file.read_bytes()
            return Response(data, mimetype=mime, headers={"Cache-Control": "public, max-age=86400"})
        except Exception:
            pass

    try:
        from urllib.parse import urlparse
        # ── DL2 hardening ────────────────────────────────────────────────
        # This endpoint fetches an arbitrary URL on the server's behalf, so it
        # is a textbook SSRF/DoS surface when the app is reachable from a
        # network: block internal addresses and cap the payload.
        import ipaddress
        import socket
        MAX_IMG_BYTES = 6 * 1024 * 1024
        domain = (urlparse(raw_url).netloc or "").split("@")[-1].split(":")[0].strip()

        def _blocked_host(host: str) -> bool:
            if not host:
                return True
            lowered = host.lower()
            if lowered in ("localhost", "metadata.google.internal") or lowered.endswith(".local"):
                return True
            try:
                for _fam, _t, _p, _c, sockaddr in socket.getaddrinfo(host, None):
                    ip = ipaddress.ip_address(sockaddr[0])
                    if (ip.is_private or ip.is_loopback or ip.is_link_local
                            or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                        return True
            except Exception:
                return True
            return False

        if _blocked_host(domain):
            return Response("blocked_host", status=403)
        hdrs = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": f"https://{domain}/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
        r = requests.get(raw_url, headers=hdrs, timeout=8, allow_redirects=False, stream=True)
        for _ in range(3):
            if r.status_code in (301, 302, 303, 307, 308):
                location = r.headers.get("Location", "")
                loc_domain = (urlparse(location).netloc or "").split("@")[-1].split(":")[0].strip()
                if _blocked_host(loc_domain):
                    r.close()
                    return Response("blocked_host", status=403)
                r.close()
                r = requests.get(location, headers=hdrs, timeout=8, allow_redirects=False, stream=True)
            else:
                break

        try:
            declared = int(r.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            declared = 0
        if declared > MAX_IMG_BYTES:
            r.close()
            return Response("too_large", status=413)

        content_bytes = r.content
        if len(content_bytes or b"") > MAX_IMG_BYTES:
            r.close()
            return Response("too_large", status=413)

        if r.status_code == 200:
            mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            if mime.startswith("image/") and len(content_bytes) > 100:
                try:
                    import tempfile
                    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=IMAGE_CACHE_DIR)
                    try:
                        with os.fdopen(tmp_fd, "wb") as f:
                            f.write(content_bytes)
                        os.replace(tmp_path, cached_file)
                    except Exception:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                        raise
                    meta_file.write_text(mime, encoding="utf-8")
                except Exception:
                    pass
                return Response(content_bytes, mimetype=mime, headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        pass
    return Response("not_found", status=404)


@app.route("/api/report/<sym>")
def api_report(sym):
    sym = sym.upper()
    meta_all = all_assets_meta()
    if sym not in meta_all:
        return jsonify({"error": "unknown_symbol"}), 404
    meta = meta_all[sym]
    with STATE_LOCK:
        rep = STATE["reports"].get(sym)
        arts = list(STATE["articles"])
        md = STATE["market"].get(sym, {})

    if not rep:
        try:
            rep = build_report(sym, md, arts, name=meta.get("name"),
                               fa_name=meta.get("fa"), is_crypto=meta.get("is_crypto"),
                               icon=meta.get("icon"),
                               max_age=CONFIG.get("report_max_age_hours", MAX_AGE_HOURS))
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    lang = (request.args.get("lang") or "en").lower()
    if lang == "fa":
        rep = translate_report(rep)

    payload = dict(rep)
    payload["chart"] = chart_payload(md, sym, meta)
    payload["lang"] = lang
    return jsonify(payload)


def translate_report(rep):
    """Fill the Persian slot of every text section (real translation, cached)."""
    sym = rep.get("symbol")
    stamp = rep.get("generated_at")
    with _FA_REPORT_LOCK:
        if sym in FA_REPORT_CACHE and FA_REPORT_CACHE[sym][0] == stamp:
            return FA_REPORT_CACHE[sym][1]

    texts = [v["en"] for k, v in rep.get("sections", []) if k == "p" and v.get("en")]
    try:
        table = translate_many(texts)
        save_cache()
    except Exception as e:
        log(f"  x report translation failed: {e}")
        table = {}

    sections = []
    for kind, val in rep.get("sections", []):
        if kind == "p" and isinstance(val, dict):
            sections.append((kind, {**val, "fa": table.get(val.get("en", "")) or val.get("en", "") or ""}))
        elif kind == "meta":
            sections.append((kind, {**val,
                                    "asof_fa": val.get("asof_fa") or fa_datetime(val.get("asof"))}))
        else:
            sections.append((kind, val))
    out = {**rep, "sections": sections, "translated": True}
    with _FA_REPORT_LOCK:
        FA_REPORT_CACHE[sym] = (stamp, out)
    return out


def report_to_markdown(rep, include_sources: bool = True):
    """include_sources=False → analysis prose only (no citation blocks)."""
    lines = []
    for kind, val in rep.get("sections", []):
        if kind == "meta":
            lines.append(f"# {val.get('title')}")
            lines.append(f"As of: {val.get('asof')} | Price: {val.get('price')}")
            continue
        if kind == "h":
            lines.append(f"\n## {val.get('en')}\n")
        elif kind == "p":
            lines.append((val.get("en") or "") + "\n")
        elif kind == "cites" and include_sources:
            lines.append(f"\n### {val.get('title_fa', 'منابع')}\n")
            for it in val.get("items", []):
                lines.append(f"- [{it.get('index_fa')}] {it.get('title_fa')} "
                             f"— {it.get('source')} — {it.get('datetime_fa')} "
                             f"({it.get('credibility_fa')}) {it.get('link')}")
            lines.append("")
    return "\n".join(lines)


def report_to_markdown_fa(rep, include_sources: bool = True):
    lines = []
    for kind, val in rep.get("sections", []):
        if kind == "meta":
            lines.append(f"# {val.get('title_fa')}")
            lines.append(f"زمان گزارش: {val.get('asof_fa')} | قیمت: {val.get('price')}")
            continue
        if kind == "h":
            lines.append(f"\n## {val.get('fa')}\n")
        elif kind == "p":
            lines.append((val.get("fa") or val.get("en") or "") + "\n")
        elif kind == "cites" and include_sources:
            lines.append(f"\n### {val.get('title_fa', 'منابع')}\n")
            for it in val.get("items", []):
                lines.append(f"- [{it.get('index_fa')}] {it.get('title_fa')} — "
                             f"{it.get('source')} — {it.get('datetime_fa')} — {it.get('link')}")
            lines.append("")
    return "\n".join(lines)


@app.route("/api/report/<sym>/markdown")
def api_report_markdown(sym):
    sym = sym.upper()
    lang = (request.args.get("lang") or "en").lower()
    with STATE_LOCK:
        rep = STATE["reports"].get(sym)
    if not rep:
        return jsonify({"error": "not_ready"}), 404
    with_sources = request.args.get("sources", "1") not in ("0", "false", "no")
    if lang == "fa":
        rep = translate_report(rep)
        return Response(report_to_markdown_fa(rep, include_sources=with_sources),
                        mimetype="text/markdown; charset=utf-8")
    return Response(report_to_markdown(rep, include_sources=with_sources),
                    mimetype="text/markdown; charset=utf-8")


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    with STATE_LOCK:
        if STATE['stats'].get('cycle_running'):
            return jsonify({"ok": False, "error": "cycle already running"}), 429

    with _LIVE_LOCK:
        if time.time() - _last_refresh[0] < 30:
            return jsonify({"ok": False, "error": "refresh cooldown"}), 429
        _last_refresh[0] = time.time()

    threading.Thread(target=run_cycle, kwargs={"reason": "manual"}, daemon=True).start()
    return jsonify({"status": "started"})


# ---------------------------------------------------------------------------
# source monitoring — why each feed is down (Persian) + one-click recovery
# ---------------------------------------------------------------------------
REASON_FA = {
    "not_found":      "Feed URL is gone (404) — publisher moved or removed the RSS",
    "bot_blocked":    "Site blocks bots (403) — firewall/Cloudflare is rejecting us",
    "auth_required":  "Feed requires authentication (401) — no longer public",
    "rate_limited":   "Rate limited (429) — the server is throttling us; it usually reopens later",
    "server_error":   "Publisher's server is down (5xx) — their side; we will retry",
    "ssl_error":      "SSL certificate problem — the site's certificate chain failed verification",
    "timeout":        "No response (timeout) — the server answered too slowly",
    "dns_or_network": "Network/DNS failure — the host did not resolve at all",
    "redirect_loop":  "Endless redirect loop — the feed URL is broken",
    "http_error":     "Unexpected HTTP response from the publisher",
    "empty_feed":     "Feed is alive but returns 0 items — publisher is temporarily quiet",
    "exception":      "Unknown error while fetching",
    "circuit_open":   "مدار این منبع باز است — چند چرخه پیاپی خطا داد و موقتاً با فاصله‌ی فزاینده کنار گذاشته شد (خودکار برمی‌گردد)",
}


def _monitor_view():
    """Per-source monitoring rows with a root-cause for every failure."""
    rows = []
    with STATE_LOCK:
        for s in all_sources_view():
            st = STATE["sources_status"].get(s["key"], {})
            reason = st.get("reason")
            rows.append({
                "key": s["key"], "name": s["name"], "url": s["url"],
                "kind_fa": s.get("kind_fa"), "enabled": s["enabled"],
                "ok": bool(s.get("last_ok")), "count": s.get("last_count") or 0,
                "http": st.get("http"),
                "recovered": bool(st.get("recovered")),
                "recovery": st.get("recovery") or [],
                "mirror": bool(st.get("mirror")),
                "reason": reason,
                "reason_fa": REASON_FA.get(reason) if reason else None,
                "detail": st.get("error"),
                "checked_fa": fa_time(st.get("at")),
                "hist": list(STATE["src_hist"].get(s["key"], [])),
            })
    broken = [r for r in rows if r["enabled"] and not r["ok"]]
    recovered = [r for r in rows if r["recovered"]]
    return {
        "total": len(rows),
        "ok": len(rows) - len(broken),
        "broken": len(broken),
        "recovered_now": len(recovered),
        "rows": rows,
    }


@app.route("/api/econ")
def api_econ():
    """Market context bundle: calendar (this+next week), F&G, ETF flows, macro, sessions."""
    try:
        ctx = market_context()
    except Exception as e:
        ctx = {"error": str(e)}
    ctx["macro"] = _macro_cached()
    try:
        ctx["sessions"] = market_sessions()
    except Exception:
        ctx["sessions"] = []
    return jsonify(ctx)


@app.route("/api/ideas")
def api_ideas():
    """TradingView public ideas for ONE asset (?sym=BTC or ?sym=DOGE).

    Each item comes with the chart image, the idea text (snippet + body) and a
    permalink that actually resolves, so the ideas tab can show a card per idea
    and filter per asset. Cached server-side for 30 min; degrades to ok:false.
    """
    sym = (request.args.get("sym") or "BTC").upper().strip()
    sort = (request.args.get("sort") or "popular").lower()
    kind = (request.args.get("kind") or "all").lower()
    try:
        limit = int(request.args.get("limit") or 30)
    except Exception:
        limit = 30
    limit = max(1, min(60, limit))
    tag = TAG_BY_ASSET.get(sym) or (sym.lower() if sym else "btcusd")
    try:
        bundle = fetch_idea_asset(sym, limit=limit, sort=sort, kind=kind)
        return jsonify({"ok": True, **bundle})
    except Exception as e:
        return jsonify({"ok": False, "sym": sym, "tag": tag, "error": str(e),
                        "url": ideas_page_url(tag), "items": []})


IDEA_FA_CACHE = {}                 # "sym|id" -> {"title_fa", "paragraphs"}
_IDEA_INFLIGHT: set = set()


def _idea_paragraphs(text: str) -> list:
    """One idea body -> paragraph list (blank-line separated, like news)."""
    return [p.strip() for p in re.split(r"\n{2,}", (text or "").strip()) if p.strip()]


def _schedule_idea_fa(key: str, idea: dict) -> bool:
    """Translate one idea off-thread (title + body), same contract as news:
    the response says pending:true and the client polls until it lands."""
    if key in _IDEA_INFLIGHT or key in IDEA_FA_CACHE:
        return False
    paras = _idea_paragraphs(idea.get("body") or idea.get("snippet"))
    if not paras and not idea.get("title"):
        return False
    _IDEA_INFLIGHT.add(key)

    def _job():
        try:
            fa = translate_paragraphs(paras[:40]) if paras else []
            title_fa = translate_one(idea.get("title") or "") or ""
            save_cache()
            IDEA_FA_CACHE[key] = {"title_fa": title_fa, "paragraphs": fa}
        except Exception as e:
            log(f"  x idea translation failed: {e}")
        finally:
            _IDEA_INFLIGHT.discard(key)

    threading.Thread(target=_job, daemon=True).start()
    return True


@app.route("/api/ideas/translate")
def api_ideas_translate():
    """Persian version of one idea (the modal's «ترجمهٔ فارسی» button).

    Never blocks: the first call schedules the translation and answers
    pending:true — the modal polls until the Persian text is ready.
    """
    sym = (request.args.get("sym") or "BTC").upper().strip()
    idea_id = (request.args.get("id") or "").strip()
    if not idea_id:
        return jsonify({"ok": False, "error": "missing_id"}), 400
    idea = find_idea(sym, idea_id)
    if not idea:
        return jsonify({"ok": False, "error": "not_cached"})
    key = f"{sym}|{idea_id}"
    hit = IDEA_FA_CACHE.get(key)
    if hit:
        return jsonify({"ok": True, "pending": False, "cached": True, **hit})
    pending = _schedule_idea_fa(key, idea)
    return jsonify({"ok": True, "pending": pending or key in _IDEA_INFLIGHT,
                    "cached": False, "title_fa": "", "paragraphs": []})


# ---------------------------------------------------------------------------
# alerts: price/keyword (browser) + telegram digest (server, after each cycle)
# ---------------------------------------------------------------------------
TG_LOCK = threading.Lock()


def _tg_clean_token(tok):
    tok = str(tok or "").strip().strip('"').strip("'")
    if tok.lower().startswith("bot"):
        sub = tok[3:]
        if ":" in sub:
            tok = sub.strip()
    return tok


def _tg_clean_chat(chat):
    chat = str(chat or "").strip().strip('"').strip("'")
    if chat.startswith("https://t.me/"):
        chat = "@" + chat[len("https://t.me/"):].strip("/")
    elif chat.startswith("t.me/"):
        chat = "@" + chat[len("t.me/"):].strip("/")
    elif chat.startswith("telegram.me/"):
        chat = "@" + chat[len("telegram.me/"):].strip("/")
    if chat and not chat.startswith(("@", "-")) and not chat.isdigit():
        chat = "@" + chat
    return chat


class TgResult:
    def __init__(self, ok: bool, error: str = "", raw: dict = None):
        self.ok = bool(ok)
        self.error = str(error or "")
        self.raw = raw or {}

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f"<TgResult ok={self.ok} error={self.error!r}>"


def _telegram_cfg():
    tg = CONFIG.get("telegram") or {}
    import os as _os
    token = (tg.get("token") or "") or _os.environ.get("MOHMD_TG_TOKEN", "")
    chat = (tg.get("chat") or "") or _os.environ.get("MOHMD_TG_CHAT", "")
    return _tg_clean_token(token), _tg_clean_chat(chat)


def _tg_parse_error(r):
    try:
        data = r.json()
    except Exception:
        data = {}
    desc = data.get("description") or (r.text if hasattr(r, "text") else "") or ""
    code = data.get("error_code") or getattr(r, "status_code", 0)
    low = desc.lower()
    if "unauthorized" in low:
        msg = "توکن ربات نامعتبر است (Unauthorized). توکن را از BotFather بررسی کنید."
    elif "chat not found" in low:
        msg = "شناسهٔ چت یافت نشد (Chat not found). اگر کانال است، آیدی را با @ وارد کنید یا ربات را عضو کانال نمایید."
    elif "bot was blocked by the user" in low:
        msg = "ربات توسط شما بلاک شده یا استارت نشده است. در تلگرام وارد ربات شده و Start را بزنید."
    elif "bot is not a member" in low:
        msg = "ربات عضو این کانال یا گروه نیست. ابتدا ربات را به عنوان ادمین کانال اضافه کنید."
    elif "not enough rights" in low:
        msg = "ربات دسترسی ارسال پیام در این کانال/گروه را ندارد. دسترسی ارسال پیام (Post Messages) را به ربات بدهید."
    elif "can't parse entities" in low:
        msg = "خطا در فرمت کاراکترهای پیام تلگرام."
    elif "message is too long" in low:
        msg = "طول پیام بیش از حد مجاز تلگرام است."
    elif "too many requests" in low or code == 429:
        msg = "محدودیت تعداد درخواست تلگرام (Rate limit). کمی صبر کنید."
    else:
        msg = f"خطای تلگرام ({code}): {desc}" if desc else f"خطای تلگرام ({code})"
    return msg, data


def _tg_send(token, chat, text, silent=False):
    token = _tg_clean_token(token)
    chat = _tg_clean_chat(chat)
    if not token or not chat:
        return TgResult(False, "توکن یا شناسهٔ چت تلگرام خالی است")
    if not text:
        return TgResult(False, "متن پیام خالی است")

    import re
    # Convert markdown **bold** to <b>bold</b> if present for HTML parse mode
    text_html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", str(text))

    payload = {
        "chat_id": chat,
        "text": text_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "disable_notification": bool(silent),
    }

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload,
            timeout=15,
        )
        if r.status_code == 200:
            return TgResult(True, raw=r.json() if r.content else {})

        err_msg, raw = _tg_parse_error(r)
        desc = (raw.get("description") or "").lower()
        if "can't parse entities" in desc:
            import re
            payload_plain = dict(payload)
            payload_plain.pop("parse_mode", None)
            payload_plain["text"] = re.sub(r"<[^>]+>", "", text)
            r2 = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json=payload_plain,
                timeout=15,
            )
            if r2.status_code == 200:
                return TgResult(True, raw=r2.json() if r2.content else {})
            err_msg, raw = _tg_parse_error(r2)

        return TgResult(False, err_msg, raw)
    except requests.exceptions.Timeout:
        return TgResult(False, "مهلت اتصال به سرور تلگرام به پایان رسید (Timeout).")
    except requests.exceptions.ConnectionError:
        return TgResult(False, "خطای اتصال به api.telegram.org (اینترنت یا فیلترینگ را بررسی کنید).")
    except Exception as e:
        return TgResult(False, f"خطای پیش‌بینی‌نشده: {e}")


def _tg_escape(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _tg_render_digest(articles, tg):
    """Render the digest message from the saved template + settings.
    Supports: hyperlink on title, asset hashtags, emoji, summary on/off,
    credibility stars, Persian or English text, adhering to 17 financial editorial standards."""
    import news_editorial
    tpl = (tg.get("template") or TG_TEMPLATE_DEFAULT)
    fa = (tg.get("language") or "fa") == "fa"
    include_link = tg.get("include_link", True)
    include_summary = tg.get("include_summary", True)
    hashtags = tg.get("hashtags", True)
    emoji = tg.get("emoji", True)
    show_stars = tg.get("show_stars", True)
    if len(articles) == 1:
        lines = []
    else:
        header = tg.get("header") or ("🦅 <b>MOHMD NEWS</b> — خبرهای معتبر چرخه اخیر" if fa
                                      else "🦅 <b>MOHMD NEWS</b> — latest validated news")
        lines = [header + f"\n🕐 {_tg_escape(fa_datetime(datetime.now(timezone.utc)))}\n"]
    for i, a in enumerate(articles, 1):
        raw_title = a.get("title_fa") or a.get("title") or ""
        clean_title = news_editorial.clean_editorial_title(raw_title)
        title = _tg_escape(clean_title)
        url = _tg_escape(a.get("link") or "")
        title_html = f'<a href="{url}">{title}</a>' if (include_link and url) else title
        cred = int(round((a.get("credibility") or 0) * 100))
        stars = "★" * max(1, round(cred / 20)) if show_stars else ""
        assets = [x for x in (a.get("assets") or [])][:3]
        if fa:
            assets_txt = "، ".join(_ASSET_FA_TG.get(x, x) for x in assets) if assets else "—"
        else:
            assets_txt = ", ".join(assets) if assets else "—"
        tags = " ".join("#" + x for x in assets) if hashtags else ""

        # 2-4 sentences summary retaining key numbers and market drivers
        raw_summ = a.get("summary_fa") or a.get("summary") or ""
        summ_clean, takeaway = news_editorial.format_editorial_summary(raw_summ)
        summ = _tg_escape(summ_clean)

        market_tag = news_editorial.detect_market_emoji(a) if emoji else ""
        lead = "" if ("{market_emoji}" in tpl or "{emoji}" in tpl) else (f"{market_tag} " if market_tag else "")

        key_point_str = f"📌 <b>نکته کلیدی:</b> {_tg_escape(takeaway)}\n\n" if (takeaway and "{key_point}" in tpl) else ""
        link_line = ("🔗 " + url) if (include_link and url and tg.get("link_on_own_line")) else ""

        msg = tpl.format(index=fa_digits(i) if fa else i,
                         title=title_html,
                         summary_fa=(summ + "\n\n") if (include_summary and summ) else "",
                         source=_tg_escape(a.get("source_name", "")),
                         cred=(str(fa_digits(cred)) if fa else str(cred)),
                         stars=stars, assets=_tg_escape(assets_txt), tags=tags,
                         time_fa=_tg_escape(fa_time(a.get("published_ts"))),
                         link_line=link_line,
                         emoji=market_tag,
                         market_emoji=market_tag,
                         key_point=key_point_str)
        if not include_summary:
            msg = "\n".join(l for l in msg.splitlines() if l.strip())
        lines.append(lead + msg.strip())
    return "\n\n".join(lines)[:4000]


_ASSET_FA_TG = {"BTC": "بیت‌کوین", "ETH": "اتریوم", "SOL": "سولانا", "XRP": "ریپل",
                "ADA": "کاردانو", "BNB": "بی‌ان‌بی", "DOGE": "دوج‌کوین",
                "LINK": "چین‌لینک", "XAU": "طلا", "XAG": "نقره"}


# ---------------------------------------------------------------------------
# Bale Messenger (پیام‌رسان بله)
# ---------------------------------------------------------------------------
BALE_LOCK = threading.Lock()


def _bale_clean_token(tok):
    tok = str(tok or "").strip().strip('"').strip("'")
    if tok.lower().startswith("bot"):
        sub = tok[3:]
        if ":" in sub:
            tok = sub.strip()
    return tok


def _bale_clean_chat(chat):
    chat = str(chat or "").strip().strip('"').strip("'")
    if chat.startswith("https://ble.ir/"):
        chat = "@" + chat[len("https://ble.ir/"):].strip("/")
    elif chat.startswith("ble.ir/"):
        chat = "@" + chat[len("ble.ir/"):].strip("/")
    elif chat.startswith("https://bale.ai/"):
        chat = "@" + chat[len("https://bale.ai/"):].strip("/")
    elif chat.startswith("bale.ai/"):
        chat = "@" + chat[len("bale.ai/"):].strip("/")
    if chat and not chat.startswith(("@", "-")) and not chat.isdigit():
        chat = "@" + chat
    return chat


def _bale_cfg():
    bale = CONFIG.get("bale") or {}
    import os as _os
    token = (bale.get("token") or "") or _os.environ.get("MOHMD_BALE_TOKEN", "")
    chat = (bale.get("chat") or "") or _os.environ.get("MOHMD_BALE_CHAT", "")
    return _bale_clean_token(token), _bale_clean_chat(chat)


def _bale_parse_error(r):
    try:
        data = r.json()
    except Exception:
        data = {}
    desc = data.get("description") or (r.text if hasattr(r, "text") else "") or ""
    code = data.get("error_code") or getattr(r, "status_code", 0)
    low = desc.lower()
    if "token not found" in low or "unauthorized" in low:
        msg = "توکن ربات بله نامعتبر است. توکن را از BotFather@ در پیام‌رسان بله دریافت کنید."
    elif "chat not found" in low:
        msg = "شناسهٔ چت یا کانال بله یافت نشد. اگر کانال است، آیدی را با @ وارد کرده یا ربات را عضو کانال نمایید."
    elif "blocked" in low:
        msg = "ربات در بله مسدود شده یا هنوز دکمه شروع (Start) زده نشده است."
    elif "not a member" in low:
        msg = "ربات عضو این کانال یا گروه بله نیست. ابتدا ربات را به عنوان مدیر (Admin) کانال اضافه کنید."
    elif "not enough rights" in low:
        msg = "ربات دسترسی ارسال پیام در این کانال یا گروه بله را ندارد."
    else:
        msg = f"خطای پیام‌رسان بله ({code}): {desc}" if desc else f"خطای بله ({code})"
    return msg, data


def _bale_send(token, chat, text, silent=False):
    token = _bale_clean_token(token)
    chat = _bale_clean_chat(chat)
    if not token or not chat:
        return TgResult(False, "توکن یا شناسهٔ چت بله خالی است")
    if not text:
        return TgResult(False, "متن پیام خالی است")

    payload = {
        "chat_id": chat,
        "text": text,
        "disable_notification": bool(silent),
    }

    try:
        r = requests.post(
            f"https://tapi.bale.ai/bot{token}/sendMessage",
            json=payload,
            timeout=15,
        )
        if r.status_code == 200:
            return TgResult(True, raw=r.json() if r.content else {})

        err_msg, raw = _bale_parse_error(r)
        return TgResult(False, err_msg, raw)
    except requests.exceptions.Timeout:
        return TgResult(False, "مهلت اتصال به سرور بله به پایان رسید (Timeout).")
    except requests.exceptions.ConnectionError:
        return TgResult(False, "خطای اتصال به api پیام‌رسان بله (tapi.bale.ai).")
    except Exception as e:
        return TgResult(False, f"خطای پیش‌بینی‌نشده: {e}")


def _bale_render_digest(articles, bale):
    """Render digest message formatted cleanly for Bale messenger, adhering to 17 financial editorial standards."""
    import news_editorial
    tpl = (bale.get("template") or BALE_TEMPLATE_DEFAULT)
    fa = (bale.get("language") or "fa") == "fa"
    include_link = bale.get("include_link", True)
    include_summary = bale.get("include_summary", True)
    hashtags = bale.get("hashtags", True)
    emoji = bale.get("emoji", True)
    show_stars = bale.get("show_stars", True)
    if len(articles) == 1:
        lines = []
    else:
        header = bale.get("header") or ("🦅 MOHMD NEWS — معتبرترین خبرهای بازار" if fa
                                        else "🦅 MOHMD NEWS — latest validated news")
        lines = [header + f"\n🕐 {fa_datetime(datetime.now(timezone.utc))}\n"]
    for i, a in enumerate(articles, 1):
        raw_title = a.get("title_fa") or a.get("title") or ""
        title = news_editorial.clean_editorial_title(raw_title)
        url = a.get("link") or ""
        cred = int(round((a.get("credibility") or 0) * 100))
        stars = "★" * max(1, round(cred / 20)) if show_stars else ""
        assets = [x for x in (a.get("assets") or [])][:3]
        if fa:
            assets_txt = "، ".join(_ASSET_FA_TG.get(x, x) for x in assets) if assets else "—"
        else:
            assets_txt = ", ".join(assets) if assets else "—"
        tags = " ".join("#" + x for x in assets) if hashtags else ""

        # 2-4 sentences summary retaining key numbers and market drivers
        raw_summ = a.get("summary_fa") or a.get("summary") or ""
        summ_clean, takeaway = news_editorial.format_editorial_summary(raw_summ)
        summ = summ_clean

        market_tag = news_editorial.detect_market_emoji(a) if emoji else ""
        lead = "" if ("{market_emoji}" in tpl or "{emoji}" in tpl) else (f"{market_tag} " if market_tag else "")

        key_point_str = f"📌 **نکته کلیدی:** {takeaway}\n\n" if (takeaway and "{key_point}" in tpl) else ""
        link_line = ("🔗 " + url) if (include_link and url) else ""

        msg = tpl.format(index=fa_digits(i) if fa else i,
                         title=title,
                         summary_fa=(summ + "\n\n") if (include_summary and summ) else "",
                         source=a.get("source_name", ""),
                         cred=(str(fa_digits(cred)) if fa else str(cred)),
                         stars=stars, assets=assets_txt, tags=tags,
                         time_fa=fa_time(a.get("published_ts")),
                         link_line=link_line,
                         emoji=market_tag,
                         market_emoji=market_tag,
                         key_point=key_point_str)
        if not include_summary:
            msg = "\n".join(l for l in msg.splitlines() if l.strip())
        lines.append(lead + msg.strip())
    return "\n\n".join(lines)[:4000]


def _studio_autopost(articles=None):
    """Post the day's best-scoring story to Telegram, if the operator asked for it.

    Off by default, one post per cycle at most, never the same story twice
    (the studio's own posted log feeds the ranking's repeat penalty), and it
    obeys the same quiet hours as the digest: an automated channel is only
    welcome if it stays rare.
    """
    if not articles:
        with STATE_LOCK:
            articles = list(STATE.get("articles") or [])
    if not articles:
        return
    cs = CONFIG.get("content_studio") or {}
    auto = cs.get("auto_post") or {}
    if not cs.get("enabled", True) or not auto.get("telegram"):
        return
    token, chat = _telegram_cfg()
    if not token or not chat:
        return
    tg = CONFIG.get("telegram") or {}
    if tg.get("quiet_hours", True):
        try:
            hr = datetime.now(IRAN_TZ).hour
            if hr >= 23 or hr < 8:
                return
        except Exception:
            pass
    try:
        import content_studio
        import database
        import news_editorial
        import re
        recent = database.studio_recent_keys(float(cs.get("repeat_penalty_hours") or 48))
        signals = (content_studio_signals() or {})
        ranked = content_studio.rank(articles, CONFIG, signals, recent_keys=recent)
        top = next((i for i in ranked.get("items") or [] if not i.get("repeat")), None)
        if not top:
            return
        with STATE_LOCK:
            article = next((a for a in (STATE.get("articles") or []) if a.get("id") == top["id"]), None)
        if not article:
            article = top
        result = content_studio.draft(article, top.get("format"), use_ai=True)
        text = (result.get("caption") or "").strip()
        if not text:
            text = news_editorial.format_editorial_post(article, target="telegram_html")
        else:
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        tags = " ".join(result.get("hashtags") or [])
        if tags and tags not in text:
            text = (text + "\n\n" + tags).strip()
        row_id = database.save_studio_content(top["id"], top.get("title_fa") or "",
                                             content_studio._title_key(article),
                                             top.get("score") or 0, top.get("factors") or {},
                                             top.get("format") or {}, result,
                                             result.get("method") or "template")
        with TG_LOCK:
            ok = _tg_send(token, chat, text, silent=False)
        if ok:
            database.mark_studio_posted(row_id, "telegram", "auto",
                                        json.dumps({"score": top.get("score")}, ensure_ascii=False))
            database.mark_messenger_posted(top["id"], "telegram")
            log(f"[studio] auto-posted «{top.get('title_fa', '')[:40]}» (score {top.get('score')})")
            return ok
    except Exception as e:
        log(f"[studio] autopost skipped: {e}")
        return False


@app.route("/api/studio/autopost/now", methods=["POST"])
def api_studio_autopost_now():
    """Immediately trigger Content Studio auto-post to Telegram without waiting for cycle."""
    try:
        with STATE_LOCK:
            arts = list(STATE.get("articles") or [])
        if not arts:
            return jsonify({"ok": False, "error": "هیچ خبری در سیستم موجود نیست."})
        token, chat = _telegram_cfg()
        if not token or not chat:
            return jsonify({"ok": False, "error": "تنظیمات تلگرام (توکن یا شناسه چت) تنظیم نشده است."})

        import content_studio
        import database
        import news_editorial
        import re
        cs = CONFIG.get("content_studio") or {}
        recent = database.studio_recent_keys(float(cs.get("repeat_penalty_hours") or 48))
        signals = (content_studio_signals() or {})
        ranked = content_studio.rank(arts, CONFIG, signals, recent_keys=recent)
        top = next((i for i in ranked.get("items") or [] if not i.get("repeat")), None)
        if not top:
            items = ranked.get("items") or []
            top = items[0] if items else None
        if not top:
            return jsonify({"ok": False, "error": "خبری واجد شرایط در استودیو پیدا نشد."})

        with STATE_LOCK:
            article = next((a for a in (STATE.get("articles") or []) if a.get("id") == top["id"]), None)
        if not article:
            article = top

        result = content_studio.draft(article, top.get("format"), use_ai=True)
        text = (result.get("caption") or "").strip()
        if not text:
            text = news_editorial.format_editorial_post(article, target="telegram_html")
        else:
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

        tags = " ".join(result.get("hashtags") or [])
        if tags and tags not in text:
            text = (text + "\n\n" + tags).strip()

        row_id = database.save_studio_content(top["id"], top.get("title_fa") or "",
                                             content_studio._title_key(article),
                                             top.get("score") or 0, top.get("factors") or {},
                                             top.get("format") or {}, result,
                                             result.get("method") or "template")
        with TG_LOCK:
            res = _tg_send(token, chat, text, silent=False)
        if res:
            database.mark_studio_posted(row_id, "telegram", "manual_auto",
                                        json.dumps({"score": top.get("score")}, ensure_ascii=False))
            database.mark_messenger_posted(top["id"], "telegram")
            return jsonify({
                "ok": True,
                "title": top.get("title_fa") or article.get("title_fa") or "",
                "score": top.get("score"),
                "text": text
            })
        else:
            return jsonify({"ok": False, "error": res.error or "خطا در ارسال به تلگرام."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def content_studio_signals():
    """Live demand signals for the auto-post path (import kept local on purpose)."""
    try:
        import social_signals
        social_signals.set_config(CONFIG)
        return social_signals.all_signals()
    except Exception:
        return {}


def _post_cycle_telegram(articles):
    """Post qualified articles individually to Telegram with deduplication."""
    token, chat = _telegram_cfg()
    if not token or not chat:
        return
    tg = CONFIG.get("telegram") or {}
    if tg.get("enabled") is False:
        return
    if tg.get("quiet_hours", True):
        try:
            hr = datetime.now(IRAN_TZ).hour
            if hr >= 23 or hr < 8:
                return
        except Exception:
            pass
    import database
    import time
    min_cred = float(tg.get("min_credibility") or 0.70)
    max_items = int(tg.get("max_items") or 10)
    max_age = float(tg.get("max_age_hours") or 24)
    asset_filter = set(tg.get("asset_filter") or [])
    strong = [a for a in articles
              if (a.get("credibility") or 0) >= min_cred and (a.get("age_hours") or 999) <= max_age]
    if asset_filter:
        strong = [a for a in strong if asset_filter & set(a.get("assets") or [])]
    strong.sort(key=lambda a: -(a.get("published_ts") or 0))

    # Send each unposted article individually
    unposted = [a for a in strong if not database.is_messenger_posted(a.get("id"), "telegram")]
    candidates = unposted[:max_items]
    if not candidates:
        return

    silent = bool(tg.get("silent"))
    pin = bool(tg.get("pin"))
    sent_count = 0
    for a in candidates:
        text = _tg_render_digest([a], tg)
        if not text.strip():
            continue
        with TG_LOCK:
            res = _tg_send(token, chat, text, silent=silent)
            if res:
                database.mark_messenger_posted(a.get("id"), "telegram")
                sent_count += 1
                if pin and sent_count == 1:
                    # pinChatMessage needs the message_id of the message just sent
                    msg_id = ((res.raw or {}).get("result") or {}).get("message_id")
                    if msg_id:
                        try:
                            requests.post(f"https://api.telegram.org/bot{token}/pinChatMessage",
                                          params={"chat_id": chat, "message_id": msg_id,
                                                  "disable_notification": True}, timeout=10)
                        except Exception:
                            pass
        time.sleep(0.5)


def _post_cycle_bale(articles):
    """Post qualified articles individually to Bale messenger with deduplication."""
    token, chat = _bale_cfg()
    if not token or not chat:
        return
    bale = CONFIG.get("bale") or {}
    if bale.get("enabled") is False:
        return
    if bale.get("quiet_hours", True):
        try:
            hr = datetime.now(IRAN_TZ).hour
            if hr >= 23 or hr < 8:
                return
        except Exception:
            pass
    import database
    import time
    min_cred = float(bale.get("min_credibility") or 0.70)
    max_items = int(bale.get("max_items") or 10)
    max_age = float(bale.get("max_age_hours") or 24)
    asset_filter = set(bale.get("asset_filter") or [])
    strong = [a for a in articles
              if (a.get("credibility") or 0) >= min_cred and (a.get("age_hours") or 999) <= max_age]
    if asset_filter:
        strong = [a for a in strong if asset_filter & set(a.get("assets") or [])]
    strong.sort(key=lambda a: -(a.get("published_ts") or 0))

    unposted = [a for a in strong if not database.is_messenger_posted(a.get("id"), "bale")]
    candidates = unposted[:max_items]
    if not candidates:
        return

    silent = bool(bale.get("silent"))
    for a in candidates:
        text = _bale_render_digest([a], bale)
        if not text.strip():
            continue
        with BALE_LOCK:
            res = _bale_send(token, chat, text, silent=silent)
            if res:
                database.mark_messenger_posted(a.get("id"), "bale")
        time.sleep(0.5)


def _post_cycle_alerts(articles):
    """Dispatch digests to configured messengers (Telegram, Bale)."""
    try:
        _post_cycle_telegram(articles)
    except Exception as e:
        log(f"telegram cycle alert error: {e}")
    try:
        _post_cycle_bale(articles)
    except Exception as e:
        log(f"bale cycle alert error: {e}")


@app.route("/api/telegram/get-chat-id", methods=["POST"])
def api_telegram_get_chat_id():
    """Detect bot info and recent chat IDs using getMe and getUpdates."""
    d = request.get_json(silent=True) or {}
    token = _tg_clean_token(d.get("token") or _telegram_cfg()[0])
    if not token:
        return jsonify({"ok": False, "error": "لطفاً ابتدا توکن ربات تلگرام را وارد کنید."}), 400

    try:
        r_me = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=12)
    except requests.exceptions.Timeout:
        return jsonify({"ok": False, "error": "مهلت اتصال به سرور تلگرام به پایان رسید (Timeout)."}), 504
    except Exception as e:
        return jsonify({"ok": False, "error": f"خطا در برقراری ارتباط با سرور تلگرام: {e}"}), 502

    if r_me.status_code != 200:
        err_msg, _ = _tg_parse_error(r_me)
        return jsonify({"ok": False, "error": err_msg}), 400

    bot_info = (r_me.json() or {}).get("result") or {}
    bot_user = bot_info.get("username") or bot_info.get("first_name") or "bot"

    try:
        r_up = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", timeout=12)
        up_data = r_up.json() if r_up.status_code == 200 else {}
    except Exception:
        up_data = {}

    updates = up_data.get("result") or []
    chats = {}
    for u in updates:
        for key in ("message", "channel_post", "edited_message", "my_chat_member"):
            obj = u.get(key)
            if isinstance(obj, dict) and "chat" in obj:
                c = obj["chat"]
                cid = c.get("id")
                if cid and cid not in chats:
                    title = c.get("title") or c.get("username") or f"{c.get('first_name','')} {c.get('last_name','')}".strip() or str(cid)
                    chats[cid] = {
                        "id": str(cid),
                        "title": title,
                        "type": c.get("type", "private"),
                        "username": c.get("username") or ""
                    }

    chat_list = list(chats.values())
    if chat_list:
        return jsonify({
            "ok": True,
            "bot_username": bot_user,
            "chats": chat_list,
            "recommended": chat_list[-1]["id"]
        })

    return jsonify({
        "ok": True,
        "bot_username": bot_user,
        "chats": [],
        "hint": f"ربات @{bot_user} متصل شد، اما چت فعالی ثبت نشده است. برای دریافت Chat ID: وارد تلگرام شوید، به @{bot_user} پیام بفرستید (دکمه Start) یا ربات را به کانال/گروه اضافه کرده و دوباره دکمه تشخیص خودکار را بزنید."
    })


@app.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    d = request.get_json(silent=True) or {}
    token = _tg_clean_token(d.get("token") or "")
    chat = _tg_clean_chat(d.get("chat") or "")
    if not token or not chat:
        saved_tok, saved_chat = _telegram_cfg()
        token = token or saved_tok
        chat = chat or saved_chat
    if not token or not chat:
        return jsonify({"ok": False, "error": "توکن ربات و شناسهٔ چت هر دو لازم هستند."})
    res = _tg_send(token, chat, "MOHMD NEWS test message — اتصال تلگرام برقرار است ✓")
    return jsonify({"ok": bool(res), "error": res.error if not res else ""})


@app.route("/api/telegram/preview", methods=["POST"])
def api_telegram_preview():
    """Render the digest exactly as it would be sent — but never send it."""
    with STATE_LOCK:
        arts = list(STATE["articles"])
    tg = CONFIG.get("telegram") or {}
    min_cred = float(tg.get("min_credibility") or 0.75)
    max_items = int(tg.get("max_items") or 10)
    max_age = float(tg.get("max_age_hours") or 6)
    asset_filter = set(tg.get("asset_filter") or [])
    strong = [a for a in arts
              if (a.get("credibility") or 0) >= min_cred and (a.get("age_hours") or 999) <= max_age]
    if asset_filter:
        strong = [a for a in strong if asset_filter & set(a.get("assets") or [])]
    strong.sort(key=lambda a: -(a.get("published_ts") or 0))
    strong = strong[:max_items]
    if not strong:
        return jsonify({"ok": False, "error": "nothing_matches_filters"})
    # A user template with a stray brace used to raise from str.format() and
    # answer 500 to the settings panel. The cycle path always had a guard; this
    # endpoint — the one the user actually types into — did not.
    try:
        text = _tg_render_digest(strong, tg)
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": "template_error",
            "detail": ("قالب ذخیره‌شده قابل رندر نیست؛ فقط {index}، {title}، {summary_fa}، "
                       "{source}، {cred}، {stars}، {assets}، {tags}، {time_fa} و "
                       "{link_line} مجاز هستند. " + str(e)),
        }), 400
    return jsonify({"ok": True, "text": text})


@app.route("/api/telegram/send-now", methods=["POST"])
def api_telegram_send_now():
    """Send qualified articles immediately to Telegram as individual messages."""
    with STATE_LOCK:
        arts = list(STATE.get("articles") or [])
    token, chat = _telegram_cfg()
    if not token or not chat:
        return jsonify({"ok": False, "error": "تنظیمات تلگرام (توکن یا شناسه چت) ذخیره نشده است."})
    if not arts:
        return jsonify({"ok": False, "error": "هیچ خبری در سیستم دریافت نشده است."})
    tg = CONFIG.get("telegram") or {}
    min_cred = float(tg.get("min_credibility") or 0.70)
    max_items = int(tg.get("max_items") or 5)
    max_age = float(tg.get("max_age_hours") or 24)
    asset_filter = set(tg.get("asset_filter") or [])
    strong = [a for a in arts
              if (a.get("credibility") or 0) >= min_cred and (a.get("age_hours") or 999) <= max_age]
    if asset_filter:
        strong = [a for a in strong if asset_filter & set(a.get("assets") or [])]
    strong.sort(key=lambda a: -(a.get("published_ts") or 0))
    if not strong:
        strong = sorted(arts, key=lambda a: -(a.get("published_ts") or 0))
    candidates = strong[:max_items]
    if not candidates:
        return jsonify({"ok": False, "error": "هیچ خبری برای ارسال یافت نشد."})

    import database
    import time
    sent = 0
    last_err = ""
    for a in candidates:
        text = _tg_render_digest([a], tg)
        if not text.strip():
            continue
        with TG_LOCK:
            res = _tg_send(token, chat, text, silent=bool(tg.get("silent")))
            if res:
                database.mark_messenger_posted(a.get("id"), "telegram")
                sent += 1
            else:
                last_err = res.error
        time.sleep(0.5)

    return jsonify({"ok": sent > 0, "sent": sent, "total": len(candidates), "error": last_err if sent == 0 else ""})


@app.route("/api/telegram/send", methods=["POST"])
def api_telegram_send():
    """Dispatch one arbitrary message to the configured chat.

    The smart-alert builder decides *when* a rule fires, but that decision is
    made in the browser and the bot token must never leave the server: the
    client posts the rendered text, the server holds the credential, the parse
    mode and the send lock. Telegram caps a message at 4096 characters, so a
    runaway template is rejected here rather than by the API.
    """
    d = request.get_json(silent=True) or {}
    text = (d.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "متن پیام خالی است."})
    if len(text) > 3500:
        return jsonify({"ok": False, "error": "طول متن بیش از ۳۵۰۰ کاراکتر است."})
    token, chat = _telegram_cfg()
    if not token or not chat:
        return jsonify({"ok": False, "error": "تنظیمات تلگرام ذخیره نشده است."})
    with TG_LOCK:
        res = _tg_send(token, chat, text, silent=bool(d.get("silent")))
    return jsonify({"ok": bool(res), "error": res.error if not res else ""})


# ---------------------------------------------------------------------------
# Bale endpoints
# ---------------------------------------------------------------------------
@app.route("/api/bale/get-chat-id", methods=["POST"])
def api_bale_get_chat_id():
    """Detect Bale bot info and recent chat IDs using getMe and getUpdates."""
    d = request.get_json(silent=True) or {}
    token = _bale_clean_token(d.get("token") or _bale_cfg()[0])
    if not token:
        return jsonify({"ok": False, "error": "لطفاً ابتدا توکن ربات بله را وارد کنید."}), 400

    try:
        r_me = requests.get(f"https://tapi.bale.ai/bot{token}/getMe", timeout=12)
    except requests.exceptions.Timeout:
        return jsonify({"ok": False, "error": "مهلت اتصال به سرور بله به پایان رسید (Timeout)."}), 504
    except Exception as e:
        return jsonify({"ok": False, "error": f"خطا در برقراری ارتباط با سرور بله: {e}"}), 502

    if r_me.status_code != 200:
        err_msg, _ = _bale_parse_error(r_me)
        return jsonify({"ok": False, "error": err_msg}), 400

    bot_info = (r_me.json() or {}).get("result") or {}
    bot_user = bot_info.get("username") or bot_info.get("first_name") or "bot"

    try:
        r_up = requests.get(f"https://tapi.bale.ai/bot{token}/getUpdates", timeout=12)
        up_data = r_up.json() if r_up.status_code == 200 else {}
    except Exception:
        up_data = {}

    updates = up_data.get("result") or []
    chats = {}
    for u in updates:
        for key in ("message", "channel_post", "edited_message"):
            obj = u.get(key)
            if isinstance(obj, dict) and "chat" in obj:
                c = obj["chat"]
                cid = c.get("id")
                if cid and cid not in chats:
                    title = c.get("title") or c.get("username") or f"{c.get('first_name','')} {c.get('last_name','')}".strip() or str(cid)
                    chats[cid] = {
                        "id": str(cid),
                        "title": title,
                        "type": c.get("type", "private"),
                        "username": c.get("username") or ""
                    }

    chat_list = list(chats.values())
    if chat_list:
        return jsonify({
            "ok": True,
            "bot_username": bot_user,
            "chats": chat_list,
            "recommended": chat_list[-1]["id"]
        })

    return jsonify({
        "ok": True,
        "bot_username": bot_user,
        "chats": [],
        "hint": f"ربات @{bot_user} متصل شد، اما چت فعالی ثبت نشده است. برای دریافت Chat ID: در بله به @{bot_user} پیام بفرستید (دکمه شروع) یا ربات را به کانال/گروه اضافه کرده و مجدداً روی دکمه تشخیص خودکار کلیک کنید."
    })


@app.route("/api/bale/test", methods=["POST"])
def api_bale_test():
    d = request.get_json(silent=True) or {}
    token = _bale_clean_token(d.get("token") or "")
    chat = _bale_clean_chat(d.get("chat") or "")
    if not token or not chat:
        saved_tok, saved_chat = _bale_cfg()
        token = token or saved_tok
        chat = chat or saved_chat
    if not token or not chat:
        return jsonify({"ok": False, "error": "توکن ربات و شناسهٔ چت بله هر دو لازم هستند."})
    res = _bale_send(token, chat, "MOHMD NEWS test message — اتصال پیام‌رسان بله برقرار است ✓")
    return jsonify({"ok": bool(res), "error": res.error if not res else ""})


@app.route("/api/bale/preview", methods=["POST"])
def api_bale_preview():
    """Render the Bale digest exactly as it would be sent."""
    with STATE_LOCK:
        arts = list(STATE["articles"])
    bale = CONFIG.get("bale") or {}
    min_cred = float(bale.get("min_credibility") or 0.70)
    max_items = int(bale.get("max_items") or 10)
    max_age = float(bale.get("max_age_hours") or 24)
    asset_filter = set(bale.get("asset_filter") or [])
    strong = [a for a in arts
              if (a.get("credibility") or 0) >= min_cred and (a.get("age_hours") or 999) <= max_age]
    if asset_filter:
        strong = [a for a in strong if asset_filter & set(a.get("assets") or [])]
    strong.sort(key=lambda a: -(a.get("published_ts") or 0))
    strong = strong[:max_items]
    if not strong:
        strong = sorted(arts, key=lambda a: -(a.get("published_ts") or 0))[:max_items]
    if not strong:
        return jsonify({"ok": False, "error": "nothing_matches_filters"})
    try:
        text = _bale_render_digest(strong, bale)
    except Exception as e:
        return jsonify({"ok": False, "error": "template_error", "detail": str(e)}), 400
    return jsonify({"ok": True, "text": text})


@app.route("/api/bale/send-now", methods=["POST"])
def api_bale_send_now():
    """Send qualified articles immediately to Bale as individual messages."""
    with STATE_LOCK:
        arts = list(STATE.get("articles") or [])
    token, chat = _bale_cfg()
    if not token or not chat:
        return jsonify({"ok": False, "error": "تنظیمات پیام‌رسان بله (توکن یا شناسه چت) ذخیره نشده است."})
    if not arts:
        return jsonify({"ok": False, "error": "هیچ خبری در سیستم دریافت نشده است."})
    bale = CONFIG.get("bale") or {}
    min_cred = float(bale.get("min_credibility") or 0.70)
    max_items = int(bale.get("max_items") or 5)
    max_age = float(bale.get("max_age_hours") or 24)
    asset_filter = set(bale.get("asset_filter") or [])
    strong = [a for a in arts
              if (a.get("credibility") or 0) >= min_cred and (a.get("age_hours") or 999) <= max_age]
    if asset_filter:
        strong = [a for a in strong if asset_filter & set(a.get("assets") or [])]
    strong.sort(key=lambda a: -(a.get("published_ts") or 0))
    if not strong:
        strong = sorted(arts, key=lambda a: -(a.get("published_ts") or 0))
    candidates = strong[:max_items]
    if not candidates:
        return jsonify({"ok": False, "error": "هیچ خبری برای ارسال یافت نشد."})

    import database
    import time
    sent = 0
    last_err = ""
    for a in candidates:
        text = _bale_render_digest([a], bale)
        if not text.strip():
            continue
        with BALE_LOCK:
            res = _bale_send(token, chat, text, silent=bool(bale.get("silent")))
            if res:
                database.mark_messenger_posted(a.get("id"), "bale")
                sent += 1
            else:
                last_err = res.error
        time.sleep(0.5)

    return jsonify({"ok": sent > 0, "sent": sent, "total": len(candidates), "error": last_err if sent == 0 else ""})


@app.route("/api/bale/send", methods=["POST"])
def api_bale_send():
    """Dispatch one arbitrary message to the configured Bale chat."""
    d = request.get_json(silent=True) or {}
    text = (d.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "متن پیام خالی است."})
    if len(text) > 3500:
        return jsonify({"ok": False, "error": "طول متن بیش از ۳۵۰۰ کاراکتر است."})
    token, chat = _bale_cfg()
    if not token or not chat:
        return jsonify({"ok": False, "error": "تنظیمات پیام‌رسان بله ذخیره نشده است."})
    with BALE_LOCK:
        res = _bale_send(token, chat, text, silent=bool(d.get("silent")))
    return jsonify({"ok": bool(res), "error": res.error if not res else ""})


@app.route("/api/monitor")
def api_monitor():
    # NOTE: no outer STATE_LOCK here — _monitor_view() takes the lock itself.
    # threading.Lock is non-reentrant: nesting them deadlocks the whole server
    # on the first /api/monitor request (every other route then queues forever).
    return jsonify({"ok": True, "monitor": _monitor_view()})


@app.route("/api/recover", methods=["POST"])
def api_recover():
    """One button for everything: run the DEEP recovery ladder (60+ distinct
    ways per broken feed: 14 user-agents, referer tricks, SSL-lenient, URL
    rewrites, 3 XML proxies, Wayback snapshot, Google-News/Bing mirrors and
    patient backoffs) across all broken feeds in parallel. Progress is
    pollable at /api/recover/status; when a feed comes back a fresh cycle
    pulls its news through the normal pipeline."""
    if RECOVERY_JOB["running"]:
        return jsonify({"status": "already_running", "job": _recover_view()})

    def _recover_worker():
        RECOVERY_JOB.update({"running": True, "done": 0, "total": 0, "fixed": 0,
                             "attempts": 0, "current": "", "log": [],
                             "started": time.time()})
        try:
            with STATE_LOCK:
                snapshot = dict(STATE["sources_status"])
            enabled = {k for k, on in CONFIG["sources_enabled"].items() if on}
            broken = [k for k, st in snapshot.items()
                      if k in enabled and k in SOURCES and not st.get("ok")]
            RECOVERY_JOB["total"] = len(broken)
            log(f"deep recovery: {len(broken)} broken feeds × 60+ ways each")
            if not broken:
                return

            job_lock = threading.Lock()

            def _progress(key, attempt_no, attempt_total, label):
                with job_lock:
                    RECOVERY_JOB["attempts"] += 1
                    RECOVERY_JOB["current"] = f"{SOURCES[key].get('name', key)} — {label}"

            from concurrent.futures import ThreadPoolExecutor
            fixed = 0
            with ThreadPoolExecutor(max_workers=4) as pool:
                futs = {pool.submit(deep_recover, k, SOURCES[k], _progress): k
                        for k in broken}
                for fut in list(futs):
                    try:
                        _, arts, st = fut.result()
                    except Exception as e:
                        k = futs[fut]
                        st = {"ok": False, "error": str(e)}
                        arts = []
                    k = futs[fut]
                    with STATE_LOCK:
                        STATE["sources_status"][k] = st
                        # a plain list, like the cycle path — a deque here made
                        # `del hist[:-30]` raise TypeError the day this branch ran
                        hist = STATE["src_hist"].setdefault(k, [])
                        hist.append(1 if st.get("ok") else 0)
                        del hist[:-30]
                    with job_lock:
                        RECOVERY_JOB["done"] += 1
                        if st.get("ok"):
                            fixed += 1
                            RECOVERY_JOB["fixed"] = fixed
                            RECOVERY_JOB["log"].append(
                                f"✓ {SOURCES[k].get('name', k)} back online "
                                f"({st.get('ways', '?')} ways, via "
                                f"{(st.get('recovery') or ['-'])[-1]})")
                        else:
                            RECOVERY_JOB["log"].append(
                                f"✗ {SOURCES[k].get('name', k)} still down "
                                f"({st.get('ways', '?')} ways tried)")
                    log(f"  deep recovery {k}: " +
                        ("FIXED via " + (st.get("recovery") or ["?"])[-1]
                         if st.get("ok") else "still down"))
            log(f"deep recovery done — {fixed}/{len(broken)} back online")
            if fixed:
                # bring the recovered feeds' news into the pipeline right away
                threading.Thread(target=run_cycle,
                                 kwargs={"reason": "post-recovery"},
                                 daemon=True).start()
        except Exception as e:
            log(f"deep recovery error: {e}")
            RECOVERY_JOB["log"].append(f"error: {e}")
        finally:
            RECOVERY_JOB["running"] = False
            RECOVERY_JOB["finished"] = time.time()

    threading.Thread(target=_recover_worker, daemon=True).start()
    return jsonify({"status": "recovery_started", "job": _recover_view()})


def _recover_view():
    with _RECOVER_LOCK:
        return dict(RECOVERY_JOB)


@app.route("/api/recover/status")
def api_recover_status():
    return jsonify(_recover_view())


@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.get_json(silent=True) or {}
    added = []

    with _CONFIG_LOCK:
        if "interval" in data:
            try:
                iv = int(data["interval"])
                if 60 <= iv <= 86400:
                    CONFIG["interval"] = iv
            except (TypeError, ValueError):
                pass

        if "assets" in data and isinstance(data["assets"], list):
            keep = [s for s in data["assets"] if s in all_assets_meta()]
            if keep:
                CONFIG["assets"] = keep

        if "auto_reports" in data:
            CONFIG["auto_reports"] = bool(data["auto_reports"])

        if "openai_key" in data and not _is_secret_mask(str(data["openai_key"] or "")):
            ai_cfg = CONFIG.setdefault("ai", {})
            ai_cfg["openai_key"] = str(data["openai_key"] or "").strip()
            ai_cfg["enabled"] = bool(ai_cfg["openai_key"])
            _init_ai_config()

        # ── news hygiene (applies to what is already in memory, not just the next
        #    cycle — the operator should see the effect the moment they save) ────
        hygiene_touched = False
        if "news_min_chars" in data:
            try:
                CONFIG["news_min_chars"] = max(0, min(2000, int(data["news_min_chars"])))
                hygiene_touched = True
            except (TypeError, ValueError):
                pass
        if "news_hide_social" in data:
            CONFIG["news_hide_social"] = bool(data["news_hide_social"])
            hygiene_touched = True
        # ── social popularity gate (min Reddit upvotes/comments) ─────────────
        gate_touched = False
        if "social_score_filter" in data:
            CONFIG["social_score_filter"] = bool(data["social_score_filter"])
            gate_touched = True
        if "social_score_min" in data:
            try:
                CONFIG["social_score_min"] = max(0, min(100000, int(data["social_score_min"])))
                gate_touched = True
            except (TypeError, ValueError):
                pass
        if "social_comments_min" in data:
            try:
                CONFIG["social_comments_min"] = max(0, min(100000, int(data["social_comments_min"])))
                gate_touched = True
            except (TypeError, ValueError):
                pass
        if gate_touched and CONFIG.get("social_score_filter"):
            # saved config wins over the default when the checkbox is on
            if "social_score_min" not in data:
                CONFIG["social_score_min"] = CONFIG.get("social_score_min", 2000)

        if "report_max_age_hours" in data:
            try:
                h = int(float(data["report_max_age_hours"]))
                # clamped, not rejected: the value that is stored is the value
                # that survives the restart
                CONFIG["report_max_age_hours"] = max(NEWS_WINDOW_MIN_HOURS,
                                                     min(NEWS_WINDOW_MAX_HOURS, h))
            except (TypeError, ValueError):
                pass

        if "source_updates" in data and isinstance(data["source_updates"], dict):
            for k, on in data["source_updates"].items():
                if k in CONFIG["sources_enabled"]:
                    CONFIG["sources_enabled"][k] = bool(on)

        if "telegram" in data and isinstance(data["telegram"], dict):
            tg_in = data["telegram"]
            tok = _tg_clean_token(tg_in.get("token") or "")
            chat = _tg_clean_chat(tg_in.get("chat") or "")
            if _is_secret_mask(tok):
                tok = ""  # round-tripped masked field — keep the stored token
            tg = CONFIG.setdefault("telegram", {})
            if tok:
                tg["token"] = tok
            if chat:
                tg["chat"] = chat
            # extended digest tuning
            if "enabled" in tg_in:
                tg["enabled"] = bool(tg_in["enabled"])
            if "min_credibility" in tg_in:
                try:
                    tg["min_credibility"] = min(1.0, max(0.0, float(tg_in["min_credibility"])))
                except (TypeError, ValueError):
                    pass
            if "max_items" in tg_in:
                try:
                    tg["max_items"] = min(30, max(3, int(tg_in["max_items"])))
                except (TypeError, ValueError):
                    pass
            if "quiet_hours" in tg_in:
                tg["quiet_hours"] = bool(tg_in["quiet_hours"])
            if "include_link" in tg_in:
                tg["include_link"] = bool(tg_in["include_link"])
            if "include_summary" in tg_in:
                tg["include_summary"] = bool(tg_in["include_summary"])
            if "hashtags" in tg_in:
                tg["hashtags"] = bool(tg_in["hashtags"])
            if "emoji" in tg_in:
                tg["emoji"] = bool(tg_in["emoji"])
            if "show_stars" in tg_in:
                tg["show_stars"] = bool(tg_in["show_stars"])
            if "link_on_own_line" in tg_in:
                tg["link_on_own_line"] = bool(tg_in["link_on_own_line"])
            if "silent" in tg_in:
                tg["silent"] = bool(tg_in["silent"])
            if "pin" in tg_in:
                tg["pin"] = bool(tg_in["pin"])
            if "max_age_hours" in tg_in:
                try:
                    tg["max_age_hours"] = min(72, max(1, float(tg_in["max_age_hours"])))
                except (TypeError, ValueError):
                    pass
            if isinstance(tg_in.get("asset_filter"), list):
                tg["asset_filter"] = [str(x).upper()[:12] for x in tg_in["asset_filter"][:20]]
            if "header" in tg_in:
                tg["header"] = str(tg_in["header"])[:120]
            if "template" in tg_in and str(tg_in["template"]).strip():
                tg["template"] = str(tg_in["template"])[:600]
            if "language" in tg_in and tg_in["language"] in ("fa", "en"):
                tg["language"] = tg_in["language"]
            if tok and chat:
                try:
                    _tg_send(tok, chat, "MOHMD NEWS — digest connected ✓ از این بعد بعد از هر چرخه خلاصه خبری می‌آید.")
                except Exception:
                    pass

        if "bale" in data and isinstance(data["bale"], dict):
            bale_in = data["bale"]
            tok = _bale_clean_token(bale_in.get("token") or "")
            chat = _bale_clean_chat(bale_in.get("chat") or "")
            if _is_secret_mask(tok):
                tok = ""  # round-tripped masked field — keep the stored token
            bale = CONFIG.setdefault("bale", {})
            if tok:
                bale["token"] = tok
            if chat:
                bale["chat"] = chat
            if "enabled" in bale_in:
                bale["enabled"] = bool(bale_in["enabled"])
            if "min_credibility" in bale_in:
                try:
                    bale["min_credibility"] = min(1.0, max(0.0, float(bale_in["min_credibility"])))
                except (TypeError, ValueError):
                    pass
            if "max_items" in bale_in:
                try:
                    bale["max_items"] = min(30, max(3, int(bale_in["max_items"])))
                except (TypeError, ValueError):
                    pass
            if "quiet_hours" in bale_in:
                bale["quiet_hours"] = bool(bale_in["quiet_hours"])
            if "include_link" in bale_in:
                bale["include_link"] = bool(bale_in["include_link"])
            if "include_summary" in bale_in:
                bale["include_summary"] = bool(bale_in["include_summary"])
            if "hashtags" in bale_in:
                bale["hashtags"] = bool(bale_in["hashtags"])
            if "emoji" in bale_in:
                bale["emoji"] = bool(bale_in["emoji"])
            if "show_stars" in bale_in:
                bale["show_stars"] = bool(bale_in["show_stars"])
            if "link_on_own_line" in bale_in:
                bale["link_on_own_line"] = bool(bale_in["link_on_own_line"])
            if "silent" in bale_in:
                bale["silent"] = bool(bale_in["silent"])
            if "max_age_hours" in bale_in:
                try:
                    bale["max_age_hours"] = min(72, max(1, float(bale_in["max_age_hours"])))
                except (TypeError, ValueError):
                    pass
            if isinstance(bale_in.get("asset_filter"), list):
                bale["asset_filter"] = [str(x).upper()[:12] for x in bale_in["asset_filter"][:20]]
            if "header" in bale_in:
                bale["header"] = str(bale_in["header"])[:120]
            if "template" in bale_in and str(bale_in["template"]).strip():
                bale["template"] = str(bale_in["template"])[:600]
            if "language" in bale_in and bale_in["language"] in ("fa", "en"):
                bale["language"] = bale_in["language"]
            if tok and chat:
                try:
                    _bale_send(tok, chat, "MOHMD NEWS — اتصال به پیام‌رسان بله برقرار شد ✓")
                except Exception:
                    pass

        if data.get("add_source"):
            add = data["add_source"]
            name = (add.get("name") or "").strip()[:48]
            url = (add.get("rss") or "").strip()
            if name and url.startswith(("http://", "https://")):
                key = "custom_" + str(abs(hash(url)) % 10_000_000)
                CONFIG["custom_sources"][key] = {"name": name, "rss": url,
                                                 "trust": float(add.get("trust") or 0.6)}
                CONFIG["sources_enabled"][key] = True
                added.append(name)

        for key in (data.get("remove_sources") or []):
            CONFIG["custom_sources"].pop(key, None)
            CONFIG["sources_enabled"].pop(key, None)

        # ---- custom assets -------------------------------------------------
        if data.get("add_asset"):
            add = data["add_asset"]
            sym = (add.get("symbol") or "").strip().upper()[:12]
            yahoo = (add.get("yahoo") or "").strip()
            if sym and yahoo and sym not in ASSETS:
                CONFIG["custom_assets"][sym] = {
                    "fa": (add.get("fa") or "").strip() or sym,
                    "name": (add.get("name") or "").strip() or sym,
                    "icon": (add.get("icon") or "★").strip()[:3] or "★",
                    "yahoo": yahoo.upper(),
                    "coingecko": (add.get("coingecko") or "").strip().lower() or None,
                    "keywords": (add.get("keywords") or "").strip() or None,
                }
                CONFIG["assets"].append(sym)
                added.append(sym)

        for sym in (data.get("remove_assets") or []):
            sym = str(sym).upper()
            if sym in ASSETS:            # builtin assets stay, only custom are removable
                continue
            CONFIG["custom_assets"].pop(sym, None)
            CONFIG["assets"] = [a for a in CONFIG["assets"] if a != sym]

        save_config()

        if hygiene_touched or gate_touched:
            refilter_state()

        safe_config = _mask_secrets(CONFIG)

    CYCLE_EVENT.set()  # wake the scheduler so changes apply quickly
    return jsonify({"ok": True, "config": safe_config, "added": added})


# ---------------------------------------------------------------------------
# Full-text extraction
# ---------------------------------------------------------------------------
_JUNK_LINE = (
    "subscribe", "newsletter", "sign up", "sign in", "log in", "cookie",
    "advertisement", "advertise with us", "follow us", "share this", "read more:",
    "read more", "related articles", "terms of service", "privacy policy",
    "all rights reserved", "disclaimer", "download our app", "watch now",
    "click here", "join our", "topics:", "tags:", "منتشر شده در",
)
_MIN_PARA = 60


def _paragraphs_from(node):
    out = []
    for p in node.find_all(["p", "h2", "h3"]):
        txt = p.get_text(" ", strip=True)
        txt = " ".join(txt.split())
        if len(txt) < _MIN_PARA:
            continue
        low = txt.lower()
        if any(j in low for j in _JUNK_LINE) and len(txt) < 220:
            continue
        out.append(txt)
    return out


def _jsonld_body(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                body = node.get("articleBody")
                if isinstance(body, str) and len(body) > 300:
                    return body
                for v in node.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
    return None


from urllib.parse import quote_plus, unquote, urlparse


_BLOCKED_HOSTS = ("news.google.", "googleusercontent", "www.google.", "google.com",
                  "bing.com", "duckduckgo.com", "news.yahoo.com", "msn.com",
                  "facebook.com", "twitter.com", "x.com", "instagram.com")
_STOPWORDS = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "as", "at",
              "with", "is", "are", "its", "it", "after", "over", "up", "down", "new",
              "says", "will", "could", "than", "from", "by", "be", "has", "have"}


def _title_tokens(title: str):
    words = re.findall(r"[A-Za-z0-9$%]+", (title or "").lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]


def _bounded(fn, seconds, *args, **kwargs):
    """Run fn(*args) in a worker thread and give up after `seconds` (→ None).

    The paywall ladder is a *sequence* of tries whose socket timeouts run 15–45s,
    so one hostile host used to hold the article modal open for over a minute.
    Bounding it keeps behaviour identical whenever the ladder finishes in time.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(fn, *args, **kwargs).result(timeout=seconds)
    except Exception:
        return None
    finally:
        pool.shutdown(wait=False)


def _looks_like_match(url: str, title: str, publisher: str = "") -> bool:
    """Only accept a search hit that is plausibly *this* story."""
    try:
        parts = urlparse(url)
        host = parts.netloc.lower()
    except Exception:
        return False
    if any(b in host for b in _BLOCKED_HOSTS):
        return False
    tokens = _title_tokens(title)
    if not tokens:
        return False
    # The path is the only thing that can tie a URL to a headline. A bare
    # domain or a section page (`…/symbols/BTCUSD/`, `…/economy-news/`) carries
    # no headline words, and accepting it on a publisher-host match alone used
    # to hand the modal a completely unrelated page as "the article".
    path = unquote(parts.path).lower()
    hits = sum(1 for t in tokens if t.strip("$%") and t.strip("$%") in path)
    # A substantive hit is a real headline word, not a bare ticker — otherwise
    # `…/symbols/btcusd/` matches any story whose headline opens "BTC/USD:".
    strong = sum(1 for t in tokens if len(t) >= 5 and t in path)
    if hits == 0 or strong == 0:
        return False
    slug = re.sub(r"[^a-z0-9]", "", (publisher or "").lower())
    stem = slug[3:] if slug.startswith("the") and len(slug) > 6 else slug
    if len(stem) > 3 and (stem in host.replace("-", "").replace(".", "")):
        return True
    return hits >= max(3, int(len(tokens) * 0.34))


# ---------------------------------------------------------------------------
# Google News links: ids are encrypted, the page is a JS shell, and Google
# never redirects - so the URL has to be *exchanged*. Every article page
# carries a signature (`data-n-a-sg`) and a timestamp (`data-n-a-ts`); posting
# those to the public batchexecute endpoint returns the publisher's address.
# Free, no key, ~300ms. Hits are cached on disk because an id never changes.
# ---------------------------------------------------------------------------
NEWSLINK_FILE = Path(__file__).parent / ".news_links.json"
_NEWSLINK_CACHE = {}
_NEWSLINK_LOCK = threading.Lock()


def _load_newslinks():
    try:
        if NEWSLINK_FILE.exists():
            data = json.loads(NEWSLINK_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _NEWSLINK_CACHE.update({k: v for k, v in data.items() if isinstance(v, str)})
    except Exception:
        pass


def _save_newslinks():
    try:
        tmp = NEWSLINK_FILE.with_suffix(".tmp")
        with _NEWSLINK_LOCK:
            snap = dict(_NEWSLINK_CACHE)
        tmp.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
        tmp.replace(NEWSLINK_FILE)
    except Exception:
        pass


def _gn_article_id(url: str):
    m = re.search(r"/articles/([^?/#]+)", url or "")
    return m.group(1) if m else None


def _gn_offline_id(art_id: str):
    """Some (older) ids are base64 of a small protobuf with the URL in clear;
    those need no network round trip at all."""
    if not art_id or not art_id.startswith("CBMi"):
        return None
    try:
        raw = base64.urlsafe_b64decode(art_id + "=" * (-len(art_id) % 4))
        for m in re.finditer(rb"https?://[\x20-\x7e]{10,400}", raw):
            cand = m.group(0).decode("utf-8", "replace")
            cand = re.split(r"[\x00-\x1f]", cand)[0]
            if "news.google.com" not in cand and "." in cand.split("//")[-1][:40]:
                return cand
    except Exception:
        return None
    return None


def decode_google_news_url(art_id: str, timeout: int = 8):
    """Swap an encrypted Google News article id for the publisher URL."""
    if not art_id:
        return None
    try:
        page = requests.get(f"https://news.google.com/rss/articles/{art_id}",
                            headers=HEADERS, timeout=timeout)
        html = page.text or ""
    except Exception:
        return None
    sg = re.search(r'data-n-a-sg="([^"]+)"', html)
    ts = re.search(r'data-n-a-ts="([^"]+)"', html)
    if not (sg and ts):
        return None
    inner = ("[\"garturlreq\",[[\"X\",\"X\",[\"X\",\"X\"],null,null,1,1,"
             "\"US:en\",null,1,null,null,null,null,null,0,1],\"X\",\"X\",1,"
             "[1,1,1],1,1,null,0,0,null,0],\"%s\",%s,\"%s\"]"
             % (art_id, ts.group(1), sg.group(1)))
    payload = json.dumps([[ ["Fbv4je", inner] ]])
    url = None
    for kwargs in ({"params": {"f.req": payload}}, {"data": {"f.req": payload}}):
        if url:
            break
        try:
            r = requests.post("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                              headers=HEADERS, timeout=timeout, **kwargs)
            body = r.text or ""
        except Exception:
            continue
        for part in body.split("\n\n"):
            try:
                rows = json.loads(part)
            except Exception:
                continue
            for row in (rows if isinstance(rows, list) else []):
                if (isinstance(row, list) and len(row) > 2 and row[0] == "wrb.fr"
                        and isinstance(row[2], str)):
                    try:
                        cand = json.loads(row[2])[1]
                    except Exception:
                        continue
                    if isinstance(cand, str) and cand.startswith("http"):
                        url = cand
                        break
        if not url:
            m = re.search(r'"(https?://(?!news\.google\.com)[^"\\]{12,})"', body)
            if m:
                url = m.group(1)
    if not url:
        return None
    url = (url.replace("\\u003d", "=").replace("\\u0026", "&")
              .replace("\\/", "/").strip())
    if not url.startswith("http") or "news.google.com" in url or "google.com/url" in url:
        return None
    return url


def resolve_news_url(url: str, title: str = "", publisher: str = "", timeout: int = 8):
    """Google News wrapper → the publisher's own address (or None).
    Exchange first (exact, fast), then the search-engine lookup, then nothing -
    the caller falls back to the headline it already has."""
    if "news.google.com" not in (url or ""):
        return None
    art_id = _gn_article_id(url)
    if not art_id:
        return None
    with _NEWSLINK_LOCK:
        hit = _NEWSLINK_CACHE.get(art_id)
    if hit:
        return hit
    real = _gn_offline_id(art_id) or decode_google_news_url(art_id, timeout=timeout)
    if not real:
        real = resolve_publisher_url(title, publisher)
    if real:
        with _NEWSLINK_LOCK:
            _NEWSLINK_CACHE[art_id] = real
        _save_newslinks()
    return real


_load_newslinks()


def resolve_publisher_url(title: str, publisher: str = "", timeout: int = 15):
    """
    Google News article ids are encrypted, so `news.google.com/rss/articles/...`
    cannot be unwrapped. We look the headline up on public search engines and
    only accept a hit that plausibly matches this story (host = publisher name,
    or enough headline words inside the URL path).
    """
    if not title:
        return None
    query = f'"{title}"' + (f' {publisher}' if publisher else "")
    candidates = []

    # 1) Bing — result links carry the real URL base64-encoded in `u=a1...`
    try:
        r = requests.get("https://www.bing.com/search", params={"q": query},
                         headers=HEADERS, timeout=timeout)
        for tok in re.findall(r"u=a1([A-Za-z0-9_\-]+)", r.text)[:14]:
            try:
                dec = base64.urlsafe_b64decode(tok + "=" * (-len(tok) % 4))
                dec = dec.decode("utf-8", "replace")
                if dec.startswith("http"):
                    candidates.append(dec)
            except Exception:
                continue
    except Exception as e:
        log(f"  x bing lookup failed: {e}")

    # 2) DuckDuckGo (rate limited, best effort)
    if not candidates:
        for attempt in ("lite", "html"):
            try:
                if attempt == "lite":
                    r = requests.get("https://lite.duckduckgo.com/lite/",
                                     params={"q": query}, headers=HEADERS, timeout=timeout)
                else:
                    r = requests.post("https://html.duckduckgo.com/html/",
                                      data={"q": query}, headers=HEADERS, timeout=timeout)
                got = [unquote(u) for u in re.findall(r"uddg=([^\"&]+)", r.text)]
                candidates.extend(got)
                if got:
                    break
            except Exception:
                continue

    for c in candidates:
        if _looks_like_match(c, title, publisher):
            return c
    return None


# ---------------------------------------------------------------------------
# deep article extraction — when the publisher's page is a JS shell, an IP
# block or a paywall, these relay sources usually still have the full text.
# All free, no keys. Ordered by quality of output.
# ---------------------------------------------------------------------------

def _jina_reader_text(url: str):
    """r.jina.ai renders the page in a headless browser and returns clean
    text/markdown — the single most effective free fix for JS-rendered news
    *and* for hosts that answer 403 to this machine's IP.

    Headers matter more than they should: r.jina.ai sits behind Cloudflare and
    challenges the app's own `HEADERS` UA (and any Chrome-looking one) with a
    403 challenge page, while the crawler UA sails through — measured 3/3 hosts
    that were 403 for every other rung (cryptopotato 576 words, ccn 1168,
    robinhood 342). One retry absorbs the flaky challenge; with MOHMD_JINA_KEY
    set the authenticated route is used instead.
    """
    _hdrs = {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; "
                           "+http://www.google.com/bot.html)",
             "Accept": "text/plain", "Accept-Language": "en-US,en;q=0.9"}
    if _JINA_KEY:
        _hdrs["Authorization"] = f"Bearer {_JINA_KEY}"
    for attempt in range(2):
        try:
            r = requests.get(f"https://r.jina.ai/{url}", headers=_hdrs, timeout=25)
        except Exception:
            r = None
        if r is not None and r.status_code == 200 and len(r.text) >= 300:
            return r.text
        if r is not None and r.status_code not in (403, 429, 503):
            break
        time.sleep(0.8 * (attempt + 1))
    return None


def _proxy_html(url: str, template: str, timeout: float = 3.0):
    """Fetch the page through a raw XML/HTML proxy (beats IP/UA blocks)."""
    from urllib.parse import quote_plus
    try:
        r = requests.get(template.format(q=quote_plus(url)),
                         headers=HEADERS, timeout=timeout)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    return None


def _wayback_html(url: str):
    """Closest Wayback Machine snapshot of the article page."""
    try:
        r = requests.get("https://archive.org/wayback/available",
                         params={"url": url}, headers=HEADERS, timeout=8)
        snap = ((r.json() or {}).get("archived_snapshots") or {}).get("closest") or {}
        if snap.get("url"):
            rr = requests.get(snap["url"], headers=HEADERS, timeout=20)
            if rr.status_code == 200 and len(rr.text) > 500:
                return rr.text
    except Exception:
        pass
    return None


def _ua_fetch(url: str, headers: dict):
    """Direct fetch with a crawler UA (Googlebot/Bingbot often see the full
    article on sites that serve browsers a paywall stub)."""
    try:
        r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    return None


def _archive_ph_html(url: str):
    """Fetch the latest archive.ph (archive.today) snapshot of a URL.
    archive.ph mirrors often have the full paywalled article text."""
    from urllib.parse import quote_plus
    try:
        # archive.ph returns the latest snapshot page with a redirect
        r = requests.get(
            f"https://archive.ph/newest/{url}",
            headers={**HEADERS, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"},
            timeout=15, allow_redirects=True)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    return None


def _reddit_session(url: str):
    """GET the page and, when reddit answers with its proof-of-work shell, solve
    it (two rounds) so the session holds the `rdt` cookie. Returns (session,
    last_response)."""
    s = requests.Session()
    s.headers.update(HEADERS)
    r = s.get(url, timeout=15, allow_redirects=True)
    for _ in range(4):
        # ~60 kB is comfortably above the shell and far below any real page
        if r.status_code != 200 or len(r.content) > 60000:
            break
        m = re.search(r'await\(async e=>e\+e\)\("([0-9a-f]{8,})"\)', r.text)
        if not m:
            break
        tok = re.search(r'name="jsc_token" value="([^"]*)"', r.text)
        r = s.get(r.url, params={"solution": m.group(1) * 2,
                                 "js_challenge": "1",
                                 "jsc_token": tok.group(1) if tok else "",
                                 "jsc_orig_r": ""}, timeout=15)
    return s, r


def _reddit_html(url: str):
    """reddit.com hands non-browser clients a tiny JS interstitial (an ~8 kB
    shell whose only job is `<form name="solution">` + a proof-of-work nonce)
    instead of the post. The "work" is the nonce doubled, and reddit normally
    asks for two consecutive rounds before it sets the `rdt` cookie and serves
    the real ~500 kB page — so two extra GETs buy the full post with no browser
    and no third-party relay. Measured: 8407 B challenge → 554 kB post."""
    try:
        s, r = _reddit_session(url)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except Exception:
        pass
    return None


def _looks_like_paragraph(s: str) -> bool:
    """Reject the shapes a body extractor picks up by accident: a bare media URL,
    a line of markup, a run of emoji/labels."""
    if len(s) < _MIN_PARA:
        return False
    if s.startswith(("http://", "https://")) and " " not in s[:80]:
        return False
    letters = sum(1 for c in s if c.isalpha() or c.isspace() or c in ".,;:!?-'\"()[]/&%")
    return letters / len(s) >= 0.75


def _reddit_paras(text: str, prefix: str = "") -> list:
    out = []
    for blk in re.split(r"\n\s*\n", text or ""):
        blk = " ".join(blk.split())
        if not _looks_like_paragraph(blk):
            continue
        out.append((prefix + blk) if prefix else blk)
    return out


def _pullpush_selftext(post_id: str):
    """pullpush.io mirrors reddit submissions — including selftext that moderation
    has since `[removed]`, which the live .json endpoint refuses to hand over."""
    try:
        r = requests.get("https://api.pullpush.io/reddit/search/submission/",
                         params={"ids": post_id}, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            rows = (r.json() or {}).get("data") or []
            if rows and isinstance(rows[0], dict):
                st = rows[0].get("selftext") or ""
                if len(st.split()) >= 30:
                    return st
    except Exception:
        pass
    return ""


def _reddit_external(post: dict, url: str):
    """A link post carries no prose of its own — the article it points at *is*
    the content, so the ladder has to follow it."""
    try:
        if post.get("is_self"):
            return None
        ext = (post.get("url") or "").strip()
        if not ext.startswith(("http://", "https://")):
            return None
        host = urlparse(ext).netloc.lower()
        if "reddit." in host or "redd.it" in host:
            return None
        return ext
    except Exception:
        return None


def _reddit_content(url: str):
    """A reddit post is a shell plus an XHR: the body never ships in the HTML the
    ladder parses, which is why every thread came back as ~22 words of title and
    metadata. The `.json` endpoint (same session, fetched *after* the PoW cookie)
    returns selftext and comment tree directly; pullpush fills the gap where the
    post body was removed."""
    try:
        s, _ = _reddit_session(url)
        j = s.get(url.rstrip("/") + ".json?raw_json=1&limit=12",
                  headers={**HEADERS, "Accept": "application/json"}, timeout=15)
        if j.status_code != 200 or not j.text.lstrip().startswith("["):
            return None
        data = j.json()
        if not isinstance(data, list) or not data:
            return None
        post = (((data[0].get("data") or {}).get("children")) or [{}])[0].get("data") or {}
        paras = _reddit_paras(post.get("selftext") or "")
        wc = sum(len(p.split()) for p in paras)
        if wc < 60:
            m = re.search(r"/comments/([a-z0-9]+)", url)
            archived = _pullpush_selftext(m.group(1)) if m else ""
            got = _reddit_paras(archived)
            if sum(len(p.split()) for p in got) > wc:
                paras = got
                wc = sum(len(p.split()) for p in got)
        # a text-less post (image / link / removed body) is a *discussion*:
        # the thread's comments are the only prose the page has
        if wc < 120 and len(data) > 1:
            for c in ((data[1].get("data") or {}).get("children")) or []:
                if c.get("kind") != "t1":
                    continue
                cd = c.get("data") or {}
                body = (cd.get("body") or "").strip()
                if body in ("[removed]", "[deleted]"):
                    continue
                paras += _reddit_paras(body, prefix=f"u/{cd.get('author') or '?'}: ")
                wc = sum(len(p.split()) for p in paras)
                if wc >= 400 or len(paras) >= 8:
                    break
        if not paras:
            return {"paragraphs": [], "word_count": 0, "partial": False,
                    "title": post.get("title") or "", "site": "reddit",
                    "published": "", "url": url, "resolved_url": url,
                    "external_url": _reddit_external(post, url),
                    "via": "reddit-json-empty"}
        return {"paragraphs": paras[:40], "word_count": wc, "partial": wc < 120,
                "title": post.get("title") or "", "site": "reddit",
                "published": "", "url": url, "resolved_url": url,
                "external_url": _reddit_external(post, url),
                "via": "reddit-json"}
    except Exception:
        return None


def _parse_reader_text(text: str):
    """Parse r.jina.ai output: 'Title: …' header + 'Markdown Content:' body."""
    title = ""
    body = text
    m = re.search(r"^Title:\s*(.+)$", text, re.M)
    if m:
        title = m.group(1).strip()
    m = re.search(r"^Markdown Content:\s*$", text, re.M)
    if m:
        body = text[m.end():]
    # markdown → plain lines, keep prose-looking ones
    lines = []
    for ln in body.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith(("#", "!", ">", "---", "|", "```")):
            continue
        ln = re.sub(r"^([-*+]\s+|\d+\.\s+)", "", ln)          # bullet / numbering
        ln = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", ln)   # ![alt](url) → gone
        ln = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", ln)   # [txt](url) → txt
        ln = re.sub(r"[*_`]{1,3}", "", ln)
        ln = " ".join(ln.split())
        if len(ln) < 55:
            continue
        # a link that survived the strip (nested markdown, bare url in text) is
        # navigation, not prose — the nav bullets of a page used to read as a
        # paragraph of image labels
        if "](" in ln or "![" in ln:
            continue
        letters = sum(1 for c in ln if c.isalpha() or c.isspace())
        if letters / len(ln) < 0.72:
            continue
        low = ln.lower()
        if any(j in low for j in _JUNK_LINE) and len(ln) < 220:
            continue
        lines.append(ln)
    return title, lines


# ---------------------------------------------------------------------------
# Inline app payloads. The page an SPA *serves* is a shell — the article lives
# in the JSON it hydrates from (Next.js `__NEXT_DATA__`, Nuxt/Redux initial
# state, the React flight stream `self.__next_f.push`). Reading the payload
# turns a 28-word stub into the real document with no headless browser, and it
# survives every proxy rung of the ladder because the data ships with the HTML.
# ---------------------------------------------------------------------------
_PAYLOAD_KEYS = (
    "articlebody", "longdescription", "fulldescription", "articletext",
    "bodytext", "articlecontent", "htmlbody", "contenthtml",
)


def _looks_like_prose(s: str) -> bool:
    """True for a string that reads as an article paragraph, not as markup,
    CSS, a label from an i18n table or a URL."""
    if not isinstance(s, str):
        return False
    s = s.strip()
    if len(s) < 200 or len(s.split()) < 30:
        return False
    low = s[:400].lower()
    if any(j in low for j in ("function(", "=>", "window.", "undefined",
                              ".css", ".js", "http://", "https://t")):
        return False
    if s.startswith(("http://", "https://") ) and " " not in s[:60]:
        return False
    sentences = sum(s.count(x) for x in (". ", "? ", "! "))
    ok = sum(1 for c in s if c.isalpha() or c.isspace() or
             c in ".,;:!?-'\"()[]$/&%0123456789%")
    return sentences >= 2 and ok / len(s) >= 0.8


def _iter_strings(node, path=()):
    """Yield (key, string) for every string in a parsed JSON document."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _iter_strings(v, path + (str(k),))
    elif isinstance(node, list):
        for v in node:
            yield from _iter_strings(v, path)
    elif isinstance(node, str):
        yield (path[-1] if path else ""), node


def _payload_candidates(html: str):
    """All string content the inline scripts of the document carry."""
    out = []
    for m in re.finditer(r"<script([^>]*)>(.*?)</script>", html or "", re.S | re.I):
        attrs, body = m.group(1), m.group(2)
        if not body.strip():
            continue
        raw = body.lstrip()
        if "json" in attrs.lower() or "__next_data__" in attrs.lower() or raw[:1] in ("{", "["):
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = None
            if parsed is not None:
                out.extend(_iter_strings(parsed))
                continue
        # React Server flight / Redux / Nuxt: JS, not JSON — pull the string
        # literals out of it (they are JSON-escaped, so json.loads decodes them)
        if any(k in body for k in ("self.__next_f", "__INITIAL_STATE__", "__NUXT__")):
            for sm in re.finditer(r'"((?:[^"\\]|\\.){160,})"', body):
                try:
                    s = json.loads('"' + sm.group(1) + '"')
                except Exception:
                    continue
                if isinstance(s, str):
                    out.append(("", s))
    return out


def _payload_blocks(texts) -> list:
    """Turn chosen payload strings into clean paragraphs."""
    out, seen = [], set()
    for t in texts:
        if not isinstance(t, str):
            continue
        for ln in t.splitlines() or [t]:
            ln = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", ln).strip()
            ln = " ".join(ln.split())
            if not _looks_like_paragraph(ln):
                continue
            k = ln[:120]
            if k in seen:
                continue
            seen.add(k)
            out.append(ln)
    return out


def _payload_paragraphs(html: str) -> list:
    """Salvage the article from the page's own hydration JSON.

    Tier 1 trusts the keys a CMS uses for the article itself (first hit per
    key, so a 'related articles' list of the same field never leaks in). Tier
    2 — only when tier 1 stayed thin — trusts the *shape*: a field repeated
    many times is a block list, otherwise the first prose-looking string.
    """
    cands = _payload_candidates(html)
    if not cands:
        return []
    picked, seen = [], set()
    for key, s in cands:
        k = (key or "").lower()
        if k in _PAYLOAD_KEYS and k not in seen and len(s.strip()) >= _MIN_PARA:
            seen.add(k)
            picked.append(s)
    blocks = _payload_blocks(picked)
    if sum(len(p.split()) for p in blocks) >= 100:
        return blocks

    prose = [((key or "").lower(), s) for key, s in cands if _looks_like_prose(s)]
    if not prose:
        return blocks
    counts = {}
    for k, _ in prose:
        counts[k] = counts.get(k, 0) + 1
    top = max(counts, key=counts.get)
    run = [s for k, s in prose if counts[top] >= 3 and k == top]
    if not run:
        run = [prose[0][1]]
    return _payload_blocks(run) or blocks


def _parse_article_html(html: str, url: str, publisher=None, via="direct"):
    """Full DOM/JSON-LD/app-payload extraction from one HTML document. Adds a
    statistical 'densest <p> container' pass so unknown layouts still yield the
    body. The JSON passes run *before* <script> is decomposed — they used to
    run after it, which silently made the JSON-LD pass dead code."""
    result = {"paragraphs": [], "word_count": 0, "partial": True,
              "title": "", "site": "", "published": "", "url": url,
              "resolved_url": url, "via": via}
    soup = BeautifulSoup(html, "html.parser")

    result["site"] = (soup.find("meta", property="og:site_name") or {}).get("content", "") or ""
    result["title"] = ((soup.find("meta", property="og:title") or {}).get("content")
                      or (soup.title.get_text(strip=True) if soup.title else ""))
    result["published"] = ((soup.find("meta", property="article:published_time") or {})
                           .get("content", "") or "")

    # the JSON passes need the <script> tags, so they run before the strip below
    body = _jsonld_body(soup)
    payload = _payload_paragraphs(html)

    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                     "iframe", "noscript", "form", "button"]):
        tag.decompose()

    paras = []
    if body:
        paras = [p.strip() for p in body.split("\n") if len(p.strip()) > _MIN_PARA]
    if payload and len("".join(payload)) > len("".join(paras)):
        paras = payload

    if len(paras) < 3:
        for sel in (".entry-content", ".post-content", ".article-content", ".article-body",
                    ".story-body", ".post-body", ".content-body", ".rich-text",
                    "#content", "article", "main"):
            el = soup.select_one(sel)
            if not el:
                continue
            got = _paragraphs_from(el)
            if len("".join(got)) > len("".join(paras)):
                paras = got
            if len(paras) >= 3:
                break

    if len(paras) < 3:
        best = []
        for art in soup.find_all("article"):
            got = _paragraphs_from(art)
            if len("".join(got)) > len("".join(best)):
                best = got
        if best:
            paras = best

    # statistical pass: whichever single parent element holds the most <p> text
    # is almost certainly the article body — works with any class naming
    if len(paras) < 3:
        buckets = {}
        for p in soup.find_all("p"):
            parent = p.parent
            if parent is None or parent.name in ("body", "html", "[document]"):
                continue
            txt = " ".join(p.get_text(" ", strip=True).split())
            if len(txt) < _MIN_PARA:
                continue
            buckets.setdefault(id(parent), [parent, []])[1].append(txt)
        if buckets:
            _, texts = max(buckets.values(), key=lambda v: sum(map(len, v[1])))
            if sum(map(len, texts)) > sum(map(len, paras)):
                paras = texts

    if len(paras) < 2:
        got = _paragraphs_from(soup)
        # never *replace* a real body with nothing: a page whose only prose is
        # JSON-LD / an app payload has no qualifying <p> at all, and the old
        # unconditional overwrite threw the article away
        if sum(map(len, got)) > sum(map(len, paras)):
            paras = got

    # last-resort: the meta description (thin, but beats an empty modal)
    if not paras:
        for prop in ("og:description", "description"):
            m = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if m and m.get("content"):
                paras = [m["content"].strip()]
                break

    seen, clean = set(), []
    for p in paras:
        k = p[:120]
        if k in seen:
            continue
        seen.add(k)
        clean.append(p)

    result["paragraphs"] = clean[:150]
    result["word_count"] = sum(len(p.split()) for p in result["paragraphs"])
    result["partial"] = result["word_count"] < 120
    return result


def _search_snippet_paragraphs(title, url=None, publisher=None):
    """Extract full content paragraphs from search engine snippets when the publisher blocks scrapers."""
    if not title:
        return []
    paragraphs = []
    seen = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    queries = []
    host = urlparse(url).netloc.lower() if url else ""
    clean_host = host.replace("www.", "") if host else ""
    if clean_host and "google" not in clean_host:
        queries.append(f'site:{clean_host} "{title}"')
        words = title.split()[:8]
        if len(words) >= 4:
            queries.append(f'site:{clean_host} "{" ".join(words)}"')
    queries.append(f'"{title}"')
    clean_title = re.sub(r'[\'\"\–\—\-:]', ' ', title)
    queries.append(" ".join(clean_title.split()[:10]))

    for q in queries:
        try:
            r = requests.get("https://www.bing.com/search", params={"q": q}, headers=headers, timeout=5)
            if r.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                for p in soup.select("p, .b_caption p, .b_snippet"):
                    txt = p.get_text(strip=True)
                    txt = re.sub(r'^(?:\d+\s+(?:hours?|days?|mins?|weeks?|months?)\s+ago|[A-Z][a-z]{2}\s+\d+,\s+\d{4})[·\s\-]*(?:[·])?\s*', '', txt)
                    txt = re.sub(r'(?:Read more|More|\.\.\.|…|\[\.\.\.\])\s*$', '', txt).strip()
                    if len(txt) > 35 and txt not in seen:
                        seen.add(txt)
                        paragraphs.append(txt)
        except Exception:
            pass

        try:
            r = requests.post("https://html.duckduckgo.com/html/", data={"q": q}, headers=headers, timeout=5)
            if r.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                for el in soup.select(".result__snippet"):
                    txt = el.get_text(strip=True)
                    txt = re.sub(r'(?:Read more|More|\.\.\.|…|\[\.\.\.\])\s*$', '', txt).strip()
                    if len(txt) > 35 and txt not in seen:
                        seen.add(txt)
                        paragraphs.append(txt)
        except Exception:
            pass

        if len(paragraphs) >= 4:
            break

    return paragraphs


def fetch_article_content(url, title=None, publisher=None):
    """
    Best-effort *complete* article text, through a ladder of 6+ sources:
      direct fetch → news_bypass (paywall hosts) → r.jina.ai (renders JS) →
      2 raw proxies → Wayback Machine snapshot → Google-News redirect resolution → search snippets.
    The best result (most words) wins; stops early once a source returns a
    convincing body (≥250 words).
    """
    if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return {
            "paragraphs": [],
            "word_count": 0,
            "partial": True,
            "title": "",
            "url": url or "",
            "method": "none"
        }
    host = (urlparse(url).netloc.lower() if url else "")
    from news_bypass import smart_extract
    _PAYWALL_HOSTS = ("bloomberg.", "wsj.", "ft.com", "reuters.", "marketwatch.",
                      "nytimes.", "washingtonpost.", "seekingalpha.", "economist.",
                      "forbes.", "investing.com", "businessinsider.")

    # 0) resolve Google News encrypted links to the real publisher URL first
    if "news.google.com" in url:
        resolved = resolve_news_url(url, title or "", publisher or "")
        if resolved:
            url = resolved

    # 0b) nothing could unwrap the id:
    if "news.google.com" in url:
        snip_paras = _search_snippet_paragraphs(title, url, publisher)
        if snip_paras:
            wc = sum(len(p.split()) for p in snip_paras)
            return {"paragraphs": snip_paras[:150], "word_count": wc, "partial": wc < 120,
                    "title": title or "", "site": publisher or "", "published": "",
                    "url": url, "resolved_url": None, "via": "google-news-snippets"}
        return {"paragraphs": [], "word_count": 0, "partial": True,
                "title": title or "", "site": publisher or "", "published": "",
                "url": url, "resolved_url": None, "via": "google-news-unresolved",
                "error": "google-news id could not be resolved to a publisher url"}

    best = None

    def _consider(res):
        nonlocal best
        if not res or not res.get("paragraphs"):
            return False
        if best is None or res["word_count"] > best["word_count"]:
            best = res
        return best["word_count"] >= 250          # convincing body → stop

    # 0c) reddit blocks plain clients with a solvable JS interstitial, and its
    #     body lives behind an XHR — the session solves the challenge once and
    #     then reads the .json endpoint (selftext + comments) directly.
    if "reddit." in host:
        rc = _bounded(_reddit_content, 22, url)
        if rc:
            if rc.get("paragraphs") and _consider(rc):
                return best
            # link post with (almost) no prose of its own → the target article
            ext = rc.get("external_url")
            if ext and (best is None or best["word_count"] < 120):
                inner = _bounded(fetch_article_content, 15, ext, title or "", publisher or "")
                if inner and inner.get("paragraphs"):
                    _consider({**inner, "via": "reddit→" + str(inner.get("via"))})
                    if best["word_count"] >= 250:
                        return best
        rh = _bounded(_reddit_html, 14, url)
        if rh:
            res = _parse_article_html(rh, url, publisher, via="reddit-jsc")
            if _consider(res):
                return best

    # 1) paywalled outlet? the tested bypass ladder goes first (bounded — see
    #    _bounded; unbounded it could hold the modal for a minute or more).
    #    bypass_ran stops step 4 from calling the *same* ladder with the same
    #    arguments a second time — it had already timed out once.
    bypass_ran = False
    if any(h in host for h in _PAYWALL_HOSTS):
        bypass_ran = True
        bp = _bounded(smart_extract, 25, url, title or "", publisher or "") or {}
        if bp.get("paragraphs"):
            _consider({**bp, "site": publisher or "", "published": "",
                       "resolved_url": bp.get("resolved_url") or url,
                       "via": "bypass:" + (bp.get("bypass") or "")})

    # 2) direct fetch + full DOM parse
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        if resp.status_code == 200 and len(resp.text) > 500:
            res = _parse_article_html(resp.text, url, publisher, via="direct")
            res["resolved_url"] = resp.url
            if _consider(res):
                return best
    except Exception:
        pass

    # 2b) trafilatura — the best open-source article extractor (Apache-2.0,
    #     key-less): readability + justext fallbacks built in. One second on
    #     live feeds where the DOM pass returned thin text, so it goes right
    #     before the parallel deep burst and also re-tries the paywall hosts.
    def _trafilatura_rung():
        try:
            import trafilatura
            r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
            if r.status_code != 200 or len(r.text) < 500:
                return None
            txt = trafilatura.extract(r.text, include_comments=False,
                                      include_tables=False, favor_recall=True,
                                      url=url) or ""
            paras = [p.strip() for p in txt.splitlines() if len(p.strip()) > 40]
            if not paras:
                return None
            wc = sum(len(p.split()) for p in paras)
            return {"paragraphs": paras[:150], "word_count": wc, "partial": wc < 120,
                    "title": title or "", "site": publisher or "", "published": "",
                    "url": url, "resolved_url": url, "via": "trafilatura"}
        except ImportError:
            return None
        except Exception:
            return None

    tr = _bounded(_trafilatura_rung, 16)
    if tr:
        if _consider(tr):
            return best
        # even a thin trafilatura body usually beats nothing; keep it as `best`

    # 3) deep sources — all fetched IN PARALLEL (worst case ≈ slowest source,
    #    not the sum), so a thin article never stalls the modal for minutes
    _GBOT = {**HEADERS, "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
    _BBOT = {**HEADERS, "User-Agent": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"}
    deep_sources = (
        ("snippets",   lambda: "\n\n".join(_search_snippet_paragraphs(title, url, publisher)), "text"),
        ("jina",       lambda: _jina_reader_text(url),            "text"),
        ("allorigins", lambda: _proxy_html(url, "https://api.allorigins.win/raw?url={q}"), "html"),
        ("codetabs",   lambda: _proxy_html(url, "https://api.codetabs.com/v1/proxy?quest={q}"), "html"),
        ("wayback",    lambda: _wayback_html(url),                "html"),
        # many publishers hand the FULL page to search crawlers while giving
        # browsers the paywall stub — two more parallel getters, zero extra wait
        ("googlebot",  lambda: _ua_fetch(url, _GBOT),             "html"),
        ("bingbot",    lambda: _ua_fetch(url, _BBOT),             "html"),
        # archive.ph mirrors often bypass paywalls completely
        ("archiveph",  lambda: _archive_ph_html(url),             "html"),
        # Google webcache (separate from the google-cache in news_bypass)
        ("gcache",     lambda: _proxy_html(url, "https://webcache.googleusercontent.com/search?q=cache:{q}&strip=1", 12.0), "html"),
    )
    deep_results = []

    def _run_deep(item):
        label, getter, kind = item
        try:
            return label, kind, getter()
        except Exception:
            return label, kind, None

    from concurrent.futures import (ThreadPoolExecutor, as_completed,
                                    TimeoutError as FuturesTimeout)
    # as_completed (not pool.map): map() yields in *submission* order, so a fast
    # source that finished in 1s still waited behind a 20s one. Here the first
    # convincing body ends the wait and the stragglers are abandoned.
    #
    # DEEP_BUDGET is a hard ceiling on the whole ladder. Without it the modal
    # blocked for ~10s on sites where the fast sources have already answered
    # "nothing" and the only things still in flight are two raw proxies that
    # hang until their timeout and then return no body at all.
    DEEP_BUDGET = 18
    pool = ThreadPoolExecutor(max_workers=8)
    try:
        futures = [pool.submit(_run_deep, s) for s in deep_sources]
        for fut in as_completed(futures, timeout=DEEP_BUDGET):
            try:
                label, kind, text = fut.result()
            except Exception:
                continue
            if not text:
                continue
            try:
                if kind == "text":
                    jtitle, jparas = _parse_reader_text(text)
                    wc = sum(len(p.split()) for p in jparas)
                    res = {"paragraphs": jparas[:150], "word_count": wc,
                           "partial": wc < 120, "title": jtitle,
                           "site": publisher or "", "published": "",
                           "url": url, "resolved_url": url, "via": label}
                else:
                    res = _parse_article_html(text, url, publisher, via=label)
            except Exception:
                continue
            deep_results.append(res)
            if _consider(res):
                return best          # convincing body — stop waiting on the rest
    except FuturesTimeout:
        pass                         # budget spent — take the best we already have
    finally:
        pool.shutdown(wait=False)
    for res in deep_results:
        if _consider(res):
            return best

    # 4) still thin/empty → the paywall ladder as the final attempt
    #    (only for real paywalled outlets or when we have NOTHING — otherwise
    #    it adds a minute of retries for a page that is simply short)
    paywalled = any(h in host for h in _PAYWALL_HOSTS)
    if not bypass_ran and (best is None or (best["word_count"] < 120 and paywalled)):
        bp = _bounded(smart_extract, 25, url, title or "", publisher or "") or {}
        if bp.get("paragraphs"):
            _consider({**bp, "site": (best or {}).get("site") or publisher or "",
                       "published": (best or {}).get("published", ""),
                       "url": url, "via": "bypass:" + (bp.get("bypass") or "")})

    # 5) Search engine snippet extraction (the ultimate safety net for Cloudflare / JS / bot blocks)
    if best is None or best.get("word_count", 0) < 100:
        snip_paras = _search_snippet_paragraphs(title, url, publisher)
        if snip_paras:
            wc = sum(len(p.split()) for p in snip_paras)
            res = {
                "paragraphs": snip_paras[:150],
                "word_count": wc,
                "partial": wc < 120,
                "title": title or "",
                "site": publisher or "",
                "published": "",
                "url": url,
                "resolved_url": url,
                "via": "search-snippets"
            }
            _consider(res)

    if best:
        best["title"] = best.get("title") or title or ""
        return best
    return {"paragraphs": [], "word_count": 0, "partial": True,
            "title": title or "", "site": publisher or "", "published": "",
            "url": url, "resolved_url": None, "via": "none", "error": "all sources empty"}


THIN_RETRY_SECONDS = 300.0     # lead-only / empty body retry window


def _content_fresh(hit) -> bool:
    """A thin (paywalled/JS-blocked) result is NOT final: it is re-run by the
    background job every few minutes so cached stubs heal themselves. The window
    used to be 30 minutes, which meant a publisher that came back (or a rung that
    started working) was not noticed for half an hour."""
    if not hit:
        return False
    if hit.get("via") == "pending":
        return False
    return not (hit.get("partial") and time.time() - hit.get("_at", 0) > THIN_RETRY_SECONDS)


def _schedule_article(art) -> bool:
    """Kick the (up to ~15s) extraction ladder off-thread. Returns True when a
    job was started, False when there is nothing to do."""
    key = art.get("id")
    if not key:
        return False
    with _CONTENT_LOCK:
        hit = CONTENT_CACHE.get(key)
    if key in _ART_INFLIGHT or _content_fresh(hit):
        return False
    if len(_ART_INFLIGHT) >= 8:          # cap concurrent extraction jobs
        return False
    _ART_INFLIGHT.add(key)

    def _job():
        try:
            content = fetch_article_content(
                art.get("link"), title=art.get("title"),
                publisher=art.get("source_name") if art.get("via") else None)
            content["_at"] = time.time()
            with _CONTENT_LOCK:
                old = CONTENT_CACHE.get(key)
                if (old and content.get("word_count", 0) <= old.get("word_count", 0)
                        and not content.get("error")):
                    # the ladder could not beat the copy we already had — keep it,
                    # and postpone the next retry instead of thrashing
                    old["_at"] = time.time()
                    content = old
                else:
                    CONTENT_CACHE[key] = content
            # Persist so a restart does not throw the fetch away and make the
            # reader wait again. Finished *empty* results are saved too: knowing
            # that a paywalled publisher gave nothing is information — without it
            # the first click after every restart waited ~15s to learn nothing.
            if content.get("via") != "pending":
                try:
                    from database import save_body
                    save_body(key, content)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            _ART_INFLIGHT.discard(key)

    threading.Thread(target=_job, daemon=True).start()
    return True


def _schedule_fa(art, content) -> bool:
    """Translate the extracted body off-thread (one Google round trip ≈ 5s)."""
    aid = art.get("id")
    if not aid:
        return False
    fk = aid + "|fa"
    with _FA_CONTENT_LOCK:
        cached_fa = FA_CONTENT_CACHE.get(fk)
    if fk in _ART_INFLIGHT or cached_fa:
        return False
    paras = (content or {}).get("paragraphs") or []
    if not paras:
        return False
    _ART_INFLIGHT.add(fk)

    def _job():
        try:
            fa = translate_paragraphs(paras[:60])
            save_cache()
            with _FA_CONTENT_LOCK:
                FA_CONTENT_CACHE[fk] = fa
            if fa:
                try:
                    from database import save_body
                    save_body(fk, fa)
                except Exception:
                    pass
        except Exception as e:
            log(f"  x content translation failed: {e}")
        finally:
            _ART_INFLIGHT.discard(fk)

    threading.Thread(target=_job, daemon=True).start()
    return True


def article_content_cached(art, want_fa=False):
    """Never blocks the request: returns the cached body when we have one and
    starts the extraction ladder in the background when we do not. The
    returned stub carries `pending: True` so the API can tell the client to
    poll again — that is what removed the 8-15 s spinner on every click."""
    aid = art.get("id")
    if not aid:
        return {
            "paragraphs": [], "word_count": 0, "partial": True,
            "title": "", "site": "", "published": "",
            "url": "", "resolved_url": None, "via": "none",
            "error": "missing_id", "pending": False,
        }
    with _CONTENT_LOCK:
        hit = CONTENT_CACHE.get(aid)
    if _content_fresh(hit):
        return hit
    _schedule_article(art)
    stub = dict(hit) if hit else {
        "paragraphs": [], "word_count": 0, "partial": True,
        "title": art.get("title") or "", "site": "", "published": "",
        "url": art.get("link"), "resolved_url": None, "via": "none",
        "error": None,
    }
    stub["pending"] = True
    return stub


def warm_article_bodies(limit: int = 70):
    """Pre-extract the newest articles in the background so opening one is
    instant. Extraction is network-bound (up to ~15s), and doing it lazily on
    click meant the reader watched a spinner on every first visit; the body is
    now usually already in CONTENT_CACHE before the modal is opened. Runs after
    boot and after every cycle; concurrency is capped by _schedule_article."""
    try:
        with STATE_LOCK:
            arts = [a for a in (STATE.get("articles") or [])
                    if a.get("id") and a.get("link")]
        arts.sort(key=lambda a: -(a.get("published_ts") or 0))
        for a in arts[:limit]:
            with _CONTENT_LOCK:
                cached_art = CONTENT_CACHE.get(a["id"])
            if _content_fresh(cached_art):
                continue
            while len(_ART_INFLIGHT) >= 6:       # let the ladder breathe
                time.sleep(0.5)
            _schedule_article(a)
            time.sleep(0.35)
    except Exception as e:
        log(f"  x body pre-warm stopped: {e}")


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Health & Metrics & Graceful Shutdown
# ---------------------------------------------------------------------------
@app.route("/api/health")
def api_health():
    """Health check endpoint for monitoring."""
    import sqlite3

    start_t = STATE.get("start_time") or STATE.get("stats", {}).get("start_time") or time.time()
    token_gate = bool((os.environ.get("MOHMD_TOKEN", "").strip() or _MOHMD_TOKEN))
    health = {
        "status": "ok",
        # The shared-secret gate is off unless MOHMD_TOKEN is set. When it IS on,
        # these paths still answer without the secret — said out loud here rather
        # than discovered by probing a LAN bind.
        "token_gate": {
            "armed": token_gate,
            "open_without_token": list(TOKEN_GATE_OPEN) if token_gate else [],
            "self_authenticating": list(TOKEN_GATE_EXEMPT) if token_gate else [],
        },
        "timestamp": time.time(),
        "uptime_seconds": time.time() - start_t,
        "cycle": {
            "running": STATE["stats"].get("cycle_running", False),
            "last_duration": STATE["stats"].get("last_duration"),
            "last_success": STATE["stats"].get("last_success"),
            "articles_total": STATE["stats"].get("total_articles") if STATE["stats"].get("total_articles") is not None else len(STATE.get("articles", [])),
            "sources_ok": STATE["stats"].get("ok_sources", 0),
            "sources_err": STATE["stats"].get("err_sources", 0),
        },
        "cache": {
            "content": len(CONTENT_CACHE),
            "fa_content": len(FA_CONTENT_CACHE),
            "fa_report": len(FA_REPORT_CACHE),
            "candles": len(CANDLES_CACHE),
            "macro": len(MACRO_CACHE),
        },
        "db": "unknown",
    }

    # Check DB health
    try:
        from database import DB_FILE
        db_path = DB_FILE if (DB_FILE and DB_FILE.exists()) else Path("E:/freebuff/freebuff.db")
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("SELECT 1")
        conn.close()
        health["db"] = "ok"
    except Exception as e:
        health["db"] = f"error: {e}"
        health["status"] = "degraded"

    # Memory usage
    try:
        proc = psutil.Process(os.getpid())
        health["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
    except Exception:
        pass

    status_code = 200 if health["status"] == "ok" else 503
    return jsonify(health), status_code


@app.route("/api/metrics")
def api_metrics():
    """Prometheus-compatible metrics endpoint."""
    metrics = []
    cycle_running = 1 if STATE["stats"].get("cycle_running") else 0
    duration = STATE["stats"].get("last_duration")
    duration_val = duration if duration is not None else 0
    total_articles = STATE["stats"].get("total_articles")
    total_art_val = total_articles if total_articles is not None else len(STATE.get("articles", []))
    ok_sources = STATE["stats"].get("ok_sources") or sum(1 for s in STATE.get("sources_status", {}).values() if s.get("ok"))
    err_sources = STATE["stats"].get("err_sources") or (len(STATE.get("sources_status", {})) - ok_sources)

    metrics.append(f'freebuff_cycle_running {cycle_running}')
    metrics.append(f'freebuff_cycle_duration_seconds {duration_val}')
    metrics.append(f'freebuff_articles_total {total_art_val}')
    metrics.append(f'freebuff_ok_sources {ok_sources}')
    metrics.append(f'freebuff_err_sources {err_sources}')
    metrics.append(f'freebuff_cache_content {len(CONTENT_CACHE)}')
    metrics.append(f'freebuff_cache_fa_content {len(FA_CONTENT_CACHE)}')
    metrics.append(f'freebuff_cache_fa_report {len(FA_REPORT_CACHE)}')
    metrics.append(f'freebuff_cache_candles {len(CANDLES_CACHE)}')
    return "\n".join(metrics) + "\n", 200, {"Content-Type": "text/plain"}


def _warn_token_gate_exemptions():
    """Say out loud which paths bypass the shared secret.

    The gate is only armed when MOHMD_TOKEN is set, and when it is, these paths
    still answer without it. That is a deliberate trade — the dashboard has no
    way to send the token — but it should be visible at boot rather than
    discovered by probing. /api/health reports the same list.
    """
    if not (os.environ.get("MOHMD_TOKEN", "").strip() or _MOHMD_TOKEN):
        return
    log("token gate armed (MOHMD_TOKEN is set)")
    log("  ↳ open without a token, by design: " + ", ".join(TOKEN_GATE_OPEN))
    log("  ↳ self-authenticating: " + ", ".join(TOKEN_GATE_EXEMPT))
    log("  ↳ to close them, the page must send X-Auth-Token on its fetches first")


_shutdown_flag = False


def _graceful_shutdown(signum=None, frame=None):
    global _shutdown_flag
    if _shutdown_flag:
        return
    _shutdown_flag = True
    logger.info("Graceful shutdown initiated...")

    # 1. Signal scheduler to stop
    STATE["stats"]["shutdown"] = True
    try:
        CYCLE_EVENT.set()
    except Exception:
        pass

    # 2. Save caches to disk
    try:
        save_cache()  # existing function
        logger.info("Caches saved to disk")
    except Exception as e:
        logger.error(f"Failed to save caches: {e}")

    # 3. Log final stats
    logger.info(f"Final stats: {STATE['stats']}")
    logger.info("Shutdown complete")





# Register signal handlers
try:
    signal.signal(signal.SIGTERM, _graceful_shutdown)
except Exception:
    pass
try:
    signal.signal(signal.SIGINT, _graceful_shutdown)
except Exception:
    pass
atexit.register(_graceful_shutdown)


if __name__ == "__main__":
    import sys
    load_config()
    _warn_token_gate_exemptions()

    # Pre-warm the macro / Fear&Greed strips in the background: on a cold
    # cache they cost four Yahoo round trips, which used to add ~2.5s to the
    # very first /api/data the browser asked for after boot.
    threading.Thread(target=lambda: (_macro_cached(), _fng_cached(),
                                     live_prices()),
                     daemon=True).start()

    try:
        from database import init_db, load_articles_for_state, load_bodies
        init_db()
        window_sec = float(CONFIG.get("report_max_age_hours", 24)) * 3600.0
        rec, arch = load_articles_for_state(window_sec)
        if rec or arch:
            with STATE_LOCK:
                STATE["articles"] = rec
                STATE["archive"] = arch
            # hygiene applies to what is already stored, so a changed threshold
            # shows up on the next boot without waiting for a full cycle
            _s1, _s2 = refilter_state()
            if _s1 or _s2:
                log(f"[filter] hydrated set: dropped {_s1} short, {_s2} social")
            log(f"[db] Hydrated {len(rec)} articles and {len(arch)} archive items from SQLite")
        bodies = load_bodies()
        for aid, payload in (bodies or {}).items():
            if aid.endswith("|fa"):
                if isinstance(payload, list) and payload:
                    with _FA_CONTENT_LOCK:
                        FA_CONTENT_CACHE.setdefault(aid, payload)
            elif isinstance(payload, dict) and "word_count" in payload:
                with _CONTENT_LOCK:
                    CONTENT_CACHE.setdefault(aid, payload)      # includes empty results
        if bodies:
            with _CONTENT_LOCK:
                cc_len = len(CONTENT_CACHE)
            with _FA_CONTENT_LOCK:
                facc_len = len(FA_CONTENT_CACHE)
            log(f"[db] Hydrated {cc_len} extracted bodies and "
                f"{facc_len} Persian translations")
    except Exception as _dbe:
        log(f"[db] hydration error: {_dbe}")

    # Warm the newest bodies in the background right away — the modal must
    # never wait for extraction (network-bound, up to ~15s per article).
    threading.Thread(target=warm_article_bodies, daemon=True).start()

    def _studio_signal_loop():
        """Keep the demand providers warm: cold they cost ~10s of network."""
        try:
            import social_signals
        except Exception as e:                   # pragma: no cover - defensive
            log(f"[studio] signals unavailable: {e}")
            return
        while True:
            try:
                social_signals.warm(CONFIG)
            except Exception as e:               # pragma: no cover - defensive
                log(f"[studio] signal warm failed: {e}")
            time.sleep(300)

    threading.Thread(target=_studio_signal_loop, daemon=True).start()

    if "--once" in sys.argv:
        run_cycle("once")
    else:
        threading.Thread(target=run_cycle, kwargs={"reason": "boot"}, daemon=True).start()
        threading.Thread(target=scheduler_loop, daemon=True).start()
        # the push clock: prices + releases leave the server on their own
        # cadence instead of waiting for a browser to ask
        threading.Thread(target=stream_ticker_loop, daemon=True).start()

    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 5055
    print(f"\nDashboard -> http://localhost:{port}   "
          f"(cycle every {CONFIG['interval'] // 60} min, news window "
          f"{CONFIG.get('report_max_age_hours', MAX_AGE_HOURS)}h)\n", flush=True)
    # DL2: localhost by default. Pass --public (or set MOHMD_HOST) only on a
    # trusted network, and set MOHMD_TOKEN to require ?token=... on every call.
    import os as _os
    host = _os.environ.get("MOHMD_HOST") or ("0.0.0.0" if "--public" in sys.argv else "127.0.0.1")
    try:
        # waitress — a real production WSGI server, pure-python, no extra deps.
        # The Werkzeug dev server is thin on threading; waitress holds up
        # under the dashboard's polling + SSE load.
        from waitress import serve
        log(f"waitress: serving on http://{host}:{port} (16 threads)")
        serve(app, host=host, port=port, threads=16)
    except ImportError:
        app.run(host=host, port=port, debug=False, threaded=True)
