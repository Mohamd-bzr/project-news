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
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request, Response

from sources import (SOURCES, ASSETS, TOPICS, TOPIC_ORDER, KIND_LABELS,
                     MAX_AGE_HOURS, REPORT_MIN_CREDIBILITY, PUBLISHER_TRUST)
from collections import deque
from scraper import scrape_all, _fetch_one, deep_recover
from market_data import fetch_market_data, yahoo_candidates
from calendar_data import market_context, _macro_quotes, _fng, market_sessions
from tv_ideas import fetch_ideas, TAG_BY_ASSET
from report_generator import build_all_reports, build_report
from indicators import chart_payload
from translate import translate_many, translate_paragraphs, cache_stats, save_cache
from fa_format import fa_datetime, fa_date, fa_time, fa_ago, fa_digits
from dashboard_html import APP_HTML

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "settings.json"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

DEFAULT_CONFIG = {
    "interval": 1800,                 # 30 minutes
    "assets": list(ASSETS.keys()),
    "custom_assets": {},              # SYM -> {fa, name, icon, yahoo, coingecko, keywords}
    "auto_reports": True,
    "sources_enabled": {k: True for k in SOURCES},
    "custom_sources": {},             # key -> {name, rss, trust}
    "report_max_age_hours": 24,      # default news window (24h) — selectable in settings
}

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
STATE = {
    "articles": [],
    "archive": [],           # older-than-window items kept for the Archive tab
    "market": {},
    "reports": {},
    "sources_status": {},
    "src_hist": {},          # key -> [1/0 per recent cycle] for health sparklines
    "stats": {
        "cycle_running": False,
        "cycles_run": 0,
        "last_update": None,
        "last_duration": None,
        "last_error": None,
        "next_cycle_ts": None,
        "cycle_stats": {},
    },
}
CONFIG = json.loads(json.dumps(DEFAULT_CONFIG))
STATE_LOCK = threading.Lock()
CYCLE_LOCK = threading.Lock()
CYCLE_EVENT = threading.Event()
CONTENT_CACHE = {}
FA_REPORT_CACHE = {}
# manual deep-recovery job state (the Source Health button polls this)
RECOVERY_JOB = {"running": False, "done": 0, "total": 0, "fixed": 0,
                "attempts": 0, "current": "", "log": [],
                "started": 0, "finished": 0}
_RECOVER_LOCK = threading.Lock()


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
    # clamp the news window to sane values (24h default — user-selectable)
    try:
        CONFIG["report_max_age_hours"] = max(6, min(168, float(CONFIG.get("report_max_age_hours", 24))))
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


def save_config():
    try:
        CONFIG_FILE.write_text(json.dumps(CONFIG, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception as e:
        print(f"[config] save failed: {e}", flush=True)


def log(msg):
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
    if not CYCLE_LOCK.acquire(blocking=False):
        log("cycle already running — skip")
        return False
    t0 = time.time()
    with STATE_LOCK:
        STATE["stats"]["cycle_running"] = True
    try:
        log(f"=== cycle start ({reason}) ===")
        meta = all_assets_meta()

        enabled = {k for k, on in CONFIG["sources_enabled"].items() if on}
        news = scrape_all(enabled=enabled or None,
                          custom=CONFIG.get("custom_sources"),
                          custom_assets=CONFIG.get("custom_assets"),
                          max_age_hours=CONFIG.get("report_max_age_hours", MAX_AGE_HOURS))

        want = [s for s in CONFIG["assets"] if s in meta]
        for s in BUILTIN_MACRO:            # macro assets always get price + report
            if s not in want:
                want.append(s)
        symbols, cg = market_maps()
        market = fetch_market_data(assets=want, symbols=symbols, coingecko=cg)
        market = {k: v for k, v in market.items() if k in want}

        reports = {}
        if CONFIG["auto_reports"]:
            reports = build_all_reports(market, news["articles"], want, meta=meta,
                                        max_age=CONFIG.get("report_max_age_hours", MAX_AGE_HOURS))
            for sym, rep in reports.items():
                try:
                    (REPORTS_DIR / f"{sym}.json").write_text(
                        json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

        dur = round(time.time() - t0, 1)
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
            STATE["articles"] = news["articles"]
            STATE["market"] = market
            STATE["reports"] = reports
            for key, st in (news.get("sources") or {}).items():
                STATE["sources_status"][key] = st
                hist = STATE["src_hist"].setdefault(key, [])
                hist.append(1 if st.get("ok") else 0)
                del hist[:-30]      # keep last 30 cycles for the health sparkline
            STATE["stats"].update({
                "cycle_running": False,
                "cycles_run": STATE["stats"]["cycles_run"] + 1,
                "last_update": datetime.now(timezone.utc).isoformat(),
                "last_duration": dur,
                "last_error": None,
                "cycle_stats": news["stats"],
            })
        CONTENT_CACHE.clear()
        FA_REPORT_CACHE.clear()
        try:
            from database import save_articles
            save_articles(news.get("articles") or [])
        except Exception as _dbe:
            log(f"[db] save failed: {_dbe}")
        try:
            _post_cycle_alerts(news["articles"])
        except Exception:
            pass
        log(f"=== cycle done in {dur}s — {news['stats']['total']} articles "
            f"(<{news['stats'].get('max_age_hours')}h), {len(market)} assets, "
            f"{len(reports)} reports ===")
        return True
    except Exception as e:
        traceback.print_exc()
        with STATE_LOCK:
            STATE["stats"].update({"cycle_running": False, "last_error": str(e),
                                   "last_duration": round(time.time() - t0, 1)})
        return False
    finally:
        with STATE_LOCK:
            STATE["stats"]["next_cycle_ts"] = time.time() + CONFIG["interval"]
        CYCLE_LOCK.release()


def scheduler_loop():
    while True:
        run_cycle("scheduled")
        CYCLE_EVENT.wait(CONFIG["interval"])
        CYCLE_EVENT.clear()


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def _ser_article(a):
    ts = a.get("published_ts")
    return {
        "id": a["id"],
        "title": a["title"],
        "title_fa": a.get("title_fa") or "",
        "summary": (a.get("summary") or "")[:260],
        "summary_fa": (a.get("summary_fa") or "")[:260],
        "link": a["link"],
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
        "author": a.get("author", ""),
        "flags": a.get("flags", []),
        "image": a.get("image") or "",
    }


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


@app.before_request
def _dl2_token_guard():
    """Optional shared-secret gate — active only when MOHMD_TOKEN is set.
    The dashboard stays open on localhost; on a LAN/internet bind this keeps
    one accidental exposure from turning the feed into a public endpoint."""
    import os as _os
    need = _os.environ.get("MOHMD_TOKEN", "")
    if not need:
        return None
    if request.path == "/" or request.path.startswith("/api/"):
        given = request.args.get("token") or request.headers.get("X-Auth-Token", "")
        if given != need:
            return Response("unauthorized", status=401)
    return None


@app.route("/")
def index():
    return Response(APP_HTML, mimetype="text/html")


@app.route("/api/data")
def api_data():
    now = time.time()
    with STATE_LOCK:
        recent, older = [], []
        for a in STATE["articles"]:
            (recent if (a.get("published_ts") or 0) >= now - 86400 else older).append(a)
        older = older + [x for x in (STATE.get("archive") or [])
                         if (x.get("published_ts") or 0) < now - 86400]
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
        stats = dict(STATE["stats"])
        assets_meta = all_assets_meta()
        cfg = dict(CONFIG)
        cfg["assets"] = list(CONFIG["assets"]) + [s for s in BUILTIN_MACRO if s not in CONFIG["assets"]]

    topic_counts, asset_counts, kind_counts = {}, {}, {}
    for a in articles:
        topic_counts[a["topic"]] = topic_counts.get(a["topic"], 0) + 1
        kind_counts[a["source_kind"]] = kind_counts.get(a["source_kind"], 0) + 1
        for s in a["assets"]:
            asset_counts[s] = asset_counts.get(s, 0) + 1

    now_iran = datetime.now(timezone.utc).astimezone(IRAN_TZ)
    interval = CONFIG["interval"]
    return jsonify({
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
        "translate": cache_stats(),
        "rules": {"max_age_hours": CONFIG.get("report_max_age_hours", MAX_AGE_HOURS),
                  "min_report_credibility": REPORT_MIN_CREDIBILITY},
        "server_time": now_iran.strftime("%Y-%m-%d %H:%M"),
        "server_time_fa": fa_datetime(now_iran),
        "interval_fa": fa_digits(round(interval / 60)),
    })


@app.route("/api/stats")
def api_stats():
    with STATE_LOCK:
        s = dict(STATE["stats"])
        s["total_articles"] = len(STATE["articles"])
    s["interval"] = CONFIG["interval"]
    return jsonify(s)


@app.route("/api/chart/<sym>")
def api_chart(sym):
    sym = sym.upper()
    meta = all_assets_meta().get(sym)
    if not meta:
        return jsonify({"error": "unknown_symbol"}), 404
    with STATE_LOCK:
        md = STATE["market"].get(sym, {})
    return jsonify(chart_payload(md, sym, meta))


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
    if now - LIVE_CACHE["ts"] < LIVE_TTL and LIVE_CACHE["data"]:
        return LIVE_CACHE["data"]

    meta = all_assets_meta()
    out = {}
    cg_ids, yahoo_syms = {}, {}
    for sym, m in meta.items():
        if CONFIG["assets"] and sym not in CONFIG["assets"]:
            continue
        if m.get("coingecko"):
            cg_ids[m["coingecko"]] = sym
        elif m.get("yahoo"):
            yahoo_syms[sym] = m["yahoo"]

    # 1) CoinGecko — one batched call covers all crypto assets
    if cg_ids:
        try:
            r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                             params={"ids": ",".join(cg_ids), "vs_currencies": "usd",
                                     "include_24hr_change": "true"},
                             headers=HEADERS, timeout=LIVE_TIMEOUT)
            r.raise_for_status()
            for cg_id, vals in r.json().items():
                sym = cg_ids.get(cg_id)
                if sym and vals.get("usd") is not None:
                    out[sym] = {"price": vals["usd"],
                                "change_24h": vals.get("usd_24h_change"),
                                "ts": now, "src": "coingecko"}
        except Exception:
            pass

    # 2) Binance for anything CoinGecko missed (rate limits / new listings)
    for sym in list((set(cg_ids.values()) | set(yahoo_syms)) - set(out)):
        if sym in BUILTIN_CRYPTO or meta.get(sym, {}).get("is_crypto"):
            got = _live_binance(sym)
            if got:
                got.update(ts=now, src="binance")
                out[sym] = got
                continue
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

    LIVE_CACHE["ts"] = now
    LIVE_CACHE["data"] = out
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
ETF_YAHOO = {
    # Bitcoin spot
    "IBIT": "iShares Bitcoin Trust", "FBTC": "Fidelity Wise Origin Bitcoin",
    "BITB": "Bitwise Bitcoin ETF",     "ARKB": "ARK 21Shares Bitcoin",
    "GBTC": "Grayscale Bitcoin Trust", "BTCO": "Invesco Galaxy Bitcoin",
    "HODL": "VanEck Bitcoin Trust",    "BRRR": "Valkyrie Bitcoin Fund",
    "EZBC": "Franklin Bitcoin ETF",   "BTCW": "WisdomTree Bitcoin Fund",
    # Bitcoin futures / short / leveraged
    "BITO": "ProShares Bitcoin Strategy", "BITI": "ProShares Short Bitcoin",
    # Ethereum spot
    "ETHA": "iShares Ethereum Trust",  "FETH": "Fidelity Ethereum Fund",
    "ETHW": "Bitwise Ethereum ETF",    "CETH": "21Shares Core Ethereum",
    "ETHV": "VanEck Ethereum ETF",     "QETH": "Invesco Galaxy Ethereum",
    "EZET": "Franklin Ethereum ETF",   "ETHE": "Grayscale Ethereum Trust",
    "ETH":  "ProShares Ether Strategy",
    # Crypto equity / miners
    "WGMI": "Valkyrie Bitcoin Miners", "BITQ": "Bitwise Crypto Innovators",
    # Metals & commodities
    "GLD": "SPDR Gold Shares",   "IAU": "iShares Gold Trust",
    "SLV": "iShares Silver Trust", "GDX": "VanEck Gold Miners",
    "USO": "United States Oil Fund", "UNG": "United States Natural Gas",
    # Broad market & rates
    "SPY": "SPDR S&P 500", "QQQ": "Invesco QQQ Trust",
    "IWM": "iShares Russell 2000", "TLT": "iShares 20+ Year Treasury",
}
ETF_GROUP = {}
for _s in "IBIT FBTC BITB ARKB GBTC BTCO HODL BRRR EZBC BTCW".split():
    ETF_GROUP[_s] = "Bitcoin"
for _s in "BITO BITI".split():
    ETF_GROUP[_s] = "BTC futures"
for _s in "ETHA FETH ETHW CETH ETHV QETH EZET ETHE ETH".split():
    ETF_GROUP[_s] = "Ethereum"
for _s in "WGMI BITQ".split():
    ETF_GROUP[_s] = "Crypto equity"
for _s in "GLD IAU SLV GDX USO UNG".split():
    ETF_GROUP[_s] = "Commodities"
for _s in "SPY QQQ IWM TLT".split():
    ETF_GROUP[_s] = "Markets"


def _etf_quotes():
    """Per-symbol Yahoo v8 chart meta — free, no key/crumb; cached 60 s."""
    now = time.time()
    if ETF_QUOTES_CACHE["data"] and now - ETF_QUOTES_CACHE["ts"] < 90:
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
            return sym, {"name": ETF_YAHOO.get(sym, sym), "price": price,
                         "change_pct": round(chg, 2) if chg is not None else None,
                         "prev_close": prev, "market_state": m.get("marketState"),
                         "group": ETF_GROUP.get(sym, "Other")}
        except Exception:
            return None
    out = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for res in ex.map(one, list(ETF_YAHOO)):
            if res:
                out[res[0]] = res[1]
    if out:
        ETF_QUOTES_CACHE["data"] = out
        ETF_QUOTES_CACHE["ts"] = now
    return out


@app.route("/api/fng/<sym>")
def api_fng_symbol(sym):
    """Per-asset fear/greed — headlines of the last 24 h for one symbol,
    scored locally (avg credibility-weighted score + fresh-news boost)."""
    sym = (sym or "").upper()
    now = time.time()
    c = FNG_SYM_CACHE.get(sym)
    if c and now - c["ts"] < 900:
        return jsonify({"ok": True, "sym": sym, **c["data"]})
    with STATE_LOCK:
        arts = [a for a in STATE["articles"]
                if sym in (a.get("assets") or [])
                and (a.get("published_ts") or 0) >= now - 86400]
    n = len(arts)
    score = 50.0
    if n:
        weighted, wsum = 0.0, 0.0
        for a in arts:
            w = a.get("credibility") or 0.5
            weighted += w * a.get("sentiment", 0.0)
            wsum += w
        sent = weighted / wsum if wsum else 0.0
        score = 50.0 + 38.0 * max(-1.0, min(1.0, sent))   # -1..1 -> 12..88
        fresh = sum(1 for a in arts if (now - (a.get("published_ts") or 0)) <= 6 * 3600)
        score += min(6.0, fresh)                          # up to +6 for very fresh flow
    score = max(0, min(100, round(score)))
    label = ("Extreme Fear" if score < 25 else "Fear" if score < 45 else
             "Neutral" if score < 55 else "Greed" if score < 75 else "Extreme Greed")
    data = {"now": score, "label": label, "count": n}
    FNG_SYM_CACHE[sym] = {"ts": now, "data": data}
    return jsonify({"ok": True, "sym": sym, **data})


FNG_SYM_CACHE = {}


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
    if not MACRO_CACHE["data"] or now - MACRO_CACHE["ts"] > 300:
        MACRO_CACHE["data"] = _macro_quotes()
        MACRO_CACHE["ts"] = now
    return MACRO_CACHE["data"]


# ---------------------------------------------------------------------------
# live intraday candles — Yahoo v8 chart endpoint (free, key-less)
# powers the TradingView-style candlestick chart in the report panel
# ---------------------------------------------------------------------------
CANDLE_TFS = {
    "5":  {"interval": "5m",  "range": "1d",  "agg": 1},
    "60": {"interval": "60m", "range": "7d",  "agg": 1},
    "4h": {"interval": "60m", "range": "60d", "agg": 4},
    "1d": {"interval": "1d",  "range": "1y",  "agg": 1},
}
CANDLE_TTL = 60.0
CANDLE_MAX = 400                 # cap candles sent to the browser (SVG perf)
CANDLES_CACHE = {}               # (sym, tf) -> {"ts": float, "data": dict}


def _agg_candles(ts, o, h, l, c, v, hours):
    """group 1h candles into `hours` buckets (used for the 4h timeframe)."""
    if hours <= 1:
        return ts, o, h, l, c, v
    T, O, H, L, C, V = [], [], [], [], [], []
    cur = None
    for i in range(len(ts)):
        b = int(ts[i] // (hours * 3600))
        if cur is None or b != cur["b"]:
            if cur:
                T.append(cur["t"]); O.append(cur["o"]); H.append(cur["h"])
                L.append(cur["l"]); C.append(cur["c"]); V.append(cur["v"])
            cur = {"b": b, "t": ts[i], "o": o[i], "h": h[i], "l": l[i], "c": c[i], "v": v[i]}
        else:
            cur["h"] = max(cur["h"], h[i]); cur["l"] = min(cur["l"], l[i])
            cur["c"] = c[i]; cur["v"] = (cur["v"] or 0) + (v[i] or 0)
    if cur:
        T.append(cur["t"]); O.append(cur["o"]); H.append(cur["h"])
        L.append(cur["l"]); C.append(cur["c"]); V.append(cur["v"])
    return T, O, H, L, C, V


def _downsample(ts, o, h, l, c, v, cap=CANDLE_MAX):
    n = len(ts)
    if n <= cap:
        return ts, o, h, l, c, v
    step = n / cap
    idx = [min(n - 1, int(i * step)) for i in range(cap)]
    pick = lambda a: [a[i] for i in idx]
    return pick(ts), pick(o), pick(h), pick(l), pick(c), pick(v)


def _yahoo_candles(yh_symbol: str, interval: str, rng: str):
    for cand in yahoo_candidates(yh_symbol):
        for host in ("query1", "query2"):
            try:
                r = requests.get(
                    f"https://{host}.finance.yahoo.com/v8/finance/chart/{cand}",
                    params={"range": rng, "interval": interval, "includePrePost": "false"},
                    headers=HEADERS, timeout=10)
                if r.status_code != 200:
                    continue
                res = ((r.json().get("chart") or {}).get("result") or [None])[0]
                if not res:
                    continue
                stamp = res.get("timestamp") or []
                q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
                cols = [q.get(k) or [] for k in ("open", "high", "low", "close", "volume")]
                pts = [(t, o_, h_, l_, c_, v_) for t, o_, h_, l_, c_, v_ in zip(stamp, *cols)
                       if c_ is not None and o_ is not None]
                if len(pts) >= 5:
                    return pts
            except Exception:
                continue
    return None


@app.route("/api/candles/<sym>")
def api_candles(sym):
    tf = request.args.get("tf", "60")
    spec = CANDLE_TFS.get(tf)
    if not spec:
        return jsonify({"ok": False, "error": "bad_tf"}), 400
    meta = all_assets_meta().get(sym) or {}
    yh = meta.get("yahoo")
    if not yh:
        return jsonify({"ok": False, "error": "no_symbol"})

    now = time.time()
    hit = CANDLES_CACHE.get((sym, tf))
    if hit and now - hit["ts"] < CANDLE_TTL:
        return jsonify(hit["data"])

    pts = _yahoo_candles(yh, spec["interval"], spec["range"])
    if not pts:
        return jsonify({"ok": False, "error": "no_data"})
    cols = list(zip(*pts))
    T, O, H, L, C, V = _agg_candles(*cols, spec["agg"])
    T, O, H, L, C, V = _downsample(T, O, H, L, C, V)

    out = {"ok": True, "sym": sym, "tf": tf, "t": T, "o": O, "h": H, "l": L, "c": C, "v": V,
           "fa": meta.get("fa"), "icon": meta.get("icon")}
    CANDLES_CACHE[(sym, tf)] = {"ts": now, "data": out}
    return jsonify(out)


def _article_blurb_fa(art, content):
    """One short Persian paragraph: what this news actually is.
    Built from the Persian summary when present, else translated from the
    first full-text paragraph, else from the RSS summary. Cached per article."""
    key = "blurb|" + art["id"]
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
        parts.append(lead if art.get("summary_fa") or (content or {}).get("paragraphs") else lead)
        if (content or {}).get("partial"):
            parts.append("متن کامل به‌دلیل پی‌وال ناقص دریافت شده است.")
        cred = int(round((art.get("credibility") or 0) * 100))
        parts.append(f"اعتبار محتوایی این خبر {fa_digits(cred)}٪ برآورد شده و منبع آن {art.get('source_name','')} است.")
    out = " ".join(parts)
    CONTENT_CACHE[key] = out
    return out


FA_ASSET_NAME = {"BTC": "بیت‌کوین", "ETH": "اتریوم", "SOL": "سولانا", "XRP": "ریپل",
                 "ADA": "کاردانو", "BNB": "بی‌ان‌بی", "DOGE": "دوج‌کوین",
                 "LINK": "چین‌لینک", "XAU": "طلا", "XAG": "نقره"}


@app.route("/api/article/<art_id>")
def api_article(art_id):
    with STATE_LOCK:
        art = next((a for a in STATE["articles"] if a["id"] == art_id), None)
        arts = list(STATE["articles"])
    if not art:
        return jsonify({"error": "not_found"}), 404

    want_fa = request.args.get("fa") in ("1", "true", "yes")
    content = article_content_cached(art, want_fa=want_fa)

    # full translation of the body, on demand and cached on disk
    content_fa = None
    if want_fa and content.get("paragraphs"):
        try:
            content_fa = translate_paragraphs(content["paragraphs"][:60])
            save_cache()
        except Exception as e:
            log(f"  x content translation failed: {e}")

    # short Persian blurb: what this news is about (one compact paragraph)
    blurb_fa = _article_blurb_fa(art, content)

    rel = []
    for a in arts:
        if a["id"] == art_id:
            continue
        overlap = set(a.get("assets", [])) & set(art.get("assets", []))
        if overlap or a.get("topic") == art.get("topic"):
            rel.append({"id": a["id"], "title": a.get("title_fa") or a["title"],
                        "source": a.get("source_name", ""), "score": len(overlap)})
    rel.sort(key=lambda x: -x["score"])

    return jsonify({
        **_ser_article(art),
        "summary_full": art.get("summary", ""),
        "summary_full_fa": art.get("summary_fa", ""),
        "content": content,
        "content_fa": content_fa,
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
        r = requests.get(raw_url, headers=hdrs, timeout=8)
        try:
            declared = int(r.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            declared = 0
        if declared > MAX_IMG_BYTES or len(r.content or b"") > MAX_IMG_BYTES:
            r.close()
            return Response("too_large", status=413)
        if r.status_code == 200:
            mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            if mime.startswith("image/") and len(r.content) > 100:
                try:
                    cached_file.write_bytes(r.content)
                    meta_file.write_text(mime, encoding="utf-8")
                except Exception:
                    pass
                return Response(r.content, mimetype=mime, headers={"Cache-Control": "public, max-age=86400"})
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
            sections.append((kind, {**val, "fa": table.get(val.get("en")) or ""}))
        elif kind == "meta":
            sections.append((kind, {**val,
                                    "asof_fa": val.get("asof_fa") or fa_datetime(val.get("asof"))}))
        else:
            sections.append((kind, val))
    out = {**rep, "sections": sections, "translated": True}
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
    """TradingView public ideas per asset tag (?sym=BTC) or a default bundle."""
    sym = (request.args.get("sym") or "").upper()
    tag = TAG_BY_ASSET.get(sym) or (sym.lower() if sym else "btcusd")
    try:
        items = fetch_ideas(tag, limit=10)
        return jsonify({"ok": True, "tag": tag, "items": items})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "items": []})


# ---------------------------------------------------------------------------
# alerts: price/keyword (browser) + telegram digest (server, after each cycle)
# ---------------------------------------------------------------------------
TG_LOCK = threading.Lock()


def _telegram_cfg():
    tg = CONFIG.get("telegram") or {}
    # DL2: secrets may live in the environment instead of settings.json
    import os as _os
    token = (tg.get("token") or "") or _os.environ.get("MOHMD_TG_TOKEN", "")
    chat = (tg.get("chat") or "") or _os.environ.get("MOHMD_TG_CHAT", "")
    return token.strip(), chat.strip()


def _tg_send(token, chat, text, silent=False):
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat, "text": text, "parse_mode": "HTML",
                                "disable_web_page_preview": True,
                                "disable_notification": bool(silent)},
                          timeout=12)
        return r.status_code == 200
    except Exception:
        return False


TG_TEMPLATE_DEFAULT = ("🏅 <b>{index}. {title}</b>\n"
                       "{summary_fa}\n"
                       "📰 {source} · ⭐ {cred}% · {assets}\n"
                       "🕒 {time_fa}\n"
                       "{link_line}")


def _tg_escape(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _tg_render_digest(articles, tg):
    """Render the digest message from the saved template + settings.
    Supports: hyperlink on title, asset hashtags, emoji, summary on/off,
    credibility stars, Persian or English text."""
    tpl = (tg.get("template") or TG_TEMPLATE_DEFAULT)
    fa = (tg.get("language") or "fa") == "fa"
    include_link = tg.get("include_link", True)
    include_summary = tg.get("include_summary", True)
    hashtags = tg.get("hashtags", True)
    emoji = tg.get("emoji", True)
    show_stars = tg.get("show_stars", True)
    header = tg.get("header") or ("🦅 <b>MOHMD NEWS</b> — خبرهای معتبر چرخه اخیر" if fa
                                  else "🦅 <b>MOHMD NEWS</b> — latest validated news")
    lines = [header + f"\n🕐 {_tg_escape(fa_datetime(datetime.now(timezone.utc)))}\n"]
    for i, a in enumerate(articles, 1):
        title = _tg_escape(a.get("title_fa") or a.get("title") or "")
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
        summ = _tg_escape(a.get("summary_fa") or a.get("summary") or "")
        if len(summ) > 160:
            summ = summ[:157] + "…"
        lead = ("🔔 " if emoji else "")
        link_line = ("🔗 " + url) if (include_link and url and tg.get("link_on_own_line")) else ""
        msg = tpl.format(index=fa_digits(i) if fa else i, title=title_html,
                         summary_fa=(summ + "\n") if include_summary else "",
                         source=_tg_escape(a.get("source_name", "")),
                         cred=(str(fa_digits(cred)) if fa else str(cred)),
                         stars=stars, assets=_tg_escape(assets_txt), tags=tags,
                         time_fa=_tg_escape(fa_time(a.get("published_ts"))),
                         link_line=link_line)
        if not include_summary:
            msg = "\n".join(l for l in msg.splitlines() if l.strip())
        lines.append(lead + msg.strip())
    return "\n\n".join(lines)[:4000]


_ASSET_FA_TG = {"BTC": "بیت‌کوین", "ETH": "اتریوم", "SOL": "سولانا", "XRP": "ریپل",
                "ADA": "کاردانو", "BNB": "بی‌ان‌بی", "DOGE": "دوج‌کوین",
                "LINK": "چین‌لینک", "XAU": "طلا", "XAG": "نقره"}


def _post_cycle_alerts(articles):
    """Telegram digest only (price/keyword alerts were removed by request)."""
    token, chat = _telegram_cfg()
    if not token or not chat:
        return
    tg = CONFIG.get("telegram") or {}
    if tg.get("enabled") is False:
        return
    # quiet hours (Tehran local time): 23:00–07:59 → skip, never spam at night
    if tg.get("quiet_hours", True):
        try:
            hr = datetime.now(IRAN_TZ).hour
            if hr >= 23 or hr < 8:
                return
        except Exception:
            pass
    min_cred = float(tg.get("min_credibility") or 0.75)
    max_items = int(tg.get("max_items") or 10)
    max_age = float(tg.get("max_age_hours") or 6)
    asset_filter = set(tg.get("asset_filter") or [])
    strong = [a for a in articles
              if (a.get("credibility") or 0) >= min_cred and (a.get("age_hours") or 999) <= max_age]
    if asset_filter:
        strong = [a for a in strong if asset_filter & set(a.get("assets") or [])]
    strong.sort(key=lambda a: -(a.get("published_ts") or 0))
    strong = strong[:max_items]
    if not strong:
        return
    text = _tg_render_digest(strong, tg)
    silent = bool(tg.get("silent"))
    pin = bool(tg.get("pin"))
    with TG_LOCK:
        ok = _tg_send(token, chat, text, silent=silent)
        if ok and pin:
            try:
                r = requests.get(f"https://api.telegram.org/bot{token}/pinChatMessage",
                                 params={"chat_id": chat, "disable_notification": True}, timeout=10)
                return r.status_code == 200
            except Exception:
                pass
    return ok


@app.route("/api/telegram/test", methods=["POST"])
def api_telegram_test():
    d = request.get_json(silent=True) or {}
    token = (d.get("token") or "").strip()
    chat = (d.get("chat") or "").strip()
    if not token or not chat:
        return jsonify({"ok": False, "error": "token/chat missing"})
    ok = _tg_send(token, chat, "MOHMD NEWS test message — اتصال تلگرام برقرار است ✓")
    return jsonify({"ok": ok})


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
    return jsonify({"ok": True, "text": _tg_render_digest(strong, tg)})


@app.route("/api/telegram/send-now", methods=["POST"])
def api_telegram_send_now():
    """Send the digest immediately from current state, without waiting for the next cycle."""
    with STATE_LOCK:
        arts = list(STATE["articles"])
    token, chat = _telegram_cfg()
    if not token or not chat:
        return jsonify({"ok": False, "error": "telegram_not_configured"})
    if not arts:
        return jsonify({"ok": False, "error": "no_articles"})
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
    text = _tg_render_digest(strong, tg)
    with TG_LOCK:
        ok = _tg_send(token, chat, text, silent=bool(tg.get("silent")))
    return jsonify({"ok": ok, "sent": len(strong)})


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
            RECOVERY_JOB["feed_names"] = {k: SOURCES[k].get("name", k) for k in broken}
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
                        hist = STATE["src_hist"].setdefault(k, deque(maxlen=30))
                        hist.append(1 if st.get("ok") else 0)
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
        return {k: v for k, v in RECOVERY_JOB.items()
                if k not in ("feed_names",)}


@app.route("/api/recover/status")
def api_recover_status():
    return jsonify(_recover_view())


@app.route("/api/settings", methods=["POST"])
def api_settings():
    data = request.get_json(silent=True) or {}
    added = []

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

    if "report_max_age_hours" in data:
        try:
            h = int(data["report_max_age_hours"])
            if 6 <= h <= 720:
                CONFIG["report_max_age_hours"] = h
        except (TypeError, ValueError):
            pass

    if "source_updates" in data and isinstance(data["source_updates"], dict):
        for k, on in data["source_updates"].items():
            if k in CONFIG["sources_enabled"]:
                CONFIG["sources_enabled"][k] = bool(on)

    if "telegram" in data and isinstance(data["telegram"], dict):
        tg_in = data["telegram"]
        tok = (tg_in.get("token") or "").strip()
        chat = (tg_in.get("chat") or "").strip()
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
    CYCLE_EVENT.set()  # wake the scheduler so changes apply quickly
    return jsonify({"ok": True, "config": CONFIG, "added": added})


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
    text/markdown — the single most effective free fix for JS-rendered news."""
    r = requests.get(f"https://r.jina.ai/{url}",
                     headers={**HEADERS, "Accept": "text/plain"}, timeout=25)
    if r.status_code != 200 or len(r.text) < 300:
        return None
    return r.text


def _proxy_html(url: str, template: str, timeout: int = 4):
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
        if not ln or ln.startswith(("#", "![", "[!", ">", "---", "|", "```")):
            continue
        ln = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", ln)   # [txt](url) → txt
        ln = re.sub(r"[*_`]{1,3}", "", ln)
        if len(ln) < 55:
            continue
        low = ln.lower()
        if any(j in low for j in _JUNK_LINE) and len(ln) < 220:
            continue
        lines.append(ln)
    return title, lines


def _parse_article_html(html: str, url: str, publisher=None, via="direct"):
    """Full DOM/JSON-LD extraction from one HTML document. Adds a statistical
    'densest <p> container' pass so unknown layouts still yield the body."""
    result = {"paragraphs": [], "word_count": 0, "partial": True,
              "title": "", "site": "", "published": "", "url": url,
              "resolved_url": url, "via": via}
    soup = BeautifulSoup(html, "html.parser")

    result["site"] = (soup.find("meta", property="og:site_name") or {}).get("content", "") or ""
    result["title"] = ((soup.find("meta", property="og:title") or {}).get("content")
                      or (soup.title.get_text(strip=True) if soup.title else ""))
    result["published"] = ((soup.find("meta", property="article:published_time") or {})
                           .get("content", "") or "")

    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                     "iframe", "noscript", "form", "button"]):
        tag.decompose()

    paras = []
    body = _jsonld_body(soup)
    if body:
        paras = [p.strip() for p in body.split("\n") if len(p.strip()) > _MIN_PARA]

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
        paras = _paragraphs_from(soup)

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


def fetch_article_content(url, title=None, publisher=None):
    """
    Best-effort *complete* article text, through a ladder of 6+ sources:
      direct fetch → news_bypass (paywall hosts) → r.jina.ai (renders JS) →
      2 raw proxies → Wayback Machine snapshot → Google-News redirect resolution.
    The best result (most words) wins; stops early once a source returns a
    convincing body (≥250 words).
    """
    host = (urlparse(url).netloc.lower() if url else "")
    from news_bypass import smart_extract
    _PAYWALL_HOSTS = ("bloomberg.", "wsj.", "ft.com", "reuters.", "marketwatch.",
                      "nytimes.", "washingtonpost.", "seekingalpha.", "economist.",
                      "forbes.", "investing.com", "businessinsider.")

    # 0) resolve Google News encrypted links to the real publisher URL first
    if "news.google.com" in url:
        resolved = resolve_publisher_url(title or "", publisher or "")
        if resolved:
            url = resolved

    # 0b) the Google News article id is encrypted (`AU_yqL…`), Google serves a
    #     JS consent shell and never 302s to the publisher — so *no* relay source
    #     can recover the body from that URL. Bail out instead of spending ~17s
    #     (the raw-proxy timeouts) for zero words. The caller still has the
    #     headline, source and summary, and marks the result partial so the
    #     resolver is retried later by article_content_cached().
    if "news.google.com" in url:
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

    # 1) paywalled outlet? the tested bypass ladder goes first (bounded — see
    #    _bounded; unbounded it could hold the modal for a minute or more).
    #    bypass_ran stops step 4 from calling the *same* ladder with the same
    #    arguments a second time — it had already timed out once.
    bypass_ran = False
    if any(h in host for h in _PAYWALL_HOSTS):
        bypass_ran = True
        bp = _bounded(smart_extract, 9, url, title or "", publisher or "") or {}
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

    # 3) deep sources — all fetched IN PARALLEL (worst case ≈ slowest source,
    #    not the sum), so a thin article never stalls the modal for minutes
    _GBOT = {**HEADERS, "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
    _BBOT = {**HEADERS, "User-Agent": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"}
    deep_sources = (
        ("jina",       lambda: _jina_reader_text(url),            "text"),
        ("allorigins", lambda: _proxy_html(url, "https://api.allorigins.win/raw?url={q}"), "html"),
        ("codetabs",   lambda: _proxy_html(url, "https://api.codetabs.com/v1/proxy?quest={q}"), "html"),
        ("wayback",    lambda: _wayback_html(url),                "html"),
        # many publishers hand the FULL page to search crawlers while giving
        # browsers the paywall stub — two more parallel getters, zero extra wait
        ("googlebot",  lambda: _ua_fetch(url, _GBOT),             "html"),
        ("bingbot",    lambda: _ua_fetch(url, _BBOT),             "html"),
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
    DEEP_BUDGET = 8.0
    pool = ThreadPoolExecutor(max_workers=6)
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
        bp = _bounded(smart_extract, 9, url, title or "", publisher or "") or {}
        if bp.get("paragraphs"):
            _consider({**bp, "site": (best or {}).get("site") or publisher or "",
                       "published": (best or {}).get("published", ""),
                       "url": url, "via": "bypass:" + (bp.get("bypass") or "")})

    if best:
        best["title"] = best.get("title") or title or ""
        return best
    return {"paragraphs": [], "word_count": 0, "partial": True,
            "title": title or "", "site": publisher or "", "published": "",
            "url": url, "resolved_url": None, "via": "none", "error": "all sources empty"}


def article_content_cached(art, want_fa=False):
    key = art["id"] + ("|fa" if want_fa else "")
    hit = CONTENT_CACHE.get(key)
    if hit:
        # a thin (paywalled/JS-blocked) result is NOT final: re-run the deep
        # ladder once every 30 min so cached stubs heal themselves
        if not (hit.get("partial") and time.time() - hit.get("_at", 0) > 1800):
            return hit
    content = fetch_article_content(art["link"], title=art.get("title"),
                                   publisher=art.get("source_name") if art.get("via") else None)
    content["_at"] = time.time()
    if (hit and content.get("word_count", 0) <= hit.get("word_count", 0)
            and not content.get("error")):
        # deep ladder could not beat the old copy — keep it, postpone retry
        hit["_at"] = time.time()
        return hit
    CONTENT_CACHE[key] = content
    return content


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------
@app.route("/api/health")
def api_health():
    """One-glance machine-readable status for uptime/monitoring checks."""
    with STATE_LOCK:
        st = dict(STATE["stats"])
        total = len(STATE["articles"])
        archive_total = len(STATE.get("archive") or [])
        srcs = dict(STATE["sources_status"])
    ok_src = sum(1 for s in srcs.values() if s.get("ok"))
    return jsonify({
        "ok": True,
        "status": "degraded" if st.get("last_error") else "healthy",
        "articles": total,
        "archive": archive_total,
        "cycles_run": st.get("cycles_run"),
        "cycle_running": st.get("cycle_running"),
        "last_update": st.get("last_update"),
        "last_duration": st.get("last_duration"),
        "last_error": st.get("last_error"),
        "sources": {"total": len(srcs), "ok": ok_src, "failed": len(srcs) - ok_src},
        "interval": CONFIG["interval"],
        "news_window_hours": CONFIG.get("report_max_age_hours"),
        "translate": cache_stats(),
    })


if __name__ == "__main__":
    import sys
    load_config()

    try:
        from database import init_db, load_articles_for_state
        init_db()
        window_sec = float(CONFIG.get("report_max_age_hours", 24)) * 3600.0
        rec, arch = load_articles_for_state(window_sec)
        if rec or arch:
            with STATE_LOCK:
                STATE["articles"] = rec
                STATE["archive"] = arch
            log(f"[db] Hydrated {len(rec)} articles and {len(arch)} archive items from SQLite")
    except Exception as _dbe:
        log(f"[db] hydration error: {_dbe}")

    if "--once" in sys.argv:
        run_cycle("once")
    else:
        threading.Thread(target=run_cycle, kwargs={"reason": "boot"}, daemon=True).start()
        threading.Thread(target=scheduler_loop, daemon=True).start()

    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 5055
    print(f"\nDashboard -> http://localhost:{port}   "
          f"(cycle every {CONFIG['interval'] // 60} min, news window "
          f"{CONFIG.get('report_max_age_hours', MAX_AGE_HOURS)}h)\n", flush=True)
    # DL2: localhost by default. Pass --public (or set MOHMD_HOST) only on a
    # trusted network, and set MOHMD_TOKEN to require ?token=... on every call.
    import os as _os
    host = _os.environ.get("MOHMD_HOST") or ("0.0.0.0" if "--public" in sys.argv else "127.0.0.1")
    app.run(host=host, port=port, debug=False, threaded=True)
