"""Core regression tests — pure logic only, no network access.

Run:  .venv\\Scripts\\python -m pytest tests -q
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fa_format  # noqa: E402
import indicators  # noqa: E402
import sources  # noqa: E402
from report_generator import select_news  # noqa: E402


# ── Persian formatting ──────────────────────────────────────────────────────
@pytest.mark.parametrize("g,j", [
    ((2026, 9, 15), (1405, 6, 24)),
    ((2024, 3, 20), (1403, 1, 1)),
])
def test_jalali_conversion(g, j):
    assert fa_format.gregorian_to_jalali(*g) == j


def test_persian_digits_and_tehran_clock():
    assert fa_format.fa_digits("2026") == "۲۰۲۶"
    assert fa_format.to_tehran(0).utcoffset().total_seconds() == 3.5 * 3600


def test_fa_ago_wording():
    assert "دقیقه" in fa_format.fa_ago(0.5)
    assert "ساعت" in fa_format.fa_ago(5)
    assert "روز" in fa_format.fa_ago(50)


# ── indicators ──────────────────────────────────────────────────────────────
def test_sma_ema_edges():
    assert indicators.sma([1, 2, 3], 5) is None
    assert indicators.sma([1, 2, 3], 3) == 2
    assert indicators.ema([], 10) is None
    assert indicators.ema([float(i) for i in range(1, 60)], 20) > 30


def test_rsi_bounds_and_extremes():
    up = [float(i) for i in range(1, 40)]
    assert indicators.rsi_wilder(up) == 100.0
    down = [float(i) for i in range(40, 0, -1)]
    assert indicators.rsi_wilder(down) < 1.0
    assert indicators.rsi_wilder([1, 2, 3], 14) is None


def test_macd_and_bollinger_shapes():
    closes = [100 + (i % 7) for i in range(120)]
    m, s, h = indicators.macd(closes)
    assert m is not None and s is not None and h is not None
    up, mid, low = indicators.bollinger(closes, 20, 2.0)
    assert low < mid < up


def test_snapshot_is_grounded():
    closes = [100 + i * 0.5 for i in range(90)]
    snap = indicators.snapshot(closes, [10] * 90,
                               [c + 1 for c in closes], [c - 1 for c in closes])
    assert snap["spot"] == closes[-1]
    assert snap["atr14"] is None or snap["atr14"] >= 0
    assert isinstance(snap["rsi14"], float)


# ── credibility gate ────────────────────────────────────────────────────────
def test_relevance_and_noise_gate():
    assert sources.is_relevant(["BTC"], "Bitcoin ETF inflows hit a record")
    assert not sources.is_relevant([], "Company declares quarterly dividend")


def test_detect_assets_and_topic():
    assert "BTC" in sources.detect_assets("Bitcoin breaks $80k", "")
    assert sources.classify_topic("SEC sues exchange over tokens") == "regulation"
    assert sources.classify_topic("Hack drains protocol funds") == "security"


def test_custom_keyword_patterns():
    pats = sources.build_custom_patterns({"FOO": {"keywords": "foo - foocoin"}})
    assert "FOO" in pats and pats["FOO"].search("FOO jumps 5%")


def test_select_news_respects_credibility_and_age():
    arts = [
        {"assets": ["BTC"], "topic": "market", "credibility": 0.9,
         "age_hours": 2, "published_ts": 100.0, "title": "a"},
        {"assets": ["BTC"], "topic": "market", "credibility": 0.2,
         "age_hours": 2, "published_ts": 90.0, "title": "b"},
        {"assets": ["BTC"], "topic": "market", "credibility": 0.9,
         "age_hours": 99, "published_ts": 80.0, "title": "c"},
    ]
    picked = select_news(arts, "BTC", max_age=24)
    for bucket in picked.values():
        for a in bucket:
            assert a["credibility"] >= sources.REPORT_MIN_CREDIBILITY
            assert a["age_hours"] <= 24


# ── the delivered UI stays intact (guards the DL2 layers) ──────────────────
def test_dashboard_ships_dl2_layers():
    from dashboard_html import APP_HTML
    assert "DESIGN LANGUAGE 2.0" in APP_HTML
    assert 'id="tickerBar"' in APP_HTML and 'id="leadRow"' in APP_HTML
    assert APP_HTML.count('value="72" selected') == 0
    style = APP_HTML.split("<style>", 1)[1].split("</style>", 1)[0]
    assert style.count("{") == style.count("}")