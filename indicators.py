#!/usr/bin/env python3
"""
MOHMD NEWS — Technical indicators
=========================================
Pure-python implementations (EMA, RSI-14 Wilder, MACD 12/26/9, ATR-14
Wilder, Bollinger 20/2, pivot levels). No pandas/numpy needed.
All functions are defensive: they return None/[] instead of raising when
there is not enough data — the report layer omits those sections.
"""

from typing import Optional

def sma(values, period: int) -> Optional[float]:
    if not values or len(values) < period:
        return None
    return sum(values[-period:]) / period


def ema_series(values, period: int):
    if not values or len(values) < period:
        return []
    k = 2.0 / (period + 1)
    e = [sum(values[:period]) / period]  # seed with SMA
    for p in values[period:]:
        e.append(p * k + e[-1] * (1 - k))
    return e


def ema(values, period: int) -> Optional[float]:
    e = ema_series(values, period)
    return e[-1] if e else None


def rsi_wilder(closes, period: int = 14) -> Optional[float]:
    if not closes or len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(closes, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram) latest values."""
    if not closes or len(closes) < slow + signal:
        return None, None, None
    ef = ema_series(closes, fast)
    es = ema_series(closes, slow)
    if not ef or not es:
        return None, None, None
    # Align lengths (EMA series start after their seed periods)
    offset = len(ef) - len(es)
    macd_line = [ef[i + offset] - es[i] for i in range(len(es))]
    sig = ema_series(macd_line, signal)
    if not sig:
        return (macd_line[-1], None, None)
    hist = macd_line[-1] - sig[-1]
    return (macd_line[-1], sig[-1], hist)


def atr14(highs, lows, closes, period: int = 14) -> Optional[float]:
    if not (highs and lows and closes) or len(closes) < period + 1:
        return None
    n = min(len(highs), len(lows), len(closes))
    highs, lows, closes = highs[:n], lows[:n], closes[:n]
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i] - closes[i-1]))
        trs.append(tr)
    if len(trs) < period:
        return None
    a = sum(trs[:period]) / period
    for t in trs[period:]:
        a = (a * (period - 1) + t) / period
    return a


def bollinger(closes, period: int = 20, k: float = 2.0):
    m = sma(closes, period)
    if m is None:
        return None, None, None
    window = closes[-period:]
    var = sum((x - m) ** 2 for x in window) / period
    sd = var ** 0.5
    return (m + k * sd), m, (m - k * sd)


def pct(values, n: int) -> Optional[float]:
    """% change over last n points."""
    if not values or len(values) <= n:
        return None
    a, b = values[-1], values[-1 - n]
    if not b:
        return None
    return (a - b) / b * 100.0


def trend_term(x: Optional[float], thresholds=((0, "flat"),)) -> str:
    """Map a signed number to a word using ordered thresholds."""
    for t, w in thresholds:
        if x is not None and x >= t:
            return w
    return thresholds[-1][1] if thresholds else "flat"


def pivot_levels(closes, lookback: int = 60):
    """Nearest support below spot / resistance above spot from swing extremes."""
    if not closes or len(closes) < 10:
        return None, None
    spot = closes[-1]
    window = closes[-lookback:]
    lo = min(window)
    hi = max(window)
    support = max([p for p in window if p < spot], default=None)
    resistance = min([p for p in window if p > spot], default=None)
    return support, resistance


# ---------------------------------------------------------------------------
# ALIGNED SERIES — for the chart panel beside the report
# ---------------------------------------------------------------------------

def _pad(seq, period, total):
    """Left-pad a series that starts after `period` points with Nones."""
    pad = total - len(seq)
    return [None] * max(0, pad) + list(seq)


def ema_aligned(closes, period: int):
    e = ema_series(closes, period)
    if not e:
        return [None] * len(closes)
    return _pad(e, period, len(closes))


def rsi_series(closes, period: int = 14):
    """Wilder RSI as a list aligned with closes (None during warm-up)."""
    n = len(closes)
    out = [None] * n
    if n < period + 1:
        return out
    deltas = [closes[i] - closes[i - 1] for i in range(1, n)]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(deltas)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
        rs = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + (ag / al if al else 0))
        out[i + 1] = rs
    return out


def macd_series(closes, fast=12, slow=26, signal=9):
    """Aligned MACD line / signal / histogram lists (None during warm-up)."""
    n = len(closes)
    if n < slow + signal:
        return [None] * n, [None] * n, [None] * n
    ef = ema_aligned(closes, fast)
    es = ema_aligned(closes, slow)
    line = [None if (a is None or b is None) else a - b for a, b in zip(ef, es)]
    valid = [v for v in line if v is not None]
    sig_valid = ema_series(valid, signal)
    sig = _pad(sig_valid, signal, len(valid)) if sig_valid else [None] * len(valid)
    sig = [None] * (n - len(sig)) + sig
    hist = [None if (m is None or s is None) else m - s for m, s in zip(line, sig)]
    return line, sig, hist


def bollinger_series(closes, period: int = 20, k: float = 2.0):
    up, mid, low = [], [], []
    for i in range(len(closes)):
        window = closes[max(0, i - period + 1): i + 1]
        if len(window) < period:
            up.append(None); mid.append(None); low.append(None)
            continue
        m = sum(window) / period
        sd = (sum((x - m) ** 2 for x in window) / period) ** 0.5
        up.append(m + k * sd); mid.append(m); low.append(m - k * sd)
    return up, mid, low


def chart_payload(md: dict, sym: str, meta: dict = None, points: int = 180) -> dict:
    """Everything the dashboard chart needs, computed from real history."""
    meta = meta or {}
    closes = list(md.get("closes") or [])
    highs = list(md.get("highs") or [])
    lows = list(md.get("lows") or [])
    vols = list(md.get("volumes") or [])
    ts = list(md.get("timestamps") or [])
    if not closes:
        return {"sym": sym, "empty": True}

    n = len(closes)
    e20 = ema_aligned(closes, 20)
    e50 = ema_aligned(closes, 50)
    e200 = ema_aligned(closes, 200)
    rsi = rsi_series(closes, 14)
    mline, msig, mhist = macd_series(closes)
    bu, bm, bl = bollinger_series(closes, 20, 2.0)

    def tail(seq):
        seq = list(seq) if seq else []
        return seq[-points:] if len(seq) >= points else ([-0.0] * 0) + seq

    sup, res = pivot_levels(closes, min(60, n))
    return {
        "sym": sym,
        "name": meta.get("name", sym),
        "fa": meta.get("fa", sym),
        "icon": meta.get("icon", ""),
        "price": md.get("price"),
        "change_24h": md.get("change_24h"),
        "stale": bool(md.get("stale")),
        "dates": ts[-points:] if ts else [],
        "closes": closes[-points:],
        "ema20": tail(e20),
        "ema50": tail(e50),
        "ema200": tail(e200),
        "bb_up": tail(bu),
        "bb_low": tail(bl),
        "bb_mid": tail(bm),
        "rsi": tail(rsi),
        "macd": tail(mline),
        "macd_signal": tail(msig),
        "macd_hist": tail(mhist),
        "volumes": (vols[-points:] if vols else []),
        "highs": (highs[-points:] if highs else []),
        "lows": (lows[-points:] if lows else []),
        "support": sup,
        "resistance": res,
        "atr14": atr14(highs, lows, closes) if (highs and lows) else None,
        "n": n,
    }


def snapshot(closes, volumes=None, highs=None, lows=None) -> dict:
    """
    Build the full indicator snapshot used by the report generator.
    Returns a flat dict of metrics (any metric may be None).
    """
    closes = list(closes) if closes else []
    snap = {}
    spot = closes[-1] if closes else None
    snap["spot"] = spot
    snap["n"] = len(closes)

    snap["ema20"] = ema(closes, 20)
    snap["ema50"] = ema(closes, 50)
    snap["ema200"] = ema(closes, 200)
    snap["rsi14"] = rsi_wilder(closes, 14)
    m, s, h = macd(closes)
    snap["macd"] = m
    snap["macd_signal"] = s
    snap["macd_hist"] = h
    up, mid, low = bollinger(closes, 20, 2.0)
    snap["bb_up"] = up
    snap["bb_mid"] = mid
    snap["bb_low"] = low
    if highs and lows and closes:
        snap["atr14"] = atr14(highs, lows, closes)
    else:
        snap["atr14"] = None
    if closes:
        sup, res = pivot_levels(closes, 60)
        snap["support"] = sup
        snap["resistance"] = res
    else:
        snap["support"] = snap["resistance"] = None
    snap["chg7d"] = pct(closes, 7)
    snap["chg30d"] = pct(closes, 30)
    snap["chg90d"] = pct(closes, 90)

    if volumes and len(volumes) == len(closes):
        cur = sum(volumes[-7:]) / 7.0
        base = sum(volumes[-30:-7]) / max(1, len(volumes[-30:-7])) if len(volumes) >= 30 else None
        snap["vol_ratio_7d_vs_30d"] = (cur / base) if (base and cur) else None
    else:
        snap["vol_ratio_7d_vs_30d"] = None

    return snap
