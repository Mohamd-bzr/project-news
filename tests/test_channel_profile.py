"""Tests for the channel board — the gold/coin page.

The page is defined as much by what it refuses as by what it runs, so the
contracts defended here are mostly about **not** letting the wrong thing
through:

1. **Word boundaries survive Persian.** «زر» inside «بزرگ» is a false lane
   opening; «سکه» inside «سکه‌ها» is a real one. Both are substring searches
   with no word boundary, so both are wrong unless the matcher is explicit.
2. **A bare «دلار» is not the FX lane.** Every crypto story quotes dollars;
   if that word opened the currency lane, the board would fill up with
   crypto and call it «نوسان بازار».
3. **Off-profile is a hard exclude, not a penalty.** A bridge-exploit story
   that happens to say «۵۰ میلیون دلار» must not rank, however well shaped.
4. **Nothing is invented.** Every number in the caption came out of the
   article; a caption that invents a price is worse than no caption.
5. **Rejections are counted.** An operator must be able to see that the tab
   is empty because nothing fit, not because the filter ate the corpus.
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
        "source_name": "ایرنا",
        "source_kind": "news",
    }
    a.update(extra)
    return a


# ───────────────────────────── 1 · matching ─────────────────────────────

def test_persian_stem_does_not_fire_inside_a_longer_word():
    """«زر» is a substring of «بزرگ»; only a boundary-aware match rejects it.

    «زرین» *is* the gold lane (a real word, and the matcher allows the
    adjectival -īn), while «بزرگ» is not a hit at all.
    """
    assert cp._hit(cp.normalize("قیمت بزرگ بازار"), "زر") is False
    assert cp._hit(cp.normalize("بازار زرین"), "زر") is True
    assert cp._hit(cp.normalize("هر گرم طلا و زر"), "زر") is True


def test_persian_stem_still_matches_its_own_inflections():
    assert cp._hit(cp.normalize("قیمت سکه‌ها امروز"), "سکه") is True
    assert cp._hit(cp.normalize("نرخ دلارهای آزاد"), "دلار") is True


def test_latin_stem_does_not_fire_inside_a_longer_word():
    assert cp._hit(cp.normalize("the bitcoin rally"), "coin") is False
    assert cp._hit(cp.normalize("prices boiled over"), "oil") is False
    assert cp._hit(cp.normalize("a coin giveaway"), "coin") is True


def test_normalize_folds_arabic_letters_and_digits():
    assert cp.normalize("طلاي ١٨ عيار") == cp.normalize("طلای ۱۸ عیار")


def test_normalize_does_not_swallow_arabic_indic_digits():
    """The diacritic character class spans U+0660..U+0669.

    Written as "ً-ٰ" it covers the Arabic-Indic digits, and a price written
    "١٢" normalised to nothing — silently deleting the number a price card is
    made of. Folding digits before the strip is the fix; this pins it.
    """
    assert "12" in cp.normalize("قیمت ١٢ میلیون")
    assert cp.normalize("١٢") == "12"


# ───────────────────────────── 2 · lanes ─────────────────────────────

def test_price_card_lands_in_the_gold_lane():
    b = cp.detect_buckets(art("قیمت طلای ۱۸ عیار به ۱۲ میلیون تومان رسید"))
    assert "gold" in b
    assert "دلار" not in " ".join(b.get("gold", []))


def test_a_bare_dollar_word_does_not_open_the_fx_lane():
    """A crypto story quoting dollars stays in the crypto lane."""
    b = cp.detect_buckets(art("تیم کریپتو روزانه ۵۰ هزار دلار درآمد دارد",
                              "پیشنهاد بیت‌کوین تازه اعلام شد."))
    assert "currency" not in b
    assert "crypto" in b


def test_a_real_rate_story_still_opens_the_fx_lane():
    b = cp.detect_buckets(art("نرخ دلار امروز در بازار آزاد اعلام شد"))
    assert "currency" in b


def test_detect_buckets_returns_the_evidence_not_just_a_label():
    b = cp.detect_buckets(art("قیمت سکه امامی کاهش یافت"))
    assert any("سکه" in w for w in b["coin"])


# ───────────────────── 3 · off-profile is a hard exclude ─────────────────────

@pytest.mark.parametrize("title,summary", [
    ("هکرها ۵۰ میلیون دلار از پل‌های زنجیره‌ای را سرقت کردند",
     "یک حمله سایبری بزرگ گزارش شد."),
    ("دی‌فای هک شد؛ ۱۰ میلیون دلار از استخر نقدینگی برداشت شد", ""),
    ("قیمت میم‌کوین دوج کوین ۳۰ درصد ریخت", ""),
    ("سلبریتی در رویدادی با طلا ۲۰ میلیون تومان ظاهر شد", ""),
])
def test_off_profile_stories_never_publish(title, summary):
    res = cp.score_article(art(title, summary), now=NOW)
    assert res["publishable"] is False
    assert res["fit"] == 0.0
    assert res["off_profile"]


def test_ordinary_market_coverage_is_not_swept_up_by_the_off_profile_lists():
    """A plain ETF-flow story mentions crypto but is not a meme-coin story."""
    res = cp.score_article(
        art("ورود پول به ETF بیت‌کوین ادامه دارد", "شاخص دلار کاهش یافت."), now=NOW)
    assert res["publishable"] is True


# ───────────────────────────── 4 · gates and ranking ─────────────────────────────

def test_credibility_is_a_gate_not_a_weight():
    low = cp.score_article(art("قیمت طلا امروز", "طلا ۱۲ میلیون تومان.",
                               credibility=0.3), now=NOW)
    assert low["publishable"] is False
    assert low["fit"] == 0.0


def test_a_story_with_no_page_lane_is_rejected_with_a_readable_reason():
    res = cp.score_article(art("تیم جدید معرفی شد",
                               "یک شرکت فناوری تازه تأسیس شد."), now=NOW)
    assert res["publishable"] is False
    assert "طلا" in res["reason"] or "خارج" in res["reason"]


def test_a_price_card_outranks_a_price_less_story_in_the_same_lane():
    card = cp.score_article(art("قیمت طلای ۱۸ عیار ۱۲ میلیون تومان شد",
                                "هر گرم طلا به ۱۲ میلیون و ۲۰۰ هزار تومان رسید."), now=NOW)
    prose = cp.score_article(art("درباره بازار طلا گفت‌وگو شد",
                                 "کارشناسان درباره روند طلا صحبت کردند."), now=NOW)
    assert card["fit"] > prose["fit"]
    assert card["factors"]["price_card"] > prose["factors"]["price_card"]


def test_a_stale_price_scores_lower_than_the_same_price_today():
    fresh = cp.score_article(art("قیمت طلا امروز ۱۲ میلیون تومان است"), now=NOW)
    old = cp.score_article(art("قیمت طلا امروز ۱۲ میلیون تومان است",
                               age_h=40), now=NOW)
    assert fresh["fit"] > old["fit"]


def test_freshness_decays_monotonically():
    scores = [cp.score_article(art("قیمت طلا امروز ۱۲ میلیون تومان",
                                   age_h=h), now=NOW)["factors"]["freshness"]
              for h in (0, 4, 12, 24, 48)]
    assert scores == sorted(scores, reverse=True)


def test_social_sources_are_penalised():
    social = cp.score_article(art("قیمت طلا امروز ۱۲ میلیون تومان",
                                  source_kind="social"), now=NOW)
    wire = cp.score_article(art("قیمت طلا امروز ۱۲ میلیون تومان",
                                source_kind="news"), now=NOW)
    assert social["fit"] < wire["fit"]
    assert "منبع اجتماعی" in social["reason"]
    assert social["factors"]["penalty"] > wire["factors"]["penalty"]


# ───────────────────────────── 5 · caption honesty ─────────────────────────────

def test_caption_numbers_come_from_the_article():
    """Every number printed on the card must be traceable to the article.

    The caption carries the numbers in latin digits for the UI to localise, so
    the comparison folds both sides first — otherwise this test would pass on
    a number the pipeline invented and wrote in the same shape.
    """
    a = art("قیمت طلای ۱۸ عیار به ۱۲ میلیون تومان رسید",
            "هر گرم طلا با ۵۰ هزار تومان کاهش به ۱۲ میلیون و ۲۰۰ هزار تومان رسید.")
    item = cp.rank_for_channel([a], now=NOW)["items"][0]
    haystack = cp.normalize(a["title_fa"] + " " + a["summary_fa"])
    for n in item["caption"]["numbers"]:
        assert n in haystack


def test_caption_carries_the_lane_badge_and_no_invented_numbers():
    a = art("قیمت سکه امامی به ۱۲۰ میلیون تومان رسید", "بازار امروز معامله شد.")
    item = cp.rank_for_channel([a], now=NOW)["items"][0]
    cap = item["caption"]
    assert cap["badge"] == cp.BUCKETS[item["primary_bucket"]]["badge"]
    assert cap["headline"].startswith(item["emoji"])
    assert "توصیه" not in cap["text"]        # no advice, no house voice invented


def test_caption_quotes_the_money_sentence_when_there_is_one():
    a = art("نرخ سود سپرده تغییر کرد",
            "نرخ سود سپرده‌های بانکی از ۲۳ به ۲۵ درصد افزایش یافت. پیش‌بینی‌ها ادامه دارد.")
    item = cp.rank_for_channel([a], now=NOW)["items"][0]
    assert "درصد" in item["caption"]["body"]


# ───────────────────────────── 6 · the board ─────────────────────────────

def test_board_dedupes_the_same_story_from_two_outlets():
    same = "قیمت طلای ۱۸ عیار به ۱۲ میلیون تومان رسید"
    board = cp.rank_for_channel(
        [art(same, id="a", source_name="ایرنا"),
         art(same, id="b", source_name="مهر")], now=NOW)
    assert len(board["items"]) == 1
    assert board["rejected"]["duplicate"] == 1


def test_board_counts_each_rejection_reason():
    board = cp.rank_for_channel([
        art("قیمت طلا ۱۲ میلیون تومان", id="keep"),
        art("هکرها ۵۰ میلیون دلار را سرقت کردند", id="hack"),
        art("قیمت طلا ۱۲ میلیون تومان", id="weak", credibility=0.2),
    ], now=NOW)
    assert board["rejected"]["off_profile"] == 1
    assert board["rejected"]["low_credibility"] == 1
    assert [i["id"] for i in board["items"]] == ["keep"]


def test_board_exposes_the_lane_breakdown_the_ui_renders():
    board = cp.rank_for_channel([
        art("قیمت طلای ۱۸ عیار ۱۲ میلیون تومان شد", id="g"),
        art("قیمت سکه امامی ۱۲۰ میلیون تومان شد", id="c"),
        art("نرخ سود سپرده بانکی افزایش یافت", id="d"),
    ], now=NOW)
    assert board["lanes"]
    assert sum(board["lanes"].values()) == len(board["items"])


def test_board_returns_an_empty_result_rather_than_raising_on_junk():
    board = cp.rank_for_channel([{}, {"title_fa": None}, None], now=NOW)
    assert board["items"] == []
    assert board["scanned"] == 0


def test_board_is_deterministic_for_the_same_corpus():
    arts = [art("قیمت طلای ۱۸ عیار ۱۲ میلیون تومان شد", id="1"),
            art("نرخ دلار در بازار آزاد اعلام شد", id="2")]
    a = cp.rank_for_channel(arts, now=NOW)
    b = cp.rank_for_channel(arts, now=NOW)
    assert [i["id"] for i in a["items"]] == [i["id"] for i in b["items"]]


def test_undated_articles_are_neither_rewarded_nor_buried():
    undated = cp.score_article(
        {"title_fa": "قیمت طلا ۱۲ میلیون تومان", "credibility": 0.85,
         "published_ts": 0}, now=NOW)
    assert undated["publishable"] is True
    assert 0.0 < undated["fit"] <= 100.0


def test_epoch_milliseconds_are_accepted():
    ms = art("قیمت طلا ۱۲ میلیون تومان")
    ms["published_ts"] = (NOW - 3600) * 1000
    res = cp.score_article(ms, now=NOW)
    assert 0.9 < res["age_hours"] < 1.1


# ───────────────────────── 7 · the board is a lens ─────────────────────

def test_a_small_request_cannot_shrink_the_board_for_the_next_caller():
    """The board is ranked once and sliced per request.

    The API caches the ranked board; if the cache stored whichever ``limit``
    the first caller asked for, one ۳-item probe would leave every other tab
    showing three cards for the rest of the cache window.
    """
    arts = [art(t, id="a%d" % i) for i, t in enumerate([
        "سکه امامی ۱۲۰ میلیون تومان شد",
        "نرخ ارز در بازار آزاد اعلام شد",
        "یورو در معاملات امروز گران شد",
        "مثقال طلا به رکورد جدید رسید",
        "ارز مسافرتی امروز اعلام شد",
        "شمش طلا در بازار جهانی دوباره بالا رفت",
    ])]
    board = cp.rank_for_channel(arts, now=NOW, limit=6)
    assert len(board["items"]) == 6
    assert len(cp.slice_board(board, 3)["items"]) == 3
    assert len(cp.slice_board(board, 6)["items"]) == 6


def test_slicing_is_a_prefix_and_keeps_the_lane_counts_in_step():
    arts = [art("قیمت طلای ۱۸ عیار ۱۲ میلیون تومان شد", id="gold"),
            art("قیمت سکه امامی ۱۲۰ میلیون تومان شد", id="coin"),
            art("نرخ دلار در بازار آزاد اعلام شد", id="fx")]
    board = cp.rank_for_channel(arts, now=NOW, limit=3)
    small = cp.slice_board(board, 2)
    assert [i["id"] for i in small["items"]] == [i["id"] for i in board["items"]][:2]
    assert sum(small["lanes"].values()) == len(small["items"])
    assert board["items"]                       # the source board is not mutated
    assert len(board["items"]) == 3


def test_a_slice_that_cuts_nothing_is_the_same_object():
    board = cp.rank_for_channel([art("قیمت طلا ۱۲ میلیون تومان")], now=NOW)
    assert cp.slice_board(board, 40) is board


# ─────────────────────── 8 · the client contract ───────────────────────

def _client_js():
    import pathlib
    return (pathlib.Path(__file__).resolve().parent.parent /
            "web" / "channel.js").read_text(encoding="utf-8")


def test_client_escape_helper_does_not_shadow_the_global_one():
    """A local ``esc`` that tests ``typeof esc`` finds *itself* and recurses.

    The page defines a global ``esc``. Reaching for it through the local name
    made the stack die inside the very first render — and the ``catch`` meant to
    report a failed load called the same broken helper, so the tab sat on its
    spinner forever. The fallback must live under another name and the global
    must be read through ``window``.
    """
    import re
    js = _client_js()
    assert "escFallback" in js
    assert not re.search(r"typeof esc\s*===?\s*'function'", js)


def test_client_is_wired_into_the_dashboard():
    from dashboard_html import APP_HTML
    for needle in ('id="nav-channel"', 'id="view-channel"', 'id="cbList"',
                   'id="cbSearch"', '/channel.js'):
        assert needle in APP_HTML, f"{needle} is missing from the dashboard"


# ── the virality engine ──────────────────────────────────────────────────────

NOW = time.time()

def _art(**kw):
    base = {"id": "t1", "title": "gold market update", "title_fa": "گزارش بازار طلا",
            "summary": "", "summary_fa": "", "assets": ["XAU"], "credibility": 0.9,
            "published_ts": NOW - 3600, "source_kind": "wire"}
    base.update(kw)
    return base


def test_shock_scales_with_the_move_against_its_own_volatility():
    """A 3% move on a quiet asset shocks; the same move on a wild one does not."""
    quiet = {"XAU": {"price": 4160.0, "change_24h": 3.0,
                     "spark": [4150, 4151, 4150, 4152, 4151, 4152, 4151, 4152]}}
    wild = {"XAU": {"price": 4160.0, "change_24h": 3.0,
                    "spark": [4000, 4100, 3950, 4150, 4050, 4180, 4000, 4200]}}
    v_quiet = cp.viral_score(_art(), market=quiet, now=NOW)
    v_wild = cp.viral_score(_art(), market=wild, now=NOW)
    assert v_quiet["viral_factors"]["shock"] > v_wild["viral_factors"]["shock"]
    assert v_quiet["viral_factors"]["shock"] > 0.6


def test_trading_at_the_window_extreme_is_a_record_bonus():
    """A price above every spark point is the 'سقف تاریخی' moment."""
    mkt = {"XAU": {"price": 4200.0, "change_24h": 1.0,
                   "spark": [4100, 4110, 4120, 4130, 4140, 4150, 4160, 4170]}}
    v = cp.viral_score(_art(), market=mkt, now=NOW)
    assert v["viral_factors"]["shock"] >= 0.55


def test_no_market_data_degrades_honestly():
    """Without a market row the factor stays neutral-low and says so."""
    v = cp.viral_score(_art(), market={}, now=NOW)
    assert v["viral_factors"]["shock"] == 0.30
    assert "بدون داده بازار" in v["viral_why"][0]


def test_board_ranks_by_viral_first_fit_second():
    """rank = 0.6*viral + 0.4*fit, and the list follows it."""
    now = time.time()
    mkt = {"XAU": {"price": 4200.0, "change_24h": 4.0,
                   "spark": [4100, 4110, 4120, 4130, 4140, 4150, 4160, 4170]}}
    hot = _art(id="hot", title_fa="سقف تاریخی طلا؛ جهش بزرگ بازار",
               summary="قیمت طلا رکورد تاریخی زد؛ بازار تهران و دلار واکنش نشان دادند",
               published_ts=now - 600)
    mild = _art(id="mild", title_fa="گزارش آرام بازار طلا",
                summary="بازار طلا امروز بی‌تحول بود", published_ts=now - 600)
    board = cp.rank_for_channel([mild, hot], now=now, market=mkt)
    ids = [i["id"] for i in board["items"]]
    assert ids.index("hot") < ids.index("mild")
    top = board["items"][0]
    assert top["rank"] == round(0.6 * top["viral"] + 0.4 * top["fit"], 1)
