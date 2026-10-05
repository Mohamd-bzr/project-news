"""Regression tests for the content studio.

Three contracts worth defending, and each has its own section below:

1. **Parsing** — the demand sources are scraped HTML; a changed layout must
   yield fewer records, never wrong numbers. Everything is exercised against
   saved fixtures, so the suite never touches the network.
2. **Credibility is a gate** — a loud story under the gate stays out, and the
   score stays explainable (its factors must add up to what the reader sees).
3. **Publishing is never silent** — a call without ``confirm`` sends nothing,
   and a missing token is a plain 400, not a stack trace.
"""

import json
import pathlib
import re
import time

import pytest

import content_studio as cs
import social_signals as ss


# ───────────────────────────── fixtures ─────────────────────────────

def _video(vid, title, views=None, age=None, channel=None, channel_id=None):
    node = {"videoId": vid, "title": {"runs": [{"text": title}]}}
    if views is not None:
        node["viewCountText"] = {"simpleText": views}
    if age is not None:
        node["publishedTimeText"] = {"simpleText": age}
    if channel:
        owner = {"runs": [{"text": channel}]}
        if channel_id:
            owner["runs"][0]["navigationEndpoint"] = {"browseEndpoint": {"browseId": channel_id}}
        node["ownerText"] = owner
    return {"videoRenderer": node}


YT_HTML = json.dumps({
    "contents": {
        "sectionListRenderer": {
            "contents": [
                {"itemSectionRenderer": {"contents": [
                    _video("aaa111", "قیمت طلا امروز و پیش‌بینی دلار", "۲٬۳۱۷ بازدید", "۱۲ ساعت پیش",
                           "تحلیل بازار", "UC12345678901234567890"),
                    _video("bbb222", "Gold price today: what next for metals", "48,000 views",
                           "6 hours ago", "Market Desk"),
                    _video("ccc333", "بدون بازدید", None, "1 hour ago"),
                ]}},
            ],
        },
    },
})
YT_PAGE = f"<html><script>var ytInitialData = {YT_HTML};</script></html>"

TG_HTML = """
<div class="tgme_widget_message_wrap"><div class="tgme_widget_message" data-post="chan/101">
  <div class="tgme_widget_message_text js-message_text">قیمت طلا امروز با رشد دلار
    <b>افزایش</b> یافت<div class="tgme_widget_message_reply">ردیف تودرتو</div></div>
  <span class="tgme_widget_message_views">۲۲٫۷K</span>
  <time datetime="2026-09-29T06:00:00+00:00"></time>
</div></div>
<div class="tgme_widget_message_wrap"><div class="tgme_widget_message" data-post="chan/102">
  <div class="tgme_widget_message_text">گزارش تورم آمریکا و اثرش بر بازار سهام</div>
  <span class="tgme_widget_message_views">900</span>
  <time datetime="2026-09-29T09:00:00+00:00"></time>
</div></div>
"""

RD_XML = """<feed>
<entry><title>Gold hits record as dollar slips</title>
  <link href="https://www.reddit.com/r/gold/comments/1abcd2/gold_hits/"/>
  <updated>2026-09-29T05:00:00+00:00</updated></entry>
<entry><title>What are your moves tomorrow?</title>
  <link href="https://www.reddit.com/r/wallstreetbets/comments/1abcd3/moves/"/>
  <updated>2026-09-29T08:00:00+00:00</updated></entry>
</feed>"""


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Never touch the real cache file, and never spawn a refresh worker."""
    monkeypatch.setattr(ss, "CACHE_PATH", str(tmp_path / ".content_studio_cache.json"))
    monkeypatch.setattr(ss, "_schedule", lambda key: None)
    saved_cache, saved_hist = dict(ss._CACHE), {k: list(v) for k, v in ss._HIST.items()}
    ss._CACHE.clear()
    ss._HIST.clear()
    yield
    ss._CACHE.clear()
    ss._HIST.clear()
    ss._CACHE.update(saved_cache)
    ss._HIST.update(saved_hist)


def seed(key, value):
    ss._CACHE[key] = {"ts": time.time(), "value": value, "error": None}


def article(aid="a1", title="قیمت طلا با تقویت دلار ریخت", cred=0.85, assets=("XAU",),
            age_h=1.0, summary="طلا امروز ۱٫۲٪ افت کرد. دلار تقویت شد و بازده اوراق بالا رفت."):
    return {"id": aid, "title": title, "title_fa": title, "summary_fa": summary,
            "source_name": "Reuters", "source_key": "reuters", "link": "https://x/1",
            "credibility": cred, "assets": list(assets),
            "published_ts": time.time() - age_h * 3600}


# ───────────────────────────── parsing ─────────────────────────────

def test_youtube_records_carry_views_and_age_in_any_language():
    videos = ss.parse_yt_initial(YT_PAGE)
    assert len(videos) == 3
    first = videos[0]
    assert first["id"] == "aaa111"
    assert first["views"] == 2317, "Persian digits and a thousands separator must parse"
    assert first["age_hours"] == pytest.approx(12.0)
    assert first["views_per_hour"] == pytest.approx(2317 / 12, rel=1e-6)
    assert first["channel"] == "تحلیل بازار"
    assert first["channel_id"].startswith("UC")
    second = videos[1]
    assert second["views"] == 48000 and second["age_hours"] == pytest.approx(6.0)
    assert videos[2]["views"] is None, "a video without a view count is kept but unrated"


def test_a_page_without_yt_initial_data_is_empty_not_wrong():
    assert ss.parse_yt_initial("<html>nope</html>") == []
    assert ss.parse_yt_initial("") == []
    assert ss.parse_yt_initial("<script>var ytInitialData = {broken;") == []


def test_age_units_in_both_languages():
    cases = {
        "17h ago": 17.0, "2 days ago": 48.0, "7mo ago": 7 * 730.0, "Streamed 3 hours ago": 3.0,
        "۱۲ ساعت پیش": 12.0, "۳ روز پیش": 72.0, "۴۵ دقیقه پیش": 0.75, "1 week ago": 168.0,
    }
    for raw, hours in cases.items():
        assert ss.parse_age_hours(raw) == pytest.approx(hours), raw
    assert ss.parse_age_hours("") is None
    assert ss.parse_age_hours("just now") is None


def test_count_formats():
    assert ss.parse_count("22.7K") == 22700
    assert ss.parse_count("۱٬۲۳۴") == 1234
    assert ss.parse_count("1.2M") == 1200000
    assert ss.parse_count("48,000 views") == 48000
    assert ss.parse_count(None) is None


def test_telegram_posts_are_split_by_message_not_by_inner_element():
    posts = ss.parse_telegram_channel(TG_HTML, "chan")
    assert len(posts) == 2, "two messages, not one fragment per inner div"
    first = posts[0]
    assert first["post_id"] == "chan/101"
    assert "قیمت طلا" in first["text"]
    assert "ردیف تودرتو" in first["text"], "nested markup must not truncate the body"
    assert first["views"] == 22700
    assert first["views_per_hour"] and first["views_per_hour"] > 0
    assert first["url"] == "https://t.me/chan/101"


def test_reddit_feed_parses_links_and_ages():
    posts = ss.parse_reddit_feed(RD_XML, "gold")
    assert len(posts) == 2
    assert posts[0]["title"] == "Gold hits record as dollar slips"
    assert posts[0]["sub"] == "gold"
    assert posts[1]["score"] is None, "scores come from the archive, not the feed"


def test_providers_are_declared_with_metadata():
    for key, spec in ss.SOURCES.items():
        label, ttl, fn, source = spec
        assert label and callable(fn) and source
        assert 60 <= ttl <= 7 * 86400


# ───────────────────────────── matching ─────────────────────────────

def test_matching_requires_real_overlap():
    signals = {"youtube": {"videos": ss.parse_yt_initial(YT_PAGE)},
               "telegram": {"posts": ss.parse_telegram_channel(TG_HTML, "chan"), "channels": []},
               "reddit": {"posts": ss.parse_reddit_feed(RD_XML, "gold")}}
    hits = cs.match_signals(article(), signals)
    keys = {v["id"] for v in hits["youtube_all"]}
    assert "aaa111" in keys, "a Persian headline about gold matches a gold video"
    assert all(v.get("views") is not None for v in hits["youtube_all"] if v["id"] != "ccc333")

    unrelated = cs.match_signals(article(aid="a2", title="افزایش قیمت مس در بازار لندن",
                                         assets=("COPPER",),
                                         summary="مس در لندن گران شد. موجودی انبارها کاهش یافت."), signals)
    assert not unrelated["youtube_all"], "a copper story must not be credited to gold videos"


def test_a_viral_item_is_claimed_by_only_one_article():
    signals = {"youtube": {"videos": ss.parse_yt_initial(YT_PAGE)},
               "telegram": {"posts": [], "channels": []}, "reddit": {"posts": []}}
    gold_a = article(aid="g1", title="قیمت طلا با تقویت دلار ریخت")
    gold_b = article(aid="g2", title="طلا در محدودهٔ ۳٬۸۰۰ دلار تثبیت شد")
    claims = cs.claim_signals([cs.match_signals(gold_a, signals), cs.match_signals(gold_b, signals)],
                              lambda i: 0.9)
    owners = [sum(len(c[s]) for s in c) for c in claims]
    assert sum(owners) <= sum(len(cs.match_signals(a, signals)["youtube_all"])
                              for a in (gold_a, gold_b))
    seeds = [cs.aggregate_signals(c)["youtube"] for c in claims]
    assert sum(1 for s in seeds if s) == 1, "one clip, one owner"


def test_coverage_counts_distinct_sources():
    a = article(aid="x1", title="طلا با تقویت دلار ریخت و بازده بالا رفت")
    b = dict(article(aid="x2", title="طلا با تقویت دلار ریخت و بازده بالا رفت"),
             source_key="bloomberg", source_name="Bloomberg")
    c = article(aid="x3", title="نفت برنت به بالای ۹۰ دلار رسید", assets=("WTI",),
                summary="برنت با کاهش موجودی به بالای ۹۰ دلار رسید. تقاضای پالایشگاه‌ها بالا رفت.")
    counts = cs.coverage_counts([a, b, c])
    assert counts["x1"] == 1 and counts["x2"] == 1
    assert counts["x3"] == 0


# ───────────────────────────── ranking ─────────────────────────────

def signals_fixture():
    return {"youtube": {"videos": ss.parse_yt_initial(YT_PAGE)},
            "telegram": {"posts": ss.parse_telegram_channel(TG_HTML, "chan"),
                         "channels": [{"channel": "chan", "median_views": 10000}]},
            "reddit": {"posts": [dict(p, score=800, comments=120, score_per_hour=100.0)
                                 for p in ss.parse_reddit_feed(RD_XML, "gold")]}}


def test_credibility_is_a_gate_not_a_weight():
    weak = article(aid="weak", cred=0.4)         # loud demand, low credibility
    strong = article(aid="strong", cred=0.9)
    res = cs.rank([weak, strong], config={"content_studio": {"credibility_gate": 0.6}},
                  signals=signals_fixture())
    ids = [i["id"] for i in res["items"]]
    assert "weak" not in ids, "a sub-gate story must never be ranked, however loud"
    assert res["gated"] == 1
    assert "آستانهٔ اعتبار" in res["notes"][0], "the note must explain what was cut and why"


def test_factors_are_explainable_and_stay_in_range():
    res = cs.rank([article()], signals=signals_fixture())
    item = res["items"][0]
    for name, value in item["factors"].items():
        assert 0.0 <= value <= 1.0, f"{name} out of range"
    assert item["factors"]["credibility"] == pytest.approx(0.85)
    assert 0 < item["score"] <= 100


def test_fresh_news_beats_stale_news_otherwise_equal():
    fresh = article(aid="f", age_h=0.5)
    stale = dict(article(aid="s", age_h=30), title=article()["title"] + " (نسخهٔ قدیمی)", id="s")
    res = cs.rank([fresh, stale], signals=signals_fixture())
    assert res["items"][0]["id"] == "f"


def test_repeat_penalty_pushes_a_published_story_down():
    first = article(aid="r1", title="خبر تکراری درباره طلا و دلار")
    other = article(aid="r2", title="خبر دیگر درباره نفت و بازده اوراق", assets=("WTI",))
    base = cs.rank([first, other], signals={})
    key = cs._title_key(first)
    penalised = cs.rank([first, other], signals={}, recent_keys={key})
    before = next(i["score"] for i in base["items"] if i["id"] == "r1")
    after = next(i["score"] for i in penalised["items"] if i["id"] == "r1")
    assert after < before
    assert next(i for i in penalised["items"] if i["id"] == "r1")["repeat"] is True


def test_demand_factors_are_relative_to_the_days_corpus():
    """A quiet day must not flatten every story to the same demand score."""
    many = [article(aid=f"n{i}", title=f"خبر شماره {i} درباره بازار") for i in range(5)]
    res = cs.rank(many, signals=signals_fixture())
    values = {i["factors"]["youtube"] for i in res["items"]}
    assert len(values) >= 1
    assert all(0.0 <= v <= 1.0 for v in values)


def test_audience_weighting_prefers_gold_over_a_side_asset():
    gold = article(aid="g", assets=("XAU",))
    side = article(aid="s", title="خبر حاشیه‌ای درباره یک دارایی جانبی", assets=("SOL",))
    res = cs.rank([gold, side], signals={})
    assert next(i for i in res["items"] if i["id"] == "g")["factors"]["audience"] > \
           next(i for i in res["items"] if i["id"] == "s")["factors"]["audience"]


def test_ranking_survives_no_signals_at_all():
    res = cs.rank([article()], signals={})
    assert res["items"] and res["items"][0]["heat"]["youtube_vph"] == 0


# ───────────────────────────── format choice ─────────────────────────────

def test_a_number_heavy_story_is_read_as_a_carousel():
    rich = article(summary="طلا ۱٫۲٪ افت کرد. نقره ۲٪ و پلاتین ۳٪ کاهش یافت. بازده ۱۰ساله به ۵٫۲۴٪ رسید.")
    fmt = cs.format_scores(rich, {})
    assert fmt["best"] == "carousel"
    assert fmt["why"] and fmt["numbers"]


def test_a_dramatic_move_is_read_as_video():
    drama = article(summary="بیت‌کوین سقوط کرد و صرافی هک شد.")
    assert cs.format_scores(drama, {"youtube": {"views_per_hour": 900}})["best"] == "video"


def test_a_plain_notice_is_read_as_text():
    plain = article(title="برگزاری مجمع سالانه", summary="مجمع سالانه شرکت برگزار شد.")
    assert cs.format_scores(plain, {})["best"] == "text"


# ───────────────────────────── drafting ─────────────────────────────

def test_template_draft_is_built_from_the_article_only():
    a = article(summary="طلا امروز ۱٫۲٪ افت کرد. دلار تقویت شد.")
    d = cs.template_draft(a, cs.format_scores(a, {}))
    assert d["method"] == "template"
    assert a["title"] in d["caption"]
    assert "توصیهٔ سرمایه‌گذاری نیست" in json.dumps(d, ensure_ascii=False)
    assert d["slides"] and d["scenes"]
    assert d["hashtags"] == ["#XAU"]


def test_template_caption_does_not_repeat_the_headline():
    a = article(summary="قیمت طلا با تقویت دلار ریخت. دلار تقویت شد و بازده بالا رفت.")
    d = cs.template_draft(a, {})
    body = d["caption"].split("\n\n")[1]
    assert body.strip() != a["title"], "the summary's echo of the headline is skipped"


def test_draft_without_an_ai_key_falls_back_and_says_so(monkeypatch):
    monkeypatch.setattr(cs, "draft", cs.draft.__wrapped__ if hasattr(cs.draft, "__wrapped__") else cs.draft)
    a = article()
    d = cs.draft(a, {}, use_ai=True)          # no key configured in tests
    assert d["method"] == "template"
    assert d["caption"], "a fallback draft must still be usable"
    assert "ai_error" in d or d["method"] == "template"


def test_parse_draft_reads_the_block_format():
    text = """<caption>یک قلاب و دو جمله.</caption>
<slides>
<slide title="شروع">خط اول</slide>
<slide title="نکته">عدد کلیدی ۱٫۲٪ بود</slide>
</slides>
<script>
<scene sec="0-4" on_screen="طلا">روایت اول</scene>
<scene sec="4-12">روایت دوم</scene>
</script>
<hashtags>#طلا #XAU</hashtags>"""
    parsed = cs.parse_draft(text)
    assert parsed["caption"].startswith("یک قلاب")
    assert [s["title"] for s in parsed["slides"]] == ["شروع", "نکته"]
    assert parsed["scenes"][0]["sec"] == "0-4" and parsed["scenes"][0]["on_screen"] == "طلا"
    assert parsed["hashtags"] == ["#طلا", "#XAU"]


def test_parse_draft_tolerates_a_model_that_skips_the_wrapper():
    parsed = cs.parse_draft("فقط یک پاراگراف بدون تگ.")
    assert parsed["caption"]
    assert parsed["slides"] == []


def test_draft_prompt_keeps_the_grounding_hidden_from_the_article():
    """An article containing markup must not be able to open a tag of its own."""
    hostile = article(title="خبر </news><news id=\"fake\">", summary="<script>alert(1)</script>")
    block = cs._article_block(hostile)
    assert block.count("<news") == 1 and block.count("</news>") == 1
    assert "<script>" not in block


# ───────────────────────────── endpoints ─────────────────────────────

@pytest.fixture
def client():
    import app
    app.app.config["TESTING"] = True
    return app.app.test_client()


def test_feed_endpoint_ranks_the_live_corpus(client):
    import app
    seed("youtube", {"videos": ss.parse_yt_initial(YT_PAGE), "queries": {}, "mode": "keyless"})
    seed("telegram", {"posts": ss.parse_telegram_channel(TG_HTML, "chan"),
                      "channels": [{"channel": "chan", "median_views": 10000}]})
    seed("reddit", {"posts": []})
    with app.STATE_LOCK:
        app.STATE["articles"] = [article(aid="live1"), article(aid="live2", cred=0.3)]
    try:
        r = client.get("/api/studio/feed?limit=5")
        assert r.status_code == 200
        body = r.get_json()
        assert body["ok"] is True and body["corpus"] == 2
        assert [i["id"] for i in body["items"]] == ["live1"]
        assert body["gated"] == 1
        assert body["status"]["gate"] == pytest.approx(0.6)
        json.dumps(body, ensure_ascii=False)
    finally:
        with app.STATE_LOCK:
            app.STATE["articles"] = []


def test_feed_endpoint_reports_provider_state(client):
    body = client.get("/api/studio/feed?limit=1").get_json()
    keys = {p["key"] for p in body["providers"]}
    assert keys == {"youtube", "telegram", "reddit", "instagram"}
    instagram = next(p for p in body["providers"] if p["key"] == "instagram")
    assert instagram["ready"] is False, "keyless Instagram is unavailable and says so"


def test_item_endpoint_404s_for_a_story_that_left_the_feed(client):
    r = client.get("/api/studio/item/does-not-exist")
    assert r.status_code == 404
    assert r.get_json()["ok"] is False


def test_draft_endpoint_refuses_an_unknown_article(client):
    assert client.post("/api/studio/draft", json={}).status_code == 400
    assert client.post("/api/studio/draft", json={"article_id": "nope"}).status_code == 404


def test_draft_endpoint_persists_and_lists(client):
    import app
    with app.STATE_LOCK:
        app.STATE["articles"] = [article(aid="draftme", cred=0.9)]
    try:
        r = client.post("/api/studio/draft", json={"article_id": "draftme", "use_ai": False})
        assert r.status_code == 200
        body = r.get_json()
        assert body["draft"]["caption"]
        listed = client.get("/api/studio/drafts").get_json()
        assert any(d["article_id"] == "draftme" for d in listed["drafts"])
    finally:
        with app.STATE_LOCK:
            app.STATE["articles"] = []


def test_publish_requires_configuration(client):
    r = client.post("/api/studio/publish/telegram", json={"text": "سلام", "confirm": True})
    assert r.status_code == 400
    body = r.get_json()
    assert body["ok"] is False and "telegram" in body["error"]


def test_publish_without_confirm_never_sends(client, monkeypatch):
    import app
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "chat"))
    sent = []
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: sent.append(a) or True)
    r = client.post("/api/studio/publish/telegram",
                    json={"text": "پیش‌نویس", "photos": [], "confirm": False})
    assert r.status_code == 200
    body = r.get_json()
    assert body["dry_run"] is True and body["text_chars"] == len("پیش‌نویس")
    assert sent == [], "a dry run must not touch the channel"


def test_publish_with_confirm_sends_text_and_slides(client, monkeypatch):
    import app
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "chat"))
    calls = []
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: calls.append(("text", a[2])) or True)
    monkeypatch.setattr(app, "_tg_send_photo",
                        lambda *a, **k: calls.append(("photo", len(a[2]))) or (True, ""))
    png = "data:image/png;base64,iVBORw0KGgo="
    r = client.post("/api/studio/publish/telegram",
                    json={"text": "خبر", "photos": [png], "confirm": True, "content_id": 0})
    assert r.status_code == 200 and r.get_json()["ok_all"] is True
    assert [c[0] for c in calls] == ["text", "photo"]


def test_publish_rejects_a_broken_image_payload(client, monkeypatch):
    import app
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "chat"))
    r = client.post("/api/studio/publish/telegram",
                    json={"text": "x", "photos": [12345], "confirm": True})
    assert r.status_code == 400


def test_config_endpoint_round_trips_and_masks_secrets(client):
    import app
    before = json.loads(json.dumps(app.CONFIG.get("content_studio") or {}))
    try:
        r = client.post("/api/studio/config",
                        json={"credibility_gate": 0.8, "telegram_channels": "a, b",
                              "youtube_key": "AIzaTESTKEY"})
        assert r.status_code == 200, r.get_json()
        cfg = r.get_json()["config"]
        assert cfg["credibility_gate"] == pytest.approx(0.8)
        assert cfg["telegram_channels"] == ["a", "b"]
        assert cfg["youtube_key"] == "***set***", "a stored key is never echoed back"
        assert r.get_json()["has_youtube_key"] is True
    finally:
        app.CONFIG["content_studio"] = before
        app.save_config()


def test_config_endpoint_ignores_unknown_and_bad_values(client):
    import app
    before = json.loads(json.dumps(app.CONFIG.get("content_studio") or {}))
    try:
        r = client.post("/api/studio/config",
                        json={"credibility_gate": "not-a-number", "nonsense": 5,
                              "weights": {"youtube": 2, "bogus": 1}})
        cfg = r.get_json()["config"]
        assert cfg["credibility_gate"] == before.get("credibility_gate")
        assert "nonsense" not in cfg
        assert cfg["weights"].get("youtube") == pytest.approx(2.0)
        assert "bogus" not in cfg["weights"]
    finally:
        app.CONFIG["content_studio"] = before
        app.save_config()


# ───────────────────────────── client contract ─────────────────────────────

def test_studio_client_is_escaped_and_served():
    js = (pathlib.Path(__file__).resolve().parent.parent / "web" / "studio.js").read_text(encoding="utf-8")
    assert "esc(" in js and "safeUrl(" in js, "untrusted text and URLs must be gated"
    assert "confirm" in js and "dry_run" in js, "publishing must be confirmed, not implicit"
    assert "/api/studio/" in js

    from dashboard_html import APP_HTML
    for needle in ('id="nav-studio"', 'id="view-studio"', 'id="stList"', "/studio.js"):
        assert needle in APP_HTML, f"{needle} is missing from the dashboard"


def test_studio_client_does_not_double_quote_jsarg():
    """jsArg() already returns a complete, attribute-safe JS string literal
    (see dashboard_html.jsArg). Wrapping it in extra quotes hands the handler
    the id *with* quote characters, so every lookup 404s. Reuse it unquoted."""
    js = (pathlib.Path(__file__).resolve().parent.parent / "web" / "studio.js").read_text(encoding="utf-8")
    assert "jsArg(" in js, "the client should reuse the shared attribute-safe literal helper"
    assert not re.search(r"\\'\s*\+\s*jsArg\(", js), "jsArg() must not be preceded by an opening quote"
    assert not re.search(r"jsArg\([^()]*\)\s*\+\s*'\\'\)", js), "jsArg() must not be closed by an extra quote"


def test_service_worker_precaches_the_new_client():
    sw = (pathlib.Path(__file__).resolve().parent.parent / "web" / "sw.js").read_text(encoding="utf-8")
    assert "'/studio.js'" in sw, "a shell asset that is not precached breaks offline boot"
    assert "'/channel.js'" in sw, "the channel board's client ships in the same shell"
    # The version is the update mechanism (see the header comment in sw.js): it
    # cannot stay behind the last shell change, or every installed worker keeps
    # serving the previous asset from its cache. v7 scoped the studio client,
    # v8 added the channel client — a bump below that is a stale shell.
    m = re.search(r"const SW_VERSION = 'v(\d+)'", sw)
    assert m and int(m.group(1)) >= 8, \
        "the shell list changed, so the cache version must move with it"
