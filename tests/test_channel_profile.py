"""Tests for the tgju.org/news editorial filter and board.

Defends the contracts for filtering foreign/international news for tgju.org/news:
1. International desks: Gold & Precious Metals, Global Macro & Oil, Forex, Crypto, Big Tech & AI.
2. Hard exclusions: Domestic Iranian market news (تومان، سکه امامی، بورس تهران، کارت ملی...),
   phishing scams, and off-topic gossip.
3. Big Tech & AI coverage: Nvidia, Apple, Microsoft, OpenAI, AI infrastructure are recognized.
4. Viral trends: Surges, viral momentum, and meme coins are covered rather than rejected.
5. Explainable scoring & deterministic deduplication.
"""

import time
import pytest
import channel_profile as cp

NOW = 1_700_000_000.0


def art(title, summary="", credibility=0.85, age_h=1.0, **extra):
    a = {
        "id": extra.pop("id", title[:12]),
        "title_fa": title,
        "summary_fa": summary,
        "title": "",
        "summary": "",
        "credibility": credibility,
        "published_ts": NOW - age_h * 3600,
        "source_name": "Reuters",
        "source_kind": "news",
    }
    a.update(extra)
    return a


# ───────────────────────────── 1 · matching ─────────────────────────────

def test_persian_stem_does_not_fire_inside_a_longer_word():
    assert cp._hit(cp.normalize("قیمت بزرگ بازار"), "زر") is False
    assert cp._hit(cp.normalize("بازار زرین"), "زر") is True
    assert cp._hit(cp.normalize("هر اونس طلا و زر"), "زر") is True


def test_persian_stem_still_matches_its_own_inflections():
    assert cp._hit(cp.normalize("شاخص دلارهای آمریکا"), "دلار") is True


def test_latin_stem_does_not_fire_inside_a_longer_word():
    assert cp._hit(cp.normalize("the bitcoin rally"), "coin") is False
    assert cp._hit(cp.normalize("prices boiled over"), "oil") is False
    assert cp._hit(cp.normalize("a gold bullion bar"), "bullion") is True


def test_normalize_folds_arabic_letters_and_digits():
    assert cp.normalize("اونس طلاي جهاني") == cp.normalize("اونس طلای جهانی")


def test_normalize_does_not_swallow_arabic_indic_digits():
    assert "12" in cp.normalize("قیمت ١٢ دلار")
    assert cp.normalize("١٢") == "12"


# ───────────────────────────── 2 · desks / buckets ─────────────────────────────

def test_gold_desk_matches_global_gold():
    b = cp.detect_buckets(art("اونس طلا در بازارهای جهانی به سقف تاریخی رسید", "قیمت نقره نیز افزایش یافت."))
    assert "gold" in b
    assert any("طلا" in w or "اونس" in w for w in b["gold"])


def test_global_macro_matches_fed_and_rates():
    b = cp.detect_buckets(art("فدرال رزرو نرخ بهره را کاهش داد", "شاخص اس اند پی و وال استریت صعودی شدند."))
    assert "global" in b


def test_currency_matches_forex():
    b = cp.detect_buckets(art("شاخص دلار در برابر یورو و ین ژاپن تقویت شد"))
    assert "currency" in b


def test_crypto_matches_digital_assets():
    b = cp.detect_buckets(art("بیت‌کوین از سقف تاریخی عبور کرد", "اتریوم و سولانا نیز رالی صعودی آغاز کردند."))
    assert "crypto" in b


def test_tech_matches_big_tech_and_ai():
    b = cp.detect_buckets(art("سهام انویدیا به رکورد جدیدی در وال استریت دست یافت", "رونق هوش مصنوعی و تقاضای تراشه."))
    assert "tech" in b


# ───────────────────── 3 · off-profile hard exclusions ─────────────────────

@pytest.mark.parametrize("title,summary", [
    ("قیمت سکه بهار آزادی و سکه امامی در بازار تهران اعلام شد", ""),
    ("طلای ۱۸ عیار امروز به ۱۲ میلیون تومان رسید", ""),
    ("نرخ ارز نیمایی و سامانه سنا اعلام شد", ""),
    ("ثبت‌نام خودرو داخلی با کارت ملی آغاز شد", ""),
    ("شاخص کل بورس تهران ۱۰ هزار واحد افت کرد", ""),
])
def test_domestic_iranian_news_is_hard_excluded(title, summary):
    """Domestic news is authored elsewhere by TGJU's domestic desk."""
    res = cp.score_article(art(title, summary), now=NOW)
    assert res["publishable"] is False
    assert res["fit"] == 0.0
    assert "domestic" in res["off_profile"]


def test_scams_are_hard_excluded():
    res = cp.score_article(art("airdrop claim free giveaway", "claim your tokens with seed phrase"), now=NOW)
    assert res["publishable"] is False
    assert "scam" in res["off_profile"]


def test_viral_memecoins_are_allowed_for_tgju():
    """Viral trends (DOGE, PEPE, meme rally) are permitted as engagement stories."""
    res = cp.score_article(art("جهش ۵۰ درصدی دوج کوین پس از اظهارات جدید", "رالی صعودی در بازار ارزهای دیجیتال."), now=NOW)
    assert res["publishable"] is True
    assert "crypto" in res["buckets"]


# ───────────────────────────── 4 · gates and ranking ─────────────────────────────

def test_credibility_is_a_gate_not_a_weight():
    low = cp.score_article(art("قیمت اونس طلا در بازار جهانی", credibility=0.3), now=NOW)
    assert low["publishable"] is False
    assert low["fit"] == 0.0


def test_a_story_with_no_desk_is_rejected_with_readable_reason():
    res = cp.score_article(art("قهرمانی تیم بسکتبال در مسابقات جهانی", "گزارش بازی نهایی."), now=NOW)
    assert res["publishable"] is False
    assert "هدف" in res["reason"] or "خارج" in res["reason"]


def test_market_impact_boosts_editorial_fit():
    impact = cp.score_article(art("فدرال رزرو نرخ بهره را ۰.۵ درصد کاهش داد",
                                  "تصمیم مهم کمیته فدرال رزرو بر بازارهای جهانی اثر گذاشت."), now=NOW)
    bland = cp.score_article(art("جلسه مدیران اقتصادی برگزار شد", "گفت‌وگو درباره همکاری‌ها."), now=NOW)
    assert impact["fit"] > bland["fit"]


def test_freshness_decays_monotonically():
    scores = [cp.score_article(art("قیمت اونس طلا در بازار جهانی", age_h=h), now=NOW)["factors"]["freshness"]
              for h in (0, 4, 12, 24, 48)]
    assert scores == sorted(scores, reverse=True)


def test_social_sources_are_penalised():
    social = cp.score_article(art("اونس طلا در بازارهای جهانی", source_kind="social"), now=NOW)
    wire = cp.score_article(art("اونس طلا در بازارهای جهانی", source_kind="news"), now=NOW)
    assert social["fit"] < wire["fit"]
    assert "منبع شبکه اجتماعی" in social["reason"]


# ───────────────────────────── 5 · caption honesty ─────────────────────────────

def test_caption_numbers_come_from_the_article():
    a = art("قیمت اونس طلا به ۲۷۰۰ دلار رسید", "نقره نیز با ۳ درصد رشد به ۳۲ دلار رسید.")
    item = cp.rank_for_channel([a], now=NOW)["items"][0]
    haystack = cp.normalize(a["title_fa"] + " " + a["summary_fa"])
    for n in item["caption"]["numbers"]:
        assert n in haystack


def test_caption_carries_the_lane_badge_and_tgju_branding():
    a = art("بیت‌کوین از مرز ۹۵۰۰۰ دلار عبور کرد", "ثبت سقف تاریخی جدید در بازار رمزارزها.")
    item = cp.rank_for_channel([a], now=NOW)["items"][0]
    cap = item["caption"]
    assert cap["badge"] == cp.BUCKETS[item["primary_bucket"]]["badge"]
    assert "TGJU" in cap["text"]


# ───────────────────────────── 6 · the board ─────────────────────────────

def test_board_dedupes_the_same_story_from_two_outlets():
    same = "اونس طلا به سقف تاریخی ۲۷۰۰ دلار رسید"
    board = cp.rank_for_channel(
        [art(same, id="a", source_name="Reuters"),
         art(same, id="b", source_name="Bloomberg")], now=NOW)
    assert len(board["items"]) == 1
    assert board["rejected"]["duplicate"] == 1


def test_board_counts_each_rejection_reason():
    board = cp.rank_for_channel([
        art("اونس طلا در بازار جهانی صعودی شد", id="keep"),
        art("قیمت سکه بهار آزادی در بازار تهران", id="domestic"),
        art("اونس طلا در بازار جهانی صعودی شد", id="weak", credibility=0.2),
    ], now=NOW)
    assert board["rejected"]["off_profile"] == 1
    assert board["rejected"]["low_credibility"] == 1
    assert [i["id"] for i in board["items"]] == ["keep"]


def test_board_exposes_the_lane_breakdown_the_ui_renders():
    board = cp.rank_for_channel([
        art("اونس طلا در بازار جهانی ۲۷۰۰ دلار شد", id="g"),
        art("سهام انویدیا و هوش مصنوعی رکورد زد", id="t"),
        art("بیت‌کوین به ۹۰۰۰۰ دلار رسید", id="c"),
    ], now=NOW)
    assert board["lanes"]
    assert sum(board["lanes"].values()) == len(board["items"])


def test_board_returns_an_empty_result_rather_than_raising_on_junk():
    board = cp.rank_for_channel([{}, {"title_fa": None}, None], now=NOW)
    assert board["items"] == []
    assert board["scanned"] == 0


def test_undated_articles_are_neither_rewarded_nor_buried():
    undated = cp.score_article(
        {"title_fa": "اونس طلا در بازار جهانی", "credibility": 0.85, "published_ts": 0}, now=NOW)
    assert undated["publishable"] is True
    assert 0.0 < undated["fit"] <= 100.0


# ───────────────────────── 7 · slicing ─────────────────────────

def test_a_small_request_cannot_shrink_the_board_for_the_next_caller():
    arts = [art(t, id="a%d" % i) for i, t in enumerate([
        "اونس طلا در بازار جهانی رکورد زد",
        "فدرال رزرو نرخ بهره را کاهش داد",
        "سهام انویدیا به بالاترین سطح رسید",
        "بیت‌کوین از ۹۰۰۰۰ دلار عبور کرد",
        "شاخص دلار در بازارهای جهانی افت کرد",
        "قیمت نفت برنت در بازار جهانی افزایش یافت",
    ])]
    board = cp.rank_for_channel(arts, now=NOW, limit=6)
    assert len(board["items"]) == 6
    assert len(cp.slice_board(board, 3)["items"]) == 3
    assert len(cp.slice_board(board, 6)["items"]) == 6


def test_slicing_is_a_prefix_and_keeps_the_lane_counts_in_step():
    arts = [art("اونس طلا در بازارهای جهانی صعود کرد", id="gold"),
            art("سهام انویدیا و تراشه‌های هوش مصنوعی جهش کردند", id="tech"),
            art("شاخص دلار در برابر یورو افت کرد", id="fx")]
    board = cp.rank_for_channel(arts, now=NOW, limit=3)
    small = cp.slice_board(board, 2)
    assert [i["id"] for i in small["items"]] == [i["id"] for i in board["items"]][:2]
    assert sum(small["lanes"].values()) == len(small["items"])
    assert len(board["items"]) == 3


# ─────────────────────── 8 · the client contract ───────────────────────

def _client_js():
    import pathlib
    return (pathlib.Path(__file__).resolve().parent.parent /
            "web" / "channel.js").read_text(encoding="utf-8")


def test_client_escape_helper_does_not_shadow_the_global_one():
    import re
    js = _client_js()
    assert "escFallback" in js
    assert not re.search(r"typeof esc\s*===?\s*'function'", js)


def test_client_is_wired_into_the_dashboard():
    from dashboard_html import APP_HTML
    for needle in ('id="nav-channel"', 'id="view-channel"', 'id="cbList"', '/channel.js'):
        assert needle in APP_HTML, f"{needle} is missing from the dashboard"


# ─────────────────────── 9 · virality engine ───────────────────────

def _art(**kw):
    base = {"id": "t1", "title": "gold market rally", "title_fa": "رالی صعودی طلا در بازار جهانی",
            "summary": "", "summary_fa": "", "assets": ["XAU"], "credibility": 0.9,
            "published_ts": NOW - 3600, "source_kind": "wire"}
    base.update(kw)
    return base


def test_shock_scales_with_market_volatility():
    mkt = {"XAU": {"price": 2750.0, "change_24h": 3.5,
                   "spark": [2650, 2660, 2670, 2680, 2700, 2720, 2740, 2750]}}
    v = cp.viral_score(_art(), market=mkt, now=NOW)
    assert v["viral_factors"]["shock"] > 0.40
    assert "XAU" in v["viral_why"][0]


def test_ai_only_and_limit_150():
    sample = [
        art("صعود اونس طلا در بازار جهانی", id="gold_1"),
        art("سهام انویدیا و تراشه‌های هوش مصنوعی رکورد زد", id="ai_1"),
        art("اوپن ای آی مدل جدید هوش مصنوعی را معرفی کرد", id="ai_2"),
        art("بیت‌کوین به بالاترین سطح رسید", id="crypto_1"),
        art("دیپ‌سیک مدل استدلال جدید منتشر کرد", id="ai_3"),
    ]
    board = cp.rank_for_channel(sample, now=NOW, limit=150, ai_only=True)
    assert len(board["items"]) == 3
    assert all("tech" in i["buckets"] for i in board["items"])
    assert {i["id"] for i in board["items"]} == {"ai_1", "ai_2", "ai_3"}

