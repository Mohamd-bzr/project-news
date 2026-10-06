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
import reddit_scores  # noqa: E402
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


# ── the delivered UI stays intact (guards the DL3 "Engraved Instrument" layer) ──
def test_dashboard_ships_dl3_layers():
    from dashboard_html import APP_HTML
    assert "DESIGN LANGUAGE 3" in APP_HTML and "ENGRAVED INSTRUMENT" in APP_HTML
    assert 'id="tickerBar"' in APP_HTML and 'id="leadRow"' in APP_HTML
    assert APP_HTML.count('value="72" selected') == 0
    style = APP_HTML.split("<style>", 1)[1].split("</style>", 1)[0]
    assert style.count("{") == style.count("}")
    # one deliberate token system: a single :root, no token defined twice
    assert style.count(":root") == 1
    for tok in ("--bg:", "--cu:", "--ink-3:", "--r3:"):
        assert style.count(tok) == 1, f"{tok} must be declared exactly once"


# ── full-text extraction: the two passes that read the page's own JSON ──────
_BODY_LONG = (
    "The market resolves based on a simple average of the index for the sixty seconds prior "
    "to the specified time. Prices must meet the criterion at exactly the specified time on "
    "the target date. If no data is available or incomplete at the expiration time, affected "
    "strikes resolve to No. You get one dollar for every contract you own when your prediction "
    "is correct, or you can close your position before the event resolves. Additional fees may "
    "apply, and the full contract terms are published alongside this market. "
) * 2


def test_jsonld_body_survives_the_script_strip():
    """The JSON-LD pass used to run *after* <script> was decomposed, so it could
    never see a node — and the last-resort <p> sweep then wiped what was left."""
    import app
    html = ("<html><head>"
            "<script type=\"application/ld+json\">"
            '{"@type": "NewsArticle", "articleBody": "' + _BODY_LONG + '"}'
            "</script></head><body><p>tiny</p></body></html>")
    res = app._parse_article_html(html, "https://example.com/a", "Example")
    assert res["word_count"] >= 100
    assert any("simple average" in p for p in res["paragraphs"])


def test_next_payload_body_is_extracted():
    """An SPA shell ships the article inside __NEXT_DATA__; the ladder must read
    it instead of falling back to the one-line meta description."""
    import json
    import app
    payload = json.dumps({"props": {"pageProps": {"event": {
        "longDescription": _BODY_LONG, "description": "XRP price at Sep 27"}}}})
    html = ('<html><head><script id="__NEXT_DATA__" type="application/json">'
            + payload + "</script></head><body><p>tiny</p></body></html>")
    res = app._parse_article_html(html, "https://app.example.com/e/x", "Example")
    assert res["word_count"] >= 100
    # the short `description` field is a label, not the body
    assert "XRP price" not in " ".join(res["paragraphs"])


def test_paragraph_filter_rejects_bare_media_urls():
    """reddit image posts carry a preview URL as their only 'text'."""
    import app
    url = ("https://preview.redd.it/on7exaw90sh1.png?width=1152&format=png"
           "&auto=webp&s=7d733ec9f1cbccdcf9befb2e3278be068e")
    assert not app._looks_like_paragraph(url)





# ── social popularity gate (min upvotes) ────────────────────────────────
@pytest.fixture(autouse=True)
def _isolate_score_cache(monkeypatch):
    """Tests must never see (or write) the real score cache, nor touch the
    network — fake ids must not be resolved against the live archive."""
    monkeypatch.setattr(reddit_scores, "_loaded", True)
    monkeypatch.setattr(reddit_scores, "_cache", {})
    monkeypatch.setattr(reddit_scores, "fetch_scores", lambda ids: {})
    monkeypatch.setattr(reddit_scores, "_save_cache", lambda: None)
    yield


def _mk_social(rid, score=None, comments=None):
    a = {"id": f"x_{rid}", "title": f"post {rid}", "summary": "body",
         "link": f"https://www.reddit.com/r/defi/comments/{rid}/slug/",
         "source_kind": "social", "published_ts": 1}
    if score is not None:
        a["reddit_score"] = score
    if comments is not None:
        a["reddit_comments"] = comments
    return a


def test_reddit_id_extraction():
    assert reddit_scores._extract_id(
        "https://www.reddit.com/r/defi/comments/1wrn4lw/slug/") == "1wrn4lw"
    assert reddit_scores._extract_id("https://example.com/x") is None


def test_social_gate_drops_below_min_score():
    arts = [_mk_social("aaaaaa", score=1999),
            _mk_social("bbbbbb", score=2000),
            _mk_social("cccccc"),              # unresolved -> dropped (fail-closed)
            _mk_social("dddddd", score=50, comments=7)]
    kept, dropped = reddit_scores.attach_scores(arts, min_score=2000)
    assert dropped == 3
    ids = [a["id"] for a in kept]
    assert "x_aaaaaa" not in ids and "x_dddddd" not in ids
    assert "x_cccccc" not in ids
    assert "x_bbbbbb" in ids


def test_social_gate_off_or_scoreless():
    arts = [_mk_social("eeeeee", score=1), _mk_social("ffffff")]
    kept, dropped = reddit_scores.attach_scores(arts, min_score=0)
    assert dropped == 0 and len(kept) == 2      # gate off -> everything passes


def test_social_gate_min_comments():
    arts = [_mk_social("gggggg", score=99999, comments=2),
            _mk_social("hhhhhh", score=3000, comments=25)]
    kept, dropped = reddit_scores.attach_scores(
        arts, min_score=2000, min_comments=10)
    assert dropped == 1 and kept[0]["id"] == "x_hhhhhh"


# ── Phase 8: PWA & Mobile ───────────────────────────────────────────────────
def test_pwa_and_manifest():
    import json
    from app import app
    from dashboard_html import APP_HTML

    # ONE manifest. There used to be two: a root manifest.json branded
    # "FreeBuff" linking /static/icons (the one the page actually used) and
    # web/manifest.webmanifest branded "MOHMD NEWS" (linked nowhere), plus a
    # duplicated icon set. The page, the install metadata and the service worker
    # now all agree on the real one.
    manifest_file = ROOT / "web" / "manifest.webmanifest"
    assert manifest_file.exists()
    m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert m_data["name"] == "MOHMD NEWS — Market Intelligence Terminal"
    assert m_data["display"] == "standalone"
    assert m_data["lang"] == "fa" and m_data["dir"] == "rtl"
    assert len(m_data["icons"]) >= 2
    assert any(i.get("purpose") == "maskable" for i in m_data["icons"])
    assert not (ROOT / "manifest.json").exists(), "the duplicate manifest is back"

    client = app.test_client()
    resp_m = client.get("/manifest.webmanifest")
    assert resp_m.status_code == 200
    assert resp_m.get_json()["short_name"] == "MOHMD NEWS"
    # the old URL still resolves, it just points at the one real manifest
    legacy = client.get("/manifest.json")
    assert legacy.status_code == 301
    assert legacy.headers["Location"].endswith("/manifest.webmanifest")

    sw_file = ROOT / "static" / "sw.js"
    assert sw_file.exists()
    assert client.get("/sw.js").status_code == 200

    icon_192 = ROOT / "web" / "icons" / "icon-192.png"
    icon_512 = ROOT / "web" / "icons" / "icon-512.png"
    assert icon_192.exists() and icon_512.exists()
    assert client.get("/icons/icon-192.png").status_code == 200

    assert '<link rel="manifest" href="/manifest.webmanifest">' in APP_HTML
    assert "@media (max-width: 768px)" in APP_HTML
    assert "navigator.serviceWorker.register('/sw.js'" in APP_HTML
    assert "navigator.serviceWorker.register('/static/sw.js')" not in APP_HTML


# ── Phase 9: REST API & OpenAPI Docs ─────────────────────────────────────────
def test_v1_api_and_docs():
    import os
    from app import app, _default_key, _generate_api_key, _hash_api_key, _api_keys

    client = app.test_client()

    # 1. OpenAPI Docs
    docs_resp = client.get("/api/docs")
    assert docs_resp.status_code == 200
    assert "swagger-ui" in docs_resp.data.decode()

    # 2. Public Health Check
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.get_json()["status"] == "ok"

    # 3. Unauthorized access
    unauth_resp = client.get("/api/v1/articles")
    assert unauth_resp.status_code == 401
    assert "API key required" in unauth_resp.get_json().get("error", "")

    # 4. Authorized access with header
    auth_resp = client.get("/api/v1/assets", headers={"X-API-Key": _default_key})
    assert auth_resp.status_code == 200
    assert auth_resp.get_json()["ok"] is True
    assert len(auth_resp.get_json()["assets"]) > 0

    # 5. Authorized access with query param
    query_resp = client.get(f"/api/v1/sentiment?api_key={_default_key}")
    assert query_resp.status_code == 200
    assert query_resp.get_json()["ok"] is True

    # 6. Calendar endpoint
    cal_resp = client.get("/api/v1/calendar", headers={"X-API-Key": _default_key})
    assert cal_resp.status_code == 200
    assert cal_resp.get_json()["ok"] is True

    # 7. Rate limiting
    test_key = _generate_api_key()
    test_hash = _hash_api_key(test_key)
    _api_keys[test_hash]["rate_limit"] = 1

    r1 = client.get("/api/v1/assets", headers={"X-API-Key": test_key})
    assert r1.status_code == 200
    r2 = client.get("/api/v1/assets", headers={"X-API-Key": test_key})
    assert r2.status_code == 429
    assert "Rate limit exceeded" in r2.get_json().get("error", "")

    # 8. Admin keys management
    # The token is restored afterwards on purpose: it used to be set here and
    # never cleared, so every test that ran later in the session was quietly
    # executed behind the shared-secret gate (test_stream_manager.py even had
    # to monkeypatch it away by hand).
    _prev_token = os.environ.get("MOHMD_TOKEN")
    os.environ["MOHMD_TOKEN"] = "test_admin_token"
    try:
        admin_unauth = client.get("/api/admin/keys")
        assert admin_unauth.status_code == 403

        admin_post = client.post(
            "/api/admin/keys",
            headers={"Authorization": "Bearer test_admin_token"},
            json={"name": "new_service", "rate_limit": 250},
        )
        assert admin_post.status_code == 200
        created_key = admin_post.get_json()["key"]
        assert created_key.startswith("fb_")

        admin_get = client.get(
            "/api/admin/keys",
            headers={"Authorization": "Bearer test_admin_token"},
        )
        assert admin_get.status_code == 200
        assert any(k["name"] == "new_service" for k in admin_get.get_json()["keys"])
    finally:
        if _prev_token is None:
            os.environ.pop("MOHMD_TOKEN", None)
        else:
            os.environ["MOHMD_TOKEN"] = _prev_token


# ── Phase 10: Integrations ───────────────────────────────────────────────────
def test_phase10_integrations():
    from integrations.discord_bot import DiscordBot
    from integrations.email_digest import build_digest_html
    from integrations.tv_webhook import process_webhook, get_recent_alerts, get_alerts_for_ticker
    from app import app, CONFIG

    # 1. Discord Bot initialization and payload building
    bot = DiscordBot(webhook_url="https://example.com/webhook")
    assert bot.webhook_url == "https://example.com/webhook"
    # test methods return bool without raising
    res_alert = bot.send_anomaly_alert([])
    assert res_alert is True

    # 2. Email Digest HTML Builder
    reports = {"BTC": {"sections": [("Technical", {"summary": "BTC looking strong", "trend": "صعودی"})]}}
    articles = [{"title": "Bitcoin reaches milestone", "link": "https://example.com/1", "sentiment_score": 0.8, "sentiment_label": "positive", "source_name": "CoinDesk"}]
    sentiment = {"BTC": {"avg_score": 0.5, "total": 12}}
    html = build_digest_html(reports, articles, sentiment)
    assert "<table" in html
    assert "FreeBuff Weekly Digest" in html
    assert "BTC" in html

    # 3. TradingView Webhook Processor
    bad_res = process_webhook({"secret": "wrong", "ticker": "ETH"}, "correct_secret")
    assert bad_res["ok"] is False
    assert bad_res["error"] == "invalid secret"

    ok_res = process_webhook({
        "secret": "correct_secret",
        "strategy": "TrendFollow",
        "ticker": "ETHUSDT",
        "action": "buy",
        "price": 3500.0,
        "message": "Breakout confirmed",
    }, "correct_secret")
    assert ok_res["ok"] is True
    assert "alert_id" in ok_res

    recent = get_recent_alerts(limit=5)
    assert len(recent) > 0
    eth_alerts = get_alerts_for_ticker("ETHUSDT")
    assert len(eth_alerts) > 0

    # 4. Flask endpoints
    client = app.test_client()
    tv_sec = CONFIG.get("tv_webhook_secret", "change-me-to-a-random-string")

    r_bad = client.post("/webhook/tv", json={"secret": "wrong_secret"})
    assert r_bad.status_code == 400
    assert r_bad.get_json()["ok"] is False

    r_ok = client.post("/webhook/tv", json={
        "secret": tv_sec,
        "ticker": "BTCUSDT",
        "action": "sell",
        "price": 60000,
        "message": "Take profit",
    })
    assert r_ok.status_code == 200
    assert r_ok.get_json()["ok"] is True

    r_alerts = client.get("/api/alerts?ticker=BTCUSDT")
    assert r_alerts.status_code == 200
    assert len(r_alerts.get_json()["alerts"]) > 0


def test_phase11_ai_features():
    from ai_features import VolumeAnomalyDetector, SentimentPredictor, get_all_predictions, get_ai_summary
    from app import app, STATE

    # 1. VolumeAnomalyDetector
    detector = VolumeAnomalyDetector(window=10, threshold=2.0)
    for _ in range(15):
        detector.record([{"symbols": ["SOL"]} for _ in range(2)])
    detector.record([{"symbols": ["SOL"]} for _ in range(12)])
    anomalies = detector.detect()
    assert len(anomalies) > 0
    assert anomalies[0]["symbol"] == "SOL"
    assert anomalies[0]["current_count"] == 12
    assert anomalies[0]["z_score"] >= 2.0

    # 2. SentimentPredictor
    predictor = SentimentPredictor()
    # Less than 10 points
    assert predictor.predict("BTC")["confidence"] == 0.0

    # 15 bullish points
    for i in range(15):
        predictor.record("BTC", 0.1 * i)
    pred_btc = predictor.predict("BTC")
    assert pred_btc["prediction"] == "bullish"
    assert pred_btc["confidence"] > 0

    # 3. get_all_predictions
    articles = [
        {"title": "BTC rises", "symbols": ["BTC"], "sentiment_score": 0.8},
        {"title": "ETH merges", "assets": ["ETH"], "sentiment_score": 0.5},
    ]
    all_preds = get_all_predictions(articles)
    assert "BTC" in all_preds
    assert "ETH" in all_preds

    # 4. Endpoints
    client = app.test_client()

    # Predictions are gated by require_tier('ai_predictions') in Phase 12
    r_pred_gated = client.get("/api/ai/predictions")
    assert r_pred_gated.status_code == 403

    from billing import register_user
    register_user("ai_test@freebuff.com", "fb_pro_ai_test_key", tier="pro")
    pro_hdr = {"X-API-Key": "fb_pro_ai_test_key"}

    r_pred = client.get("/api/ai/predictions", headers=pro_hdr)
    assert r_pred.status_code == 200
    assert r_pred.get_json()["ok"] is True

    r_anom = client.get("/api/ai/anomalies")
    assert r_anom.status_code == 200
    assert r_anom.get_json()["ok"] is True

    # Summary 404 when missing
    r_sum_none = client.get("/api/ai/summary/UNKNOWN")
    assert r_sum_none.status_code == 404

    # Summary 200 when populated
    STATE["ai_summaries"]["BTC"] = {
        "summary": "BTC shows strong accumulation momentum.",
        "key_points": ["Inflows high", "Resistance broken"],
        "sentiment": "bullish"
    }
    r_sum_ok = client.get("/api/ai/summary/BTC")
    assert r_sum_ok.status_code == 200
    assert r_sum_ok.get_json()["ok"] is True
    assert "BTC shows strong accumulation" in r_sum_ok.get_json()["summary"]


def test_phase12_freemium_and_billing():
    from billing import init_tier_db, register_user, get_user_tier, check_feature, track_usage, TIERS
    from app import app, CANDLES_CACHE

    init_tier_db()

    # 1. User registration & tier checks
    reg_free = register_user("free_user@example.com", "fb_free_key_1", tier="free")
    assert reg_free["ok"] is True
    assert reg_free["tier"] == "free"

    reg_pro = register_user("pro_user@example.com", "fb_pro_key_1", tier="pro")
    assert reg_pro["ok"] is True
    assert reg_pro["tier"] == "pro"

    # 2. Tier data & feature permissions
    t_free = get_user_tier("fb_free_key_1")
    assert t_free["tier"] == "free"
    assert t_free["api_limit"] == 100
    assert t_free["alerts_limit"] == 3

    t_pro = get_user_tier("fb_pro_key_1")
    assert t_pro["tier"] == "pro"
    assert t_pro["api_limit"] == 1000
    assert t_pro["alerts_limit"] == 999

    assert check_feature("fb_free_key_1", "dashboard") is True
    assert check_feature("fb_free_key_1", "ai_predictions") is False
    assert check_feature("fb_pro_key_1", "ai_predictions") is True

    # 3. Usage tracking
    track_usage("fb_free_key_1", "export")
    track_usage("fb_free_key_1", "export")

    client = app.test_client()

    # 4. Billing API Endpoints
    # GET /api/billing/tier
    r_tier_anon = client.get("/api/billing/tier")
    assert r_tier_anon.status_code == 200
    assert r_tier_anon.get_json()["tier"] == "free"

    r_tier_pro = client.get("/api/billing/tier", headers={"X-API-Key": "fb_pro_key_1"})
    assert r_tier_pro.status_code == 200
    assert r_tier_pro.get_json()["tier"] == "pro"

    # POST /api/billing/upgrade
    r_up_err = client.post("/api/billing/upgrade", json={})
    assert r_up_err.status_code == 400

    r_up_ok = client.post("/api/billing/upgrade", json={"email": "new_subscriber@example.com"})
    assert r_up_ok.status_code == 200
    up_data = r_up_ok.get_json()
    assert up_data["ok"] is True
    assert up_data["tier"] == "pro"
    assert "fb_pro_" in up_data["api_key"]

    new_pro_key = up_data["api_key"]

    # GET /api/billing/usage
    r_usage = client.get("/api/billing/usage", headers={"X-API-Key": "fb_free_key_1"})
    assert r_usage.status_code == 200
    usage_data = r_usage.get_json()
    assert usage_data["ok"] is True
    assert usage_data["usage"].get("export", 0) >= 2

    # 5. (RAG QA endpoint /api/ai/ask was never shipped — its test removed)

    # 6. Endpoint feature gating: Chart timeframes
    CANDLES_CACHE["BTC_1D"] = {"data": [{"time": 100, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10}]}
    CANDLES_CACHE["BTC_1H"] = {"data": [{"time": 100, "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10}]}

    # 1D is free
    r_c_free = client.get("/api/candles/BTC?tf=1D")
    assert r_c_free.status_code == 200

    # 1H is advanced and gated for free
    r_c_gated = client.get("/api/candles/BTC?tf=1H")
    assert r_c_gated.status_code == 403

    # 1H is allowed for Pro
    r_c_pro = client.get("/api/candles/BTC?tf=1H", headers={"X-API-Key": new_pro_key})
    assert r_c_pro.status_code == 200






# ── iran_market (TGJU domestic quotes) ──────────────────────────────────────

def test_iran_market_parses_tgju_rows(monkeypatch):
    import iran_market
    iran_market._CACHE["ts"], iran_market._CACHE["data"] = 0.0, None

    class _R:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"current": {
                "price_dollar_rl": {"p": "2,695,000", "dp": "0.45"},
                "geram18":         {"p": "265,125,000", "dp": "0.70"},
                "sekee":           {"p": "2,712,250,000", "dp": "-0.06"},
                "ons":             {"p": "4,144.74", "dp": "0.11"},
                "tether":          {"p": "271,300", "dp": "0.02"},
            }}
    monkeypatch.setattr(iran_market.requests, "get", lambda *a, **k: _R())
    snap = iran_market.snapshot(force=True)
    assert snap["ok"] is True
    by_key = {i["key"]: i for i in snap["items"]}
    # rial -> toman
    assert by_key["dollar"]["price"] == 269500.0
    assert by_key["gold18"]["price"] == 26512500.0
    assert by_key["coin_emami"]["change_pct"] == -0.06
    # the ounce stays in dollars
    assert by_key["gold_ounce"]["unit"] == "dollar"
    assert by_key["gold_ounce"]["price"] == 4144.74


def test_iran_market_serves_stale_on_failure(monkeypatch):
    import time
    import iran_market
    # a good snapshot in the cache, then a dead network
    iran_market._CACHE["ts"] = time.time()          # fresh ts, but force=1 re-fetches
    iran_market._CACHE["data"] = {"ok": True, "items": [{"key": "dollar", "label": "دلار",
                                                        "price": 269500.0, "change_pct": 0.45,
                                                        "unit": "toman", "stale": False}],
                                  "ts": time.time(), "source": "tgju"}
    def _boom(*a, **k): raise IOError("network down")
    monkeypatch.setattr(iran_market.requests, "get", _boom)
    snap = iran_market.snapshot(force=True)
    assert snap["ok"] is True
    assert snap["items"][0]["stale"] is True


# ── card_render (Persian news-card PNG) ─────────────────────────────────────

def test_card_render_produces_a_real_png():
    """The studio's image card: shaped, RTL, DL6 palette — from the article's own fields."""
    from card_render import render_news_card
    png = render_news_card({
        "title_fa": "سقف تاریخی جدید طلا؛ اونس به ۴۱۶۰ دلار رسید",
        "summary_fa": "بازار تهران واکنش نشان داد؛ دلار آزاد هم بالا رفت.",
        "source_name": "Bloomberg", "datetime_fa": "۲۶ مهر ۱۴۰۵ · ۱۷:۳۵",
        "numbers": ["۴۱۶۰ دلار", "۳.۲٪"],
    })
    png_sig = bytes([0x89]) + b"PNG" + bytes([0x0D, 0x0A, 0x1A, 0x0A])
    assert png[:8] == png_sig
    assert 40_000 < len(png) < 500_000


def test_card_render_rejects_empty_title():
    from card_render import render_news_card, CardUnavailable
    with pytest.raises(CardUnavailable):
        render_news_card({"title": "", "summary": "x"})
