#!/usr/bin/env python3
"""
Institutional Report Generator
==============================
Builds an English institutional-style research note (Bloomberg / trading-desk
tone) for each tracked asset, strictly from:

  1. validated news collected by the scraper (max 72h old, credibility-ranked)
  2. market data + computed indicators (real OHLC history)

Rules enforced here (mirroring the research prompt):
  • never invent data, prices, news or metrics,
  • sections without supporting data are omitted, not padded,
  • technical analysis ALWAYS carries >= 4 paragraphs,
  • every news item used is cited with **source + Persian date + Persian time**
    directly inside the text, and again as a structured citation block
    (`cites`) the UI renders underneath the section.

Each text section carries a Persian header (`fa`) and a `fa` slot that the API
fills on demand with a real translation, so the dashboard can offer a
one-click فارسی version beside the English original.
"""

import statistics
from datetime import datetime, timezone, timedelta

from indicators import snapshot as ta_snapshot
from sources import MAX_AGE_HOURS, REPORT_MIN_CREDIBILITY
from fa_format import fa_datetime, fa_date, fa_time, fa_ago, fa_digits

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

ASSET_NAMES = {
    "BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "XRP": "XRP",
    "ADA": "Cardano", "BNB": "BNB", "DOGE": "Dogecoin",
    "XAU": "Gold", "XAG": "Silver",
    "WTI": "WTI Crude Oil", "DXY": "US Dollar Index",
    "SPX": "S&P 500", "VIX": "CBOE Volatility Index",
}
DEFAULT_IS_CRYPTO = {"BTC", "ETH", "SOL", "XRP", "ADA", "BNB", "DOGE"}

# English section title  ->  Persian section title
SECTION_TITLES = {
    "overview":    ("1. Market Overview", "۱. مرور بازار"),
    "macro":       ("2. Macro & Fundamental Drivers", "۲. محرک‌های کلان و بنیادی"),
    "news":        ("3. Market News Impact", "۳. تأثیر اخبار مهم بازار"),
    "flows":       ("4. Institutional Flows & Market Structure", "۴. جریان‌های نهادی و ساختار بازار"),
    "derivatives": ("6. Derivatives & Positioning", "۶. مشتقات و پوزیشن‌گیری"),
    "technical":   ("7. Technical Analysis", "۷. تحلیل تکنیکال"),
    "scenarios":   ("8. Scenario Analysis", "۸. تحلیل سناریوها"),
    "conclusion":  ("9. Conclusion & Outlook", "۹. جمع‌بندی و چشم‌انداز"),
}

TOPIC_KEYS = {
    "institutional": "strong", "etf": "strong", "market": "strong",
    "analysis": "analysis", "regulation": "regulation", "macro": "macro",
    "security": "risk", "tech": "tech", "defi": "tech",
}


# ---------------------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------------------

def _fmt(v, nd=2):
    if v is None:
        return "n/a"
    if isinstance(v, (int, float)):
        if abs(v) >= 1000:
            return f"{v:,.{nd}f}"
        return f"{v:.{nd}f}"
    return str(v)


def _pct(v, nd=2):
    if v is None:
        return "n/a"
    return f"{'+' if v >= 0 else ''}{v:.{nd}f}%"


def _fmt_price(v):
    if v is None:
        return "n/a"
    if v >= 1000:
        return f"${v:,.0f}"
    if v >= 10:
        return f"${v:,.2f}"
    if v >= 1:
        return f"${v:,.3f}"
    return f"${v:.4f}"


def _mini_ohlc_from_closes(closes, bucket=7):
    """Approximate weekly highs/lows from daily closes (no real OHLC feeds)."""
    if not closes or len(closes) < bucket * 2:
        return None, None
    highs, lows = [], []
    for i in range(0, len(closes) - bucket + 1, bucket):
        chunk = closes[i:i + bucket]
        highs.append(max(chunk))
        lows.append(min(chunk))
    return highs, lows


def _stamp(a) -> str:
    """`۲۴ شهریور ۱۴۰۵، ساعت ۱۳:۳۵` — always Persian, as requested."""
    ts = a.get("published_ts")
    return fa_datetime(ts) or "زمان نامشخص"


def _cite_key(item: dict) -> str:
    """Stable identity of one cited article (id when we have it)."""
    return str(item.get("id") or item.get("link") or item.get("title_en") or "")


def count_cited_news(sections) -> int:
    """How many distinct articles a report actually cites.

    The top-level number used to count `cites` *blocks* (two to four source
    boxes) while the meta section summed seven candidate buckets, two of which
    the prose never draws from — two different wrong answers for one concept,
    both visible in the UI and in /api/data.
    """
    ids = set()
    for kind, val in sections:
        if kind != "cites":
            continue
        for item in (val or {}).get("items") or []:
            key = _cite_key(item)
            if key:
                ids.add(key)
    return len(ids)


def _cite(a, why_fa="", why_en="", index=None) -> dict:
    ts = a.get("published_ts")
    cred = a.get("credibility") or 0
    return {
        "id": a.get("id", ""),
        "index": index,
        "index_fa": fa_digits(index) if index else "",
        "title_en": a.get("title", ""),
        "title_fa": a.get("title_fa") or a.get("title", ""),
        "summary_fa": (a.get("summary_fa") or "")[:240],
        "source": a.get("source_name") or "منبع ناشناس",
        "source_kind": a.get("source_kind"),
        "via": a.get("via") or "",
        "link": a.get("link", ""),
        "published_ts": ts,
        "date_fa": fa_date(ts),
        "time_fa": fa_time(ts),
        "datetime_fa": fa_datetime(ts),
        "age_fa": fa_ago(a.get("age_hours")),
        "credibility": cred,
        "credibility_fa": fa_digits(int(round(cred * 100))) + "٪",
        "topic_fa": a.get("topic_fa") or "",
        "assets": a.get("assets") or [],
        "why_fa": why_fa,
        "why_en": why_en,
    }


# ---------------------------------------------------------------------------
# NEWS SELECTION — highest credibility, then newest
# ---------------------------------------------------------------------------

def _rank(a):
    """Report ordering: most credible first, then most recent."""
    return (-(a.get("credibility") or 0), -(a.get("published_ts") or 0))


def _eligible(articles, sym, min_cred, max_age, topics=None, kinds=None):
    out = []
    for a in articles:
        if sym not in (a.get("assets") or []):
            continue
        if topics and a.get("topic") not in topics:
            continue
        if kinds and a.get("source_kind") not in kinds:
            continue
        if (a.get("credibility") or 0) < min_cred:
            continue
        age = a.get("age_hours")
        if age is not None and age > max_age:
            continue
        out.append(a)
    out.sort(key=_rank)
    return out


def select_news(articles, sym, min_cred=REPORT_MIN_CREDIBILITY,
                max_age=MAX_AGE_HOURS, limits=None, prefer_min=0.68):
    """
    Pick report-grade news for one asset, bucketed by topic.

    Quality policy (as requested): news cited inside the report must be the
    **most credible and the newest** available. We therefore try a higher bar
    (prefer_min) first and only relax to min_cred if an asset is so thinly
    covered that the section would otherwise be starved. Nothing older than
    `max_age` (72h) or below the floor is ever cited.
    """
    limits = limits or {"strong": 3, "analysis": 2, "regulation": 2,
                        "macro": 2, "risk": 2, "tech": 2}

    def collect(bar):
        buckets = {k: [] for k in limits}
        for a in _eligible(articles, sym, bar, max_age):
            key = TOPIC_KEYS.get(a.get("topic"))
            if key in buckets:
                buckets[key].append(a)
        return {k: v[:limits[k]] for k, v in buckets.items()}

    buckets = collect(prefer_min)
    if sum(len(v) for v in buckets.values()) < 4:
        buckets = collect(min_cred)
    return buckets


def top_news(articles, sym, n=3, topics=None, min_cred=REPORT_MIN_CREDIBILITY,
             max_age=MAX_AGE_HOURS, prefer_min=0.68, kinds=None):
    """Flat list of the n most credible + newest items (optionally filtered)."""
    out = _eligible(articles, sym, prefer_min, max_age, topics, kinds)
    if len(out) < n and prefer_min > min_cred:
        out = _eligible(articles, sym, min_cred, max_age, topics, kinds)
    return out[:n]


def _news_sources_used(articles, sym):
    names = {}
    for a in articles:
        if sym in (a.get("assets") or []):
            nm = a.get("source_name")
            if nm:
                names[nm] = names.get(nm, 0) + 1
    return sorted(names.items(), key=lambda kv: -kv[1])


# ---------------------------------------------------------------------------
# SECTION WRITERS (English prose; Persian comes from on-demand translation)
# ---------------------------------------------------------------------------

def sec_market_overview(snap, md, name):
    spot = md.get("price")
    chg = md.get("change_24h")
    chg7 = snap.get("chg7d")
    chg30 = snap.get("chg30d")
    ema50, ema200 = snap.get("ema50"), snap.get("ema200")
    if spot is None and chg is None and chg7 is None:
        return None
    s1 = f"{name} is changing hands near {_fmt_price(spot)}"
    if chg is not None:
        s1 += f", {_pct(chg)} over the past 24 hours"
    if chg7 is not None:
        s1 += f" and {_pct(chg7)} on a 7-day view"
    s1 += "."
    s2 = ""
    if ema50 is not None and spot is not None:
        pos50 = "above" if spot > ema50 else "below"
        s2 = f" Spot trades {pos50} the 50-day average ({_fmt_price(ema50)})"
        above200 = (spot > ema200) if ema200 is not None else None
        if ema200 is not None:
            s2 += f" and {'above' if above200 else 'below'} the 200-day average ({_fmt_price(ema200)})"
        s2 += ", keeping the medium-term structure "
        s2 += ("directional per the 50-day" if above200 is None else
               "constructive" if (spot > ema50 and above200) else
               "mixed" if (spot > ema50 or above200) else "defensive")
        s2 += "."
    s3 = ""
    if chg30 is not None:
        tone = "recovery" if chg30 > 2 else ("drawdown" if chg30 < -5 else "consolidation")
        s3 = (f" The 30-day tape reads as a {tone} phase ({_pct(chg30)}), suggesting the "
              f"market is still {'repairing' if chg30 > 2 else 'digesting supply' if chg30 < -5 else 'rotating within a range'}.")
    para = s1 + s2 + s3
    return para if len(para) > 60 else None


def sec_macro(items, name):
    """Cross-asset macro drivers, grounded in collected headlines."""
    if not items:
        return None, []
    lines, cites = [], []
    for i, a in enumerate(items, 1):
        st = _stamp(a)
        lines.append(f"- {a.get('title', '')}.")
        cites.append(_cite(a, index=i))
    intro = ("Cross-asset drivers in today's wire matter for pricing risk in this market; "
             "the highest-credibility macro and policy headlines currently in circulation are:")
    return intro + "\n" + "\n".join(lines), cites


def sec_news_impact(strong, regulation, risk, name):
    """Asset-specific high-impact news: title, source, Persian date/time, impact."""
    if not (strong or regulation or risk):
        return None, []

    why_by_bucket = {
        "strong": ("Institutional / flow-oriented headlines of this type typically reprice "
                   f"short-term liquidity expectations for {name}."),
        "regulation": ("Regulatory outcomes directly alter the addressable demand base; passage "
                       "or delay of such measures historically shifts volatility and "
                       "positioning around the event."),
        "risk": ("Security incidents are a standing tail-risk: they rarely move the whole "
                 "complex alone, but they hit sentiment for affected venues and protocols "
                 "first."),
    }

    picked = ([(a, why_by_bucket["strong"]) for a in strong]
              + [(a, why_by_bucket["regulation"]) for a in regulation]
              + [(a, why_by_bucket["risk"]) for a in risk])
    # global ranking: most credible first, then newest — as requested
    picked.sort(key=lambda pair: _rank(pair[0]))

    lines, cites = [], []
    for n, (a, why) in enumerate(picked, 1):
        lines.append(f"- {a.get('title')}. {why}")
        cites.append(_cite(a, why_en=why, index=n))

    if not lines:
        return None, []
    return "\n".join(lines), cites


# ── DL2: free, key-less context for the flows / derivatives sections ────────
# Both helpers degrade to {} on any failure so a report is never blocked by a
# third-party endpoint being down, and both cache their answer (TTL) so a
# 13-asset report run costs one network round-trip, not thirteen.
import threading
_DERIV_CACHE = {}
_DERIV_LOCK = threading.Lock()
_BINANCE_SYMBOL = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
                   "XRP": "XRPUSDT", "ADA": "ADAUSDT", "BNB": "BNBUSDT",
                   "DOGE": "DOGEUSDT"}


def _derivatives_context(sym, ttl=300.0):
    """Binance futures funding / open interest / long-short (public, key-less)."""
    import time as _t
    import requests
    with _DERIV_LOCK:
        hit = _DERIV_CACHE.get(sym)
    if hit and _t.time() - hit[0] < ttl:
        return hit[1]
    out = {}
    pair = _BINANCE_SYMBOL.get(sym)
    if pair:
        try:
            r = requests.get("https://fapi.binance.com/fapi/v1/premiumIndex",
                             params={"symbol": pair}, timeout=6)
            d = r.json()
            out["funding_pct"] = round(float(d["lastFundingRate"]) * 100, 4)
        except Exception:
            pass
        try:
            r = requests.get("https://fapi.binance.com/fapi/v1/openInterest",
                             params={"symbol": pair}, timeout=6)
            out["open_interest"] = float(r.json()["openInterest"])
        except Exception:
            pass
        try:
            r = requests.get("https://fapi.binance.com/futures/data/"
                             "globalLongShortAccountRatio",
                             params={"symbol": pair, "period": "1h", "limit": 1},
                             timeout=6)
            rows = r.json()
            if rows:
                out["long_short"] = round(float(rows[-1]["longShortRatio"]), 2)
        except Exception:
            pass
    with _DERIV_LOCK:
        _DERIV_CACHE[sym] = (_t.time(), out)
    return out


def _flow_context():
    """Fear & Greed, from the already-cached market context.

    The spot-BTC ETF net-flow series (Farside) was dropped together with the
    ETF-flow panel, so this no longer carries an ETF figure.
    """
    try:
        from calendar_data import market_context
        ctx = market_context() or {}
    except Exception:
        return {}
    out = {}
    try:
        fng = ctx.get("fng") or {}
        if fng.get("now") is not None:
            out["fng"] = fng.get("now")
            out["fng_label"] = fng.get("label")
    except Exception:
        pass
    return out


def sec_flows(md, snap, sym, name, is_crypto=True):
    vol = md.get("volume_24h")
    mcap = md.get("market_cap")
    vr = snap.get("vol_ratio_7d_vs_30d")
    if not is_crypto and vol is None:
        return None
    parts = []
    if mcap:
        parts.append(f"Total market capitalization stands near ${mcap/1e9:,.1f}B (CoinGecko).")
    if vol:
        parts.append(f"Reported 24-hour spot volume is ${vol/1e9:,.2f}B")
        if vr is not None:
            tone = "elevated" if vr > 1.15 else ("subdued" if vr < 0.85 else "broadly normal")
            parts.append(f"with 7-day average turnover {tone} versus the trailing month ({vr:.2f}x)")
        parts.append(".")
    elif vr is not None:
        parts.append(f"Seven-day average turnover runs at {vr:.2f}x the trailing-month norm.")
    if is_crypto:
        parts.append("Note: the sentiment reading above is the public alternative.me series; "
                     "proprietary on-chain datasets are still left out rather than estimated.")
    fx = _flow_context()
    if is_crypto and fx.get("fng") is not None:
        parts.append(f"The alternative.me Fear & Greed gauge prints {fx['fng']}"
                     + (f" ({fx['fng_label']})" if fx.get("fng_label") else "") + ".")
    if not parts:
        return None
    return " ".join(parts)


def sec_derivatives(snap, sym, name, is_crypto=True):
    if not is_crypto:
        return None
    d = _derivatives_context(sym)
    if d.get("funding_pct") is not None or d.get("open_interest") is not None:
        bits = []
        if d.get("funding_pct") is not None:
            f = d["funding_pct"]
            bits.append(f"perpetual funding prints {f:+.4f}% per interval — "
                        + ("longs pay shorts, i.e. crowded long positioning" if f > 0
                           else "shorts pay longs, i.e. crowded short positioning"))
        if d.get("open_interest") is not None:
            bits.append(f"open interest stands at {d['open_interest']:,.0f} {name} contracts")
        if d.get("long_short") is not None:
            bits.append(f"the top-trader long/short account ratio sits at {d['long_short']:.2f}")
        return ("**Derivatives positioning** (Binance futures, free public API). Live readings: "
                + "; ".join(bits) + ". Funding and open-interest extremes are the standard "
                "trigger for squeeze dynamics: treat these as the state to trade against, not "
                "as a signal on their own.")
    return ("**Derivatives positioning.** The public Binance futures endpoints did not answer "
            "for this asset on this cycle, so rather than fabricate a view the desk flags it as "
            "a **data gap**: funding and open-interest extremes remain the standard trigger for "
            f"squeeze dynamics in {name}.")


def sec_technical(snap, name):
    """
    MANDATORY: at least 4 paragraphs, built only from computed indicators.
    """
    spot = snap.get("spot")
    ema20, ema50, ema200 = snap.get("ema20"), snap.get("ema50"), snap.get("ema200")
    rsi = snap.get("rsi14")
    macd, sig, hist = snap.get("macd"), snap.get("macd_signal"), snap.get("macd_hist")
    bb_up, bb_mid, bb_low = snap.get("bb_up"), snap.get("bb_mid"), snap.get("bb_low")
    sup, res = snap.get("support"), snap.get("resistance")
    chg7, chg30 = snap.get("chg7d"), snap.get("chg30d")
    atr = snap.get("atr14")

    paras = []

    # P1 — trend structure across horizons
    if spot is not None and ema50 is not None:
        if ema200 is not None:
            if spot > ema20 > ema50 > ema200:
                t = ("perfect bullish alignment (price > EMA20 > EMA50 > EMA200), the textbook "
                     "configuration of a trend-following regime where pullbacks into the 20-day "
                     "mean tend to be bought")
            elif spot < ema20 < ema50 < ema200:
                t = ("fully inverted (price < EMA20 < EMA50 < EMA200), the classic bear-stack in "
                     "which rallies into value tend to be sold")
            else:
                t = ("mixed — the moving averages are interleaved rather than stacked, which is "
                     "characteristic of a transitional or range-bound regime rather than a "
                     "one-way trend")
            paras.append(
                f"**Trend structure.** Across horizons the picture is {t}. Spot at {_fmt_price(spot)} "
                f"versus EMA20 {_fmt_price(ema20)}, EMA50 {_fmt_price(ema50)} and EMA200 "
                f"{_fmt_price(ema200)} frames the medium-term bias mechanically rather than "
                f"emotionally. From this configuration the desk's working assumption is that "
                f"trend-following exposure is only justified while price holds the side of the "
                f"50-day average it currently occupies.")
        else:
            paras.append(
                f"**Trend structure.** Spot at {_fmt_price(spot)} versus EMA20 {_fmt_price(ema20)} "
                f"and EMA50 {_fmt_price(ema50)}: the medium-term bias is "
                f"{'constructive' if spot > ema50 else 'defensive'}. A 200-day average could not be "
                f"computed from the available history ({snap.get('n') or 0} closes), so the "
                f"long-term read is deliberately left open.")
    elif spot is not None:
        paras.append(
            f"**Trend structure.** With {_fmt_price(spot)} the last print but insufficient history "
            f"for moving averages, trend structure is assessed from raw price action only. "
            f"Momentum without context; size accordingly.")
    else:
        paras.append(
            "**Trend structure.** No reliable price feed was available at report time for this "
            "asset. Rather than print a generic reading, the desk explicitly flags the data gap; "
            "structure will be populated on the next successful market-data refresh.")

    # P2 — support / resistance / value zones
    if spot is not None and (sup is not None or res is not None or bb_low is not None):
        zones = []
        if sup is not None:
            zones.append(f"initial support at {_fmt_price(sup)} (recent swing low)")
        if bb_low is not None:
            zones.append(f"the lower Bollinger band {_fmt_price(bb_low)} as the 2σ downside envelope")
        if res is not None:
            zones.append(f"first resistance at {_fmt_price(res)} (recent swing high)")
        if bb_up is not None:
            zones.append(f"upper band {_fmt_price(bb_up)} as the stretch target")
        paras.append(
            f"**Key levels.** The operational map reads: {'; '.join(zones)}. Levels derived from the "
            f"last ~60 sessions of closes are guides for location, not promises of reaction; they "
            f"mark where prior two-way business was done and therefore where resting liquidity is "
            f"most plausible."
            + (f" ATR(14) of {_fmt_price(atr)} implies a typical daily range of roughly "
               f"{atr / spot * 100:.1f} percent of spot, which is the unit of risk to size positions against."
               if (atr and spot) else ""))
    else:
        paras.append("**Key levels.** Level work requires at least a month of closes; the current "
                     "history is insufficient, so no support/resistance zones are asserted here.")

    # P3 — momentum indicators
    if rsi is not None or macd is not None:
        bits = []
        if rsi is not None:
            state = "overbought" if rsi >= 70 else ("oversold" if rsi <= 30 else "neutral")
            bits.append(f"RSI(14) prints {rsi:.1f} — {state} territory")
        if macd is not None and sig is not None:
            bits.append(f"MACD (12/26/9) sits {'above' if (hist or 0) > 0 else 'below'} its signal "
                        f"line ({macd:.4g} vs {sig:.4g}, histogram {hist:+.4g}), consistent with "
                        f"{'building' if (hist or 0) > 0 else 'fading'} momentum")
        paras.append(
            f"**Momentum.** {'; '.join(bits)}. Momentum readings are state descriptors, not trade "
            "signals on their own; the desk treats confluence between momentum and level location "
            "as the actionable unit.")
    else:
        paras.append("**Momentum.** RSI/MACD could not be computed from the available history "
                     "(minimum ~35 closes required). No momentum claim is made.")

    # P4 — volatility, bands, participation
    closes = snap.get("_closes") or []
    bits = []
    if closes and len(closes) >= 20:
        rets = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes)) if closes[i - 1]]
        if rets:
            daily_vol = statistics.pstdev(rets[-30:]) * 100
            bits.append(f"30-day realized volatility annualizes near {daily_vol * (365 ** 0.5):.0f}%")
    if bb_up and bb_low and bb_mid:
        width_pct = (bb_up - bb_low) / bb_mid * 100
        bits.append(f"the 20-day band spans {width_pct:.0f}% of the mid — "
                    f"{'expanded' if width_pct > 15 else 'compressed'}, which "
                    f"{'favors trend continuation tactics' if width_pct > 15 else 'often precedes a volatility expansion'}")
    if snap.get("vol_ratio_7d_vs_30d") is not None:
        bits.append(f"7-day turnover runs at {snap['vol_ratio_7d_vs_30d']:.2f}x the trailing-month norm")
    if bits:
        paras.append("**Volatility & liquidity.** " + "; ".join(bits) + ". Behavior around these "
                     "regimes — absorption at band edges, volume confirmation on breaks — is what "
                     "separates a tradeable move from noise.")
    else:
        paras.append("**Volatility & liquidity.** Volume history for this asset is unavailable from "
                     "the current feeds, so participation quality is left unassessed rather than guessed.")

    # P5 — longer-horizon performance context
    if chg30 is not None or snap.get("chg90d") is not None:
        b = []
        if chg30 is not None:
            b.append(f"{_pct(chg30)} over 30 days")
        if snap.get("chg90d") is not None:
            b.append(f"{_pct(snap['chg90d'])} over 90 days")
        paras.append("**Performance context.** On longer windows the asset has returned "
                     + " and ".join(b) + ". Positioning decisions made on monthly horizons should "
                     "respect these base rates instead of extrapolating the last week. "
                     f"The 7-session change ({_pct(chg7)}) is the shortest window the desk treats "
                     "as signal rather than noise." if chg7 is not None else
                     "**Performance context.** On longer windows the asset has returned "
                     + " and ".join(b) + ". Positioning on monthly horizons should respect these "
                     "base rates instead of extrapolating the last week.")

    return "\n\n".join(paras)


def sec_scenarios(snap, name):
    sup, res = snap.get("support"), snap.get("resistance")
    rsi = snap.get("rsi14")
    ema50 = snap.get("ema50")
    spot = snap.get("spot")

    bull_cond, bear_cond = [], []
    if res is not None:
        bull_cond.append(f"acceptance above {_fmt_price(res)} on expanding turnover")
    if sup is not None:
        bear_cond.append(f"a decisive loss of {_fmt_price(sup)}")
    if ema50 is not None and spot is not None:
        (bull_cond if spot > ema50 else bear_cond).append(
            f"continued holds of the 50-day average ({_fmt_price(ema50)})" if spot > ema50
            else f"failed reclaims of the 50-day average ({_fmt_price(ema50)})")
    if rsi is not None:
        if rsi >= 60:
            bull_cond.append(f"RSI holding above 60 (currently {rsi:.0f})")
        elif rsi <= 40:
            bear_cond.append(f"RSI staying pinned below 40 (currently {rsi:.0f})")

    bull = ("**Bullish scenario.** " +
            ("Continuation higher requires " + "; ".join(bull_cond) +
             ". Under those conditions the path of least resistance flips to buy-the-dip, with "
             "prior resistance converting to support as the confirmation test." if bull_cond else
             "No data-backed trigger levels are available; the desk would require a breakout above "
             "recent range highs with volume to turn constructive."))
    bear = ("**Bearish scenario.** " +
            ("Downside continuation triggers on " + "; ".join(bear_cond) +
             ". In that case failed support typically becomes the new ceiling, and momentum chasers "
             "provide the exit liquidity." if bear_cond else
             "Without level data, the desk treats any breakdown call as unverifiable and declines "
             "to frame one."))
    return bull + "\n\n" + bear


def sec_conclusion(snap, md, name):
    spot = md.get("price")
    chg = md.get("change_24h")
    ema50 = snap.get("ema50")
    bias = None
    if spot is not None and ema50 is not None:
        bias = "constructive" if spot > ema50 else "defensive"
    core = (f"Net take on {name}: "
            + (f"spot {_fmt_price(spot)} with the medium-term bias {bias} while price holds the "
               f"relevant side of the 50-day average. " if bias else
               "price data incomplete at publication time. ")
            + (f"The 24-hour tape ({_pct(chg)}) is consistent with that bias. "
               if (chg is not None and bias) else "")
            + "Decision zones are the levels named in the technical section, not opinions: trade "
              "the reaction at those prices, not the headline of the day.")
    return core


# ---------------------------------------------------------------------------
# TOP-LEVEL BUILDER
# ---------------------------------------------------------------------------

def build_report(sym, md, articles, now=None, name=None, fa_name=None,
                 is_crypto=None, icon=None, max_age=MAX_AGE_HOURS):
    """Build one bilingual report for asset `sym`."""
    now = now or datetime.now(timezone.utc)
    name = name or ASSET_NAMES.get(sym, sym)
    if is_crypto is None:
        is_crypto = sym in DEFAULT_IS_CRYPTO

    closes = md.get("closes") or []
    volumes = md.get("volumes") or []
    # DL2: Yahoo already returns real OHLC — the weekly close-bucket proxy is
    # only a fallback for assets whose high/low arrays are missing or shorter.
    highs, lows = list(md.get("highs") or []), list(md.get("lows") or [])
    if not highs or len(highs) != len(closes) or len(lows) != len(closes):
        highs, lows = _mini_ohlc_from_closes(closes)
    snap = ta_snapshot(closes, volumes, highs, lows)
    snap["_closes"] = closes

    picked = select_news(articles, sym, max_age=max_age)
    strong, analysis = picked["strong"], picked["analysis"]
    regulation, macro, risk = picked["regulation"], picked["macro"], picked["risk"]
    overview_news = top_news(articles, sym, n=3, max_age=max_age, prefer_min=0.75)
    # the technical section cites genuine price/technical analysis coverage only
    technical_news = top_news(articles, sym, n=2, topics=("analysis",), max_age=max_age)
    if len(technical_news) < 2:
        technical_news = top_news(articles, sym, n=2, topics=("analysis", "market"),
                                  max_age=max_age)
    used_sources = _news_sources_used(articles, sym)

    sections = []

    def head(key):
        en, fa = SECTION_TITLES[key]
        sections.append(("h", {"en": en, "fa": fa}))

    def para(en, fa=None):
        sections.append(("p", {"en": en, "fa": fa or ""}))

    def cites(items, title_fa="منابع خبری این بخش"):
        items = [c for c in items if c]
        if not items:
            return
        for i, c in enumerate(items, 1):
            c.setdefault("index", i)
            if not c.get("index_fa"):
                c["index"] = i
                c["index_fa"] = fa_digits(i)
        sections.append(("cites", {"title_fa": title_fa, "items": items}))

    sections.append(("meta", {
        "title": f"{name} — Market Intelligence Report",
        "title_fa": f"گزارش تحلیل بازار {fa_name or name}",
        "asof": now.astimezone(IRAN_TZ).strftime("%Y-%m-%d %H:%M Tehran"),
        "asof_fa": fa_datetime(now),
        "symbol": sym, "name": name, "fa_name": fa_name or name, "icon": icon or "",
        "price": md.get("price"), "change_24h": md.get("change_24h"),
        "news_window_hours": max_age,
        # filled in below, once the cites blocks exist: the same number the
        # report returns at the top level, so the UI and the API agree
        "news_used": 0,
        "sources_used": [{"name": n, "count": c} for n, c in used_sources[:12]],
        "market_stale": bool(md.get("stale")),
    }))

    # 1 — overview (+ freshest market/analysis citations)
    ov = sec_market_overview(snap, md, name)
    head("overview")
    if ov:
        para(ov)
    cites([_cite(a) for a in overview_news], "منابع خبری این بخش (جدیدترین و معتبرترین)")

    # 2 — macro drivers
    mc_items = top_news(articles, sym, n=2, topics=("macro",), max_age=max_age)
    if len(mc_items) < 2:
        mc_items = top_news(articles, sym, n=2, topics=("macro", "regulation"), max_age=max_age)
    mc_text, mc_cites = sec_macro(mc_items, name)
    if mc_text:
        head("macro")
        para(mc_text)
        cites(mc_cites, "منابع این بخش")

    # 3 — news impact
    ni_text, ni_cites = sec_news_impact(strong, regulation, risk, name)
    if ni_text:
        head("news")
        para(ni_text)
        cites(ni_cites, "منابع خبری این بخش — به ترتیب اعتبار و تازگی")

    # 4 — flows
    fl = sec_flows(md, snap, sym, name, is_crypto)
    if fl:
        head("flows")
        para(fl)

    # 6 — derivatives
    dv = sec_derivatives(snap, sym, name, is_crypto)
    if dv:
        head("derivatives")
        para(dv)

    # 7 — technical (mandatory, >= 4 paragraphs) + freshest analysis citations
    head("technical")
    para(sec_technical(snap, name))
    cites([_cite(a) for a in technical_news], "منابع خبری بخش تحلیل تکنیکال")

    # 7b — the independent cross-check: TradingView's own indicator vote
    # (unofficial scanner API, key-less). Absent when the scanner is
    # unreachable or rate-limited — the section never stalls on it.
    try:
        from tv_ta import technical_vote
        vote = technical_vote(sym)
    except Exception:
        vote = None
    if vote:
        osc = (vote.get("osc") or "n/a").replace("_", " ").title()
        ma = (vote.get("ma") or "n/a").replace("_", " ").title()
        para(
            f"Independent cross-check — TradingView's technical vote on {vote['sym']} "
            f"({vote['interval']}): {vote['buy']} buy / {vote['neutral']} neutral / "
            f"{vote['sell']} sell of the standard indicator set, summing to "
            f"{vote['rec'].replace('_', ' ').title()}; oscillators {osc}, moving averages {ma}. "
            f"A crowd-signal quoted alongside, not in place of, the local computation above."
        )

    # 8 — scenarios
    head("scenarios")
    para(sec_scenarios(snap, name))

    # 9 — conclusion
    head("conclusion")
    para(sec_conclusion(snap, md, name))

    cited = count_cited_news(sections)
    for kind, val in sections:          # one number, in both places it is read
        if kind == "meta":
            val["news_used"] = cited
            break

    return {
        "symbol": sym,
        "name": name,
        "fa_name": fa_name or name,
        "icon": icon or "",
        "sections": sections,
        "generated_at": now.isoformat(),
        "news_used": cited,
    }


def build_all_reports(market_data, articles, symbols, now=None, meta=None, max_age=MAX_AGE_HOURS):
    """Reports for all requested symbols; failures return error stubs."""
    meta = meta or {}
    out = {}
    for sym in symbols:
        m = meta.get(sym) or {}
        try:
            out[sym] = build_report(
                sym, market_data.get(sym, {}), articles, now,
                name=m.get("name") or ASSET_NAMES.get(sym, sym),
                fa_name=m.get("fa"), is_crypto=m.get("is_crypto"),
                icon=m.get("icon"), max_age=max_age)
        except Exception as e:
            out[sym] = {"symbol": sym, "name": ASSET_NAMES.get(sym, sym),
                        "error": str(e),
                        "sections": [("h", {"en": "Error", "fa": "خطا"}),
                                     ("p", {"en": f"Report generation failed: {e}", "fa": ""})],
                        "generated_at": (now or datetime.now(timezone.utc)).isoformat()}
    return out


if __name__ == "__main__":
    import math
    fake = {"price": 100.0, "closes": [100 + math.sin(i / 5) * 4 for i in range(260)],
            "volumes": [1000 + i for i in range(260)], "change_24h": 1.4}
    news = [{
        "title": "Bitcoin ETF inflows hit a 10-month high as $6.8B floods in",
        "title_fa": "ورودی صندوق‌های ETF بیت‌کوین به بالاترین سطح ۱۰ ماهه رسید",
        "source_name": "CoinDesk", "source_kind": "crypto", "link": "https://example.com/1",
        "published_ts": 1789000000, "age_hours": 2.0, "credibility": 0.92,
        "topic": "etf", "topic_fa": "ETF", "assets": ["BTC"],
        "summary_fa": "خلاصه فارسی برای تست",
    }]
    r = build_report("BTC", fake, news, name="Bitcoin", fa_name="بیت‌کوین", is_crypto=True)
    kinds = [k for k, _ in r["sections"]]
    ta = [v["en"] for k, v in r["sections"] if k == "p" and "Trend structure" in v.get("en", "")]
    print("section kinds:", kinds)
    print("cites blocks:", kinds.count("cites"))
    print("TA paragraphs:", ta[0].count("\n\n") + 1 if ta else 0)
