#!/usr/bin/env python3
"""
MOHMD NEWS — Market data snapshots
==========================================
Primary history source: Yahoo Finance chart API (no key, no strict limits)
  - crypto:      BTC-USD, ETH-USD, SOL-USD, XRP-USD, ADA-USD, BNB-USD, DOGE-USD
  - metals:      GC=F (COMEX gold futures ~ انس طلا), SI=F (silver ~ انس نقره)
  - returns daily OHLC + volume for ~6 months → real ATR/indicators

Secondary: CoinGecko simple/price (1 batched call) → market cap + 24h stats.

Resilience: last successful history per symbol is cached on disk
(.market_cache.json); if a live fetch fails, the cached history is used
and flagged stale so reports remain grounded in real (if older) data.
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
CACHE_FILE = BASE_DIR / ".market_cache.json"

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/128.0.0.0 Safari/537.36")}

YAHOO_SYMBOLS = {
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
    "XRP": "XRP-USD", "ADA": "ADA-USD", "BNB": "BNB-USD", "DOGE": "DOGE-USD",
    "XAU": "GC=F", "XAG": "SI=F",
    "WTI": "CL=F", "DXY": "DX-Y.NYB", "SPX": "^GSPC", "VIX": "^VIX",
}

COINGECKO_IDS = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
                 "XRP": "ripple", "ADA": "cardano", "BNB": "binancecoin",
                 "DOGE": "dogecoin"}


# ---------------------------------------------------------------------------
# disk cache
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict):
    """Atomic write — a crash mid-write must never truncate the disk cache."""
    try:
        tmp = CACHE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, CACHE_FILE)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# fetchers
# ---------------------------------------------------------------------------

def yahoo_candidates(symbol: str):
    """
    Users type crypto pairs in every shape. Yahoo only accepts -USD, so a
    symbol like `link-usdt` / `LINKUSDT` is retried as LINK-USD instead of
    silently returning no price.
    """
    s = (symbol or "").strip().upper().replace("/", "-").replace(" ", "")
    if not s:
        return []
    out = [s]
    if s.endswith("-USDT"):
        out.append(s[:-5] + "-USD")
    elif s.endswith("USDT") and "-" not in s:
        out.append(s[:-4] + "-USD")
    if s.endswith("-PERP"):
        out.append(s[:-5])
    if s.endswith("-USD") is False and "-" not in s and s.isalpha() and len(s) <= 5:
        out.append(s + "-USD")
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def _yahoo_chart(yh_symbol: str, rng: str = "1y", interval: str = "1d") -> dict | None:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yh_symbol}"
    try:
        r = requests.get(url, params={"range": rng, "interval": interval},
                         headers=UA, timeout=15)
        r.raise_for_status()
        data = r.json().get("chart", {}).get("result")
        if not data:
            return None
        res = data[0]
        q = res["indicators"]["quote"][0]
        # keep rows aligned: drop a whole row if any of its values is missing
        closes, highs, lows, vols, stamps = [], [], [], [], []
        raw_ts = res.get("timestamp") or []
        seq = list(zip(q.get("close") or [], q.get("high") or [],
                       q.get("low") or [], q.get("volume") or []))
        for i, (c, h, l, v) in enumerate(seq):
            if c is None or h is None or l is None:
                continue
            closes.append(round(c, 6))
            highs.append(round(h, 6))
            lows.append(round(l, 6))
            vols.append(round(v or 0))
            if i < len(raw_ts) and raw_ts[i]:
                stamps.append(datetime.fromtimestamp(raw_ts[i], timezone.utc)
                              .strftime("%Y-%m-%d"))
            else:
                stamps.append("")
        if not closes:
            return None
        return {
            "closes": closes,
            "highs": highs,
            "lows": lows,
            "volumes": vols,
            "timestamps": stamps,
        }
    except Exception as e:
        print(f"[market] yahoo {yh_symbol} failed: {e}", flush=True)
        return None


def _coingecko_simple(cg_map=None) -> dict:
    cg_map = cg_map or COINGECKO_IDS
    ids = ",".join(v for v in cg_map.values() if v)
    url = "https://api.coingecko.com/api/v3/simple/price"
    r = requests.get(url, params={
        "ids": ids, "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_24hr_vol": "true",
        "include_market_cap": "true",
    }, headers=UA, timeout=12)
    r.raise_for_status()
    by_id = {v: k for k, v in cg_map.items() if v}
    out = {}
    for cg_id, vals in r.json().items():
        sym = by_id.get(cg_id)
        if sym:
            out[sym] = vals
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def fetch_market_data(assets=None, symbols=None, coingecko=None,
                      rng: str = "1y") -> dict:
    """
    Combined snapshot. Returns {SYM: {...}} for each requested asset.
    Keys: price, change_24h, volume_24h?, market_cap?, closes, highs, lows,
          volumes, timestamps, stale(bool)

    symbols / coingecko let the caller extend (or override) the built-in maps
    with user-added assets.
    """
    yahoo_map = dict(YAHOO_SYMBOLS)
    yahoo_map.update(symbols or {})
    cg_map = dict(COINGECKO_IDS)
    cg_map.update(coingecko or {})
    assets = assets or list(yahoo_map.keys())
    t0 = time.time()
    cache = _load_cache()
    result = {}

    def fetch_one(sym: str):
        yh = yahoo_map.get(sym)
        if not yh:
            return sym, None, None
        for cand in yahoo_candidates(yh):
            hist = _yahoo_chart(cand, rng=rng)
            if hist:
                return sym, hist, cand
        return sym, None, None

    # parallel history fetch (Yahoo tolerates it fine)
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(fetch_one, s) for s in assets if s in yahoo_map]
        for f in as_completed(futs):
            sym, hist, resolved = f.result()
            if hist:
                if resolved and resolved != (yahoo_map.get(sym) or "").upper():
                    print(f"[market] {sym}: {yahoo_map.get(sym)} -> resolved as {resolved}", flush=True)
                # store a deep snapshot: the enrichment below mutates result
                # rows, and an aliased cache entry let those mutations leak
                # back into the stale fallback — a days-old price then
                # resurrected as "current" on the next outage
                hist["resolved_symbol"] = resolved
                result[sym] = hist
                cache[sym] = {"hist": json.loads(json.dumps(hist)), "ts": time.time()}
            elif sym in cache and cache[sym].get("hist"):
                # stale fallback — price/change reflect the *cached* close;
                # strip enrichment keys so they cannot masquerade as live
                h = json.loads(json.dumps(cache[sym]["hist"]))
                h["stale"] = True
                h.pop("market_cap", None)
                h.pop("volume_24h", None)
                result[sym] = h
                print(f"[market] {sym}: using cached history (stale)", flush=True)
            else:
                print(f"[market] {sym}: no data for {yahoo_map.get(sym)} "
                      f"(tried {', '.join(yahoo_candidates(yahoo_map.get(sym) or ''))})",
                      flush=True)

    _save_cache(cache)

    # enrich crypto with CoinGecko market cap / volume (single call, optional)
    try:
        simple = _coingecko_simple(cg_map)
        for sym, vals in simple.items():
            if sym in result:
                result[sym]["market_cap"] = vals.get("usd_market_cap")
                result[sym]["volume_24h"] = vals.get("usd_24h_vol")
                if vals.get("usd") is not None:
                    result[sym]["price"] = vals["usd"]
                if vals.get("usd_24h_change") is not None:
                    result[sym]["change_24h"] = round(vals["usd_24h_change"], 2)
    except Exception as e:
        print(f"[market] coingecko simple failed (non-fatal): {e}", flush=True)

    # fill price / change from history when missing
    for sym, d in result.items():
        closes = d.get("closes") or []
        if not closes:
            continue
        d.setdefault("price", closes[-1])
        if d.get("change_24h") is None and len(closes) >= 2:
            prev = closes[-2]
            if prev:
                d["change_24h"] = round((closes[-1] - prev) / prev * 100, 2)

    print(f"[market] snapshot for {len(result)}/{len(assets)} assets "
          f"in {time.time()-t0:.1f}s", flush=True)
    return result


if __name__ == "__main__":
    d = fetch_market_data()
    for k, v in sorted(d.items()):
        print(k, "price=", v.get("price"), "chg=", v.get("change_24h"),
              "closes=", len(v.get("closes", [])), "stale=", v.get("stale", False))
