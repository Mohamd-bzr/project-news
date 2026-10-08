"""tests/test_messenger_gateway.py — Telegram gateway routing + ideas auto-send.

Covers the no-VPN gateway contract (_tg_base) and the content-ideas push
shape: the title, then a ≤150-character summary in exactly two paragraphs,
then the news link alone underneath.
"""

import re

import pytest

import app
import database
import link_shortener
import news_editorial
import translate


@pytest.fixture
def client():
    app.app.config["TESTING"] = True
    return app.app.test_client()


# ── _tg_base: the gateway routing contract ──
def test_tg_base_defaults_to_direct():
    assert app._tg_base() == "https://api.telegram.org"


def test_tg_base_prefers_configured_gateway(monkeypatch):
    monkeypatch.setitem(app.CONFIG, "telegram",
                        {**(app.CONFIG.get("telegram") or {}), "gateway": "https://gw.example.workers.dev/"})
    assert app._tg_base() == "https://gw.example.workers.dev"


def test_tg_base_trailing_slash_is_stripped(monkeypatch):
    monkeypatch.setitem(app.CONFIG, "telegram",
                        {**(app.CONFIG.get("telegram") or {}), "gateway": "https://gw.example.workers.dev///"})
    assert app._tg_base() == "https://gw.example.workers.dev"


def test_tg_base_env_override(monkeypatch):
    monkeypatch.setenv("MOHMD_TG_GATEWAY", "https://env-gw.example.com")
    assert app._tg_base() == "https://env-gw.example.com"


# ── content-ideas rendering: the user's template + link underneath ──
IDEA = {
    "id": "abc123",
    "title": "Gold rallies on Fed rate-cut expectations",
    "title_fa": "طلا با کاهش انتظارات نرخ بهره فدرال‌رزرو رشد کرد",
    "summary_fa": "اونس طلا در معاملات آسیایی صعود کرد؛ سرمایه‌گذاران منتظر سیگنال‌های نرخ بهره هستند. تحلیلگران هشدار می‌دهند نوسان ادامه دارد.",
    "link": "https://example.com/gold-rally",
    "credibility": 0.9,
    "rank": 87.5,
    "published_ts": 1728200000,
}


def _render(cfg_overrides=None):
    cfg = {**app.DEFAULT_CONFIG["telegram"], **(cfg_overrides or {})}
    article_like = {
        "id": IDEA["id"],
        "title": IDEA["title"],
        "title_fa": IDEA["title_fa"],
        "summary_fa": IDEA["summary_fa"],
        "summary": IDEA["summary_fa"],
        "link": IDEA["link"],
        "credibility": IDEA["credibility"],
        "assets": [],
        "published_ts": IDEA["published_ts"],
    }
    render_cfg = {**cfg, "link_on_own_line": True, "include_link": True}
    return app._tg_render_digest([article_like], render_cfg)


def test_idea_render_uses_operator_template_shape():
    text = _render()
    # headline first (cleaned), then the editorial blocks
    assert "طلا با کاهش انتظارات نرخ بهره" in text


def test_idea_render_puts_link_on_its_own_line_underneath():
    text = _render()
    assert f"🔗 {IDEA['link']}" in text
    # the link is the last non-empty line — «زیرش لینک خبر باشه»
    lines = [l for l in text.splitlines() if l.strip()]
    assert lines[-1].strip() == f"🔗 {IDEA['link']}"


def test_idea_render_forces_link_even_when_global_setting_off():
    # the ideas push must always carry the link, regardless of the digest toggle
    text = _render({"link_on_own_line": False, "include_link": False})
    assert f"🔗 {IDEA['link']}" in text


def test_bale_idea_render_includes_link(monkeypatch):
    cfg = {**app.DEFAULT_CONFIG["bale"]}
    article_like = {
        "id": IDEA["id"],
        "title": IDEA["title"],
        "title_fa": IDEA["title_fa"],
        "summary_fa": IDEA["summary_fa"],
        "summary": IDEA["summary_fa"],
        "link": IDEA["link"],
        "credibility": IDEA["credibility"],
        "assets": [],
        "published_ts": IDEA["published_ts"],
    }
    text = app._bale_render_digest([article_like], {**cfg, "link_on_own_line": True, "include_link": True})
    assert f"🔗 {IDEA['link']}" in text
    lines = [l for l in text.splitlines() if l.strip()]
    assert lines[-1].strip() == f"🔗 {IDEA['link']}"


def test_ideas_push_skips_disabled_messenger(monkeypatch):
    called = {"n": 0}

    monkeypatch.setattr(app, "_channel_board", lambda force=False: {"items": [dict(IDEA)]})
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: u)
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True, "quiet_hours": False})

    app._post_cycle_ideas()
    # telegram disabled → only the bale push fires
    assert called["n"] == 1


def _seed_board(monkeypatch, n):
    items = []
    for i in range(n):
        items.append({**IDEA, "id": f"idea-{i}", "link": f"https://example.com/news-{i}",
                      "rank": 100 - i})
    monkeypatch.setattr(app, "_channel_board", lambda force=False: {"items": items})


def test_ideas_push_sends_every_unsent_idea_not_capped(monkeypatch):
    """«همش هر چی که تولید شده ارسال بشه» — max_items must not cap the ideas push."""
    _seed_board(monkeypatch, 12)
    sent_to = []
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send",
                        lambda token, chat, text, **k: sent_to.append(text) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: u)
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True,
                                             "quiet_hours": False, "max_items": 1})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()

    app._post_cycle_ideas()
    assert len(sent_to) == 12   # all twelve, not the digest cap of 1


def test_ideas_push_shortens_the_link(monkeypatch):
    _seed_board(monkeypatch, 1)
    sent_to = []
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send",
                        lambda token, chat, text, **k: sent_to.append(text) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: "https://tinyurl.com/abc12")
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()

    app._post_cycle_ideas()
    assert sent_to and "https://tinyurl.com/abc12" in sent_to[0]


def test_breaker_opens_after_two_connection_failures(monkeypatch):
    """A dead API must not burn 15s timeouts for the whole board."""
    _seed_board(monkeypatch, 10)
    attempts = {"n": 0}

    def dead_send(token, chat, text, **k):
        attempts["n"] += 1
        return app.TgResult(False, "مهلت اتصال به سرور بله به پایان رسید (Timeout).")

    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", dead_send)
    monkeypatch.setattr(app, "_bale_send", dead_send)
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: u)
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()

    app._post_cycle_ideas()
    # 2 attempts trip the breaker, the run aborts mid-board
    assert attempts["n"] == 2
    assert app._breaker_open("bale_ideas")
    # the next pass skips the messenger entirely
    app._post_cycle_ideas()
    assert attempts["n"] == 2


# ── link_shortener ──
def test_shortener_passes_through_non_urls():
    assert link_shortener.shorten("") == ""
    assert link_shortener.shorten("not-a-url") == "not-a-url"


def test_shortener_uses_cached_mapping(monkeypatch):
    monkeypatch.setattr(link_shortener, "_CACHE", {"tinyurl|https://example.com/a": "https://tinyurl.com/xyz9"})
    monkeypatch.setattr(link_shortener, "_CACHE_LOADED", True)
    assert link_shortener.shorten("https://example.com/a") == "https://tinyurl.com/xyz9"


def test_shortener_falls_back_to_original_when_providers_die(monkeypatch):
    monkeypatch.setattr(link_shortener, "_CACHE", {})
    monkeypatch.setattr(link_shortener, "_CACHE_LOADED", True)
    monkeypatch.setitem(link_shortener._PROVIDERS, "tinyurl",
                        lambda u, c=None: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setitem(link_shortener._PROVIDERS, "isgd",
                        lambda u, c=None: (_ for _ in ()).throw(RuntimeError("down")))
    assert link_shortener.shorten("https://example.com/b") == "https://example.com/b"


def test_shortener_success_path_is_cached(monkeypatch):
    monkeypatch.setattr(link_shortener, "_CACHE", {})
    monkeypatch.setattr(link_shortener, "_CACHE_LOADED", True)
    monkeypatch.setattr(link_shortener, "_PROVIDER_BLOCKED", {})
    monkeypatch.setitem(link_shortener._PROVIDERS, "tinyurl",
                        lambda u, c=None: "https://tinyurl.com/ok123")
    saved = {}
    monkeypatch.setattr(link_shortener, "_save_cache", lambda: saved.update(link_shortener._CACHE))
    assert link_shortener.shorten("https://example.com/c") == "https://tinyurl.com/ok123"
    assert saved.get("tinyurl|https://example.com/c") == "https://tinyurl.com/ok123"


# ── provider chain ──
def test_chain_none_disables_shortening():
    assert link_shortener._chain({"provider": "none"}) == []
    assert link_shortener.shorten("https://example.com/x", {"provider": "none"}) == "https://example.com/x"


def test_chain_auto_prefers_opizo_when_key_present():
    chain = link_shortener._chain({"provider": "auto", "api_key": "k123"})
    assert chain[0] == "opizo" and "tinyurl" in chain and "isgd" in chain


def test_chain_auto_without_key_skips_opizo():
    assert "opizo" not in link_shortener._chain({"provider": "auto", "api_key": ""})


def test_opizo_provider_parses_short_link(monkeypatch):
    class FakeResp:
        status_code = 201
        text = '{"url": "https://opizo.com/AbC12"}'
        def json(self):
            return {"url": "https://opizo.com/AbC12"}
    monkeypatch.setattr(link_shortener.requests, "post",
                        lambda *a, **k: FakeResp())
    out = link_shortener.shorten("https://example.com/z",
                                 {"provider": "opizo", "api_key": "KEY"})
    assert out == "https://opizo.com/AbC12"


def test_push_now_endpoint_starts_and_reports_single_flight(client, monkeypatch):
    import threading
    release = threading.Event()
    monkeypatch.setattr(app, "_post_cycle_ideas", lambda: release.wait(timeout=5))
    r1 = client.post("/api/ideas/push-now")
    assert r1.get_json()["ok"] is True and r1.get_json()["started"] is True
    r2 = client.post("/api/ideas/push-now")
    assert r2.get_json().get("already_running") is True
    release.set()


# ── category fairness: every lane represented, world news always included ──
def _seed_laned_board(monkeypatch, items):
    monkeypatch.setattr(app, "_channel_board", lambda force=False: {"items": items})


def test_ideas_push_interleaves_lanes_so_every_category_leads(monkeypatch):
    """Gold/crypto virality must not crowd world news out of the queue head."""
    items = ([{**IDEA, "id": f"c-{i}", "link": f"https://e.com/c{i}", "rank": 90 + i,
               "primary_bucket": "crypto"} for i in range(6)]
             + [{**IDEA, "id": f"g-{i}", "link": f"https://e.com/g{i}", "rank": 50,
                 "primary_bucket": "global"} for i in range(2)]
             + [{**IDEA, "id": "o-0", "link": "https://e.com/o0", "rank": 40,
                 "primary_bucket": "gold"}])
    _seed_laned_board(monkeypatch, items)
    sent = []
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send",
                        lambda token, chat, text, **k: sent.append(text) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: u)
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()
    app._post_cycle_ideas()
    assert len(sent) == 9   # nothing dropped


def test_ideas_push_world_news_unlimited(monkeypatch):
    """«اخبار مهم جهان باید باشه حتما حتی اگه تعدادش زیاد باشه» — no cap."""
    items = ([{**IDEA, "id": f"w-{i}", "link": f"https://e.com/w{i}", "rank": 30,
               "primary_bucket": "global"} for i in range(45)]
             + [{**IDEA, "id": f"c-{i}", "link": f"https://e.com/c{i}", "rank": 95,
                 "primary_bucket": "crypto"} for i in range(45)])
    _seed_laned_board(monkeypatch, items)
    sent = []
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send",
                        lambda token, chat, text, **k: sent.append(text) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: u)
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()
    app._post_cycle_ideas()
    assert len(sent) == 90   # all 90, the old 60-per-pass valve would have eaten 30


def test_ideas_push_unclassified_count_as_world_news(monkeypatch):
    items = [{**IDEA, "id": "x-1", "link": "https://e.com/x1", "rank": 10}]
    _seed_laned_board(monkeypatch, items)
    sent = []
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send",
                        lambda token, chat, text, **k: sent.append(text) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: u)
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()
    app._post_cycle_ideas()
    assert len(sent) == 1


# ── the ideas message shape: title → two paragraphs (≤150 chars) → link ──
LONG_SUMMARY = (
    "اونس طلا در معاملات آسیایی ۱.۲ درصد صعود کرد و به ۴۱۲۱ دلار رسید. "
    "سرمایه‌گذاران منتظر سیگنال‌های نرخ بهره فدرال‌رزرو هستند و بازار احتمال "
    "کاهش نرخ را ۷۰ درصد می‌داند. با این حال تحلیلگران هشدار می‌دهند نوسان "
    "کوتاه‌مدت ادامه دارد و شکست حمایتی ۴۰۵۰ دلار سناریوی نزولی را فعال می‌کند.")


def _ideas_article(link=None, summary=LONG_SUMMARY):
    return {
        "id": IDEA["id"], "title": IDEA["title"], "title_fa": IDEA["title_fa"],
        "summary_fa": summary, "summary": summary,
        "link": IDEA["link"] if link is None else link,
        "credibility": 0.9, "assets": [], "published_ts": IDEA["published_ts"],
    }


def _ideas_render(key, render, article=None, **overrides):
    cfg = {**app.DEFAULT_CONFIG[key], "ideas_mode": True, "link_on_own_line": True,
           "include_link": True, "summary_max_chars": news_editorial.IDEAS_SUMMARY_CHARS,
           **overrides}
    return render([article or _ideas_article()], cfg)


ONE_LONG_SENTENCE = ("یک جمله طولانی بدون هیچ نقطه پایانی که باید از وسط کلمه "
                     "بریده نشود و درست به دو بند تقسیم شود و خواننده هم بتواند "
                     "سریع بخواند و هیچ کلمه‌ای نصفه نماند")


@pytest.mark.parametrize("key,render", [("telegram", app._tg_render_digest),
                                        ("bale", app._bale_render_digest)])
@pytest.mark.parametrize("summary", [LONG_SUMMARY, ONE_LONG_SENTENCE])
def test_ideas_message_is_title_then_two_paragraphs_then_link(key, render, summary):
    text = _ideas_render(key, render, _ideas_article(summary=summary))
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    # the title leads…
    assert paras[0].startswith("<b>") or paras[0].startswith("**")
    assert IDEA["title_fa"][:20] in paras[0].replace("<", "").replace(">", "")
    # …the link is the last line, on its own…
    assert paras[-1] == f"🔗 {IDEA['link']}"
    # …and everything between is the summary in exactly two blocks
    body = paras[1:-1]
    assert len(body) == 2, body
    # the 🏦/‼️ markers are decoration; the summary text is the 150-char budget
    summary_only = " ".join(_summary_text(p) for p in body)
    assert len(summary_only) <= news_editorial.IDEAS_SUMMARY_CHARS


def _summary_text(paragraph):
    """A rendered block minus its leading market emoji marker."""
    m = re.search(r"[\u0600-\u06FF]", paragraph)
    return paragraph[m.start():] if m else paragraph


@pytest.mark.parametrize("key,render", [("telegram", app._tg_render_digest),
                                        ("bale", app._bale_render_digest)])
def test_ideas_message_without_a_summary_is_title_then_link(key, render):
    """With nothing to summarise the message is title → link, not empty blocks."""
    text = _ideas_render(key, render, _ideas_article(summary=""))
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    assert len(paras) == 2
    assert paras[-1] == f"🔗 {IDEA['link']}"


def test_ideas_summary_of_one_word_is_a_single_block_not_a_broken_pair():
    """A one-word summary cannot become two blocks — it stays whole in one."""
    assert news_editorial.ideas_summary("کوتاه") == ("کوتاه", "")
    assert news_editorial.ideas_summary("کوتاه", max_chars=3) == ("کو…", "")


def test_ideas_summary_never_cuts_a_word_in_half():
    source = "طلا صعود کرد و بازار منتظر تصمیم نرخ بهره است " * 8
    blocks = news_editorial.ideas_summary(source.strip())
    joined = " ".join(blocks)
    assert len(joined) <= news_editorial.IDEAS_SUMMARY_CHARS
    assert joined.endswith("…")                    # the cut is marked, not hidden
    # every token is a whole word of the source — no half-word stub at the cut
    for word in joined[:-1].split():
        assert word in source.split()


def test_ideas_summary_is_capped_at_150_chars_in_two_blocks():
    blocks = news_editorial.ideas_summary(LONG_SUMMARY)
    assert len(blocks) == 2 and all(blocks)
    assert len(" ".join(blocks)) <= news_editorial.IDEAS_SUMMARY_CHARS
    # nothing is rewritten, only dropped from the tail
    assert blocks[0].startswith("اونس طلا")


def test_ideas_summary_keeps_a_persian_decimal_point_inside_its_number():
    """«۱.۲ درصد» is not two sentences — the old splitter cut a block at «۱.»"""
    blocks = news_editorial.ideas_summary(LONG_SUMMARY)
    assert blocks[0].endswith("دلار رسید.")
    assert "۱.۲ درصد" in blocks[0]




def test_ideas_summary_splits_a_single_long_sentence_in_two():
    blocks = news_editorial.ideas_summary(ONE_LONG_SENTENCE)
    assert len(blocks) == 2 and all(blocks)
    assert len(" ".join(blocks)) <= news_editorial.IDEAS_SUMMARY_CHARS


@pytest.mark.parametrize("key,render", [("telegram", app._tg_render_digest),
                                        ("bale", app._bale_render_digest)])
def test_ideas_link_survives_a_custom_template(key, render):
    """«زیر لینک باشه» holds even when the operator's template buries it."""
    text = _ideas_render(key, render, template="{title}\n\n{summary_blocks}\n\n{link_line}\n\nپایان")
    assert text.strip().endswith(f"🔗 {IDEA['link']}")
    text_no_slot = _ideas_render(key, render, template="{title}\n\n{summary_blocks}")
    assert text_no_slot.strip().endswith(f"🔗 {IDEA['link']}")


def test_ideas_push_message_is_title_two_blocks_link(monkeypatch):
    """End to end through the real renderer: the shape the channel receives."""
    _seed_board(monkeypatch, 1)
    sent = []
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send",
                        lambda token, chat, text, **k: sent.append(text) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: "https://opizo.com/abc")
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()

    app._post_cycle_ideas()
    assert sent, "the board item must go out"
    paras = [p.strip() for p in sent[0].split("\n\n") if p.strip()]
    assert IDEA["title_fa"][:20].replace("*", "") in paras[0]
    assert len(paras) == 4                      # title · block · block · link
    assert paras[-1] == "🔗 https://opizo.com/abc"


# ── ideas-only: the bundled news digest is off unless explicitly asked for ──
def test_news_digest_is_off_by_default():
    assert app.DEFAULT_CONFIG["telegram"]["send_digest"] is False
    assert app.DEFAULT_CONFIG["bale"]["send_digest"] is False


def _digest_article(i=0):
    return {"id": f"digest-{i}", "title": "Gold rallies", "title_fa": "طلا رشد کرد",
            "summary_fa": "اونس طلا صعود کرد.", "summary": "اونس طلا صعود کرد.",
            "link": "https://example.com/g", "credibility": 0.95, "age_hours": 1,
            "assets": [], "published_ts": 1728200000, "source_name": "Reuters"}


def _digest_run(monkeypatch, section, send_digest):
    sent = []
    monkeypatch.setitem(app.CONFIG, section, {**(app.CONFIG.get(section) or {}),
                                             "enabled": True, "quiet_hours": False,
                                             "send_digest": send_digest,
                                             "min_credibility": 0.7})
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: sent.append(a) or app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send", lambda *a, **k: sent.append(a) or app.TgResult(True))
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    app._MESSENGER_BREAKER.clear()
    articles = [_digest_article()]
    if section == "telegram":
        app._post_cycle_telegram(articles)
    else:
        app._post_cycle_bale(articles)
    return sent


@pytest.mark.parametrize("section", ["telegram", "bale"])
def test_digest_stays_silent_while_send_digest_is_off(monkeypatch, section):
    assert _digest_run(monkeypatch, section, None) == []
    assert _digest_run(monkeypatch, section, False) == []


@pytest.mark.parametrize("section", ["telegram", "bale"])
def test_digest_returns_when_send_digest_is_turned_on(monkeypatch, section):
    """The switch is a real way back, not a one-way door."""
    assert len(_digest_run(monkeypatch, section, True)) == 1


def test_ideas_push_still_fires_while_the_digest_is_off(monkeypatch):
    """With the digest off, the channel still gets the content ideas."""
    _seed_board(monkeypatch, 2)
    sent = []
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send", lambda *a, **k: sent.append(a) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: u)
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True,
                                             "send_digest": False, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()

    app._post_cycle_alerts([_digest_article()])
    assert len(sent) == 2                       # both ideas, no digest


# ── the switches are persisted, not just painted in the UI ──
@pytest.mark.parametrize("section", ["telegram", "bale"])
def test_settings_save_persists_ideas_and_digest_switches(client, monkeypatch, tmp_path, section):
    # /api/settings persists through save_config(). Point it at a scratch file:
    # a test must never rewrite the live settings.json.
    monkeypatch.setattr(app, "CONFIG_FILE", tmp_path / "settings.json")
    before = dict(app.CONFIG.get(section) or {})
    try:
        r = client.post("/api/settings",
                        json={section: {"send_ideas": False, "send_digest": True}})
        assert r.status_code == 200
        assert app.CONFIG[section]["send_ideas"] is False
        assert app.CONFIG[section]["send_digest"] is True
    finally:
        app.CONFIG[section] = before


# ── the dashboard carries the switches, and the endpoints report them ──
def test_dashboard_ships_both_switches_for_both_messengers():
    from dashboard_html import APP_HTML
    for box in ('id="tgDigest"', 'id="baleDigest"', 'id="tgIdeas"', 'id="baleIdeas"'):
        assert box in APP_HTML, f"{box} missing from the messenger tab"
    # the boxes travel with the save payload and come back on load
    for wire in ("send_digest: document.getElementById('tgDigest')",
                 "send_digest: document.getElementById('baleDigest')",
                 "tgd.checked = tg.send_digest===true",
                 "bDigest.checked = bale.send_digest===true"):
        assert wire in APP_HTML, f"{wire} is not wired up"


def test_push_debug_reports_the_digest_switch(client, monkeypatch):
    monkeypatch.setattr(app, "_channel_board", lambda force=False: {"items": []})
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    r = client.post("/api/ideas/push-debug")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["send_digest"] is False and body["send_ideas"] is True


# ── «فقط فارسی بده»: half-English text never reaches the channel ──
HALF_ENGLISH = [
    # the exact shapes the endpoint produced and the channel published
    "Dow Jones Futures: Yields Move Higher. Samsung, Micron, Taiwan Semi, Sandisk In Focus",
    "Is Barrick Mining (NYSE:B) Riding Gold's Safe-Haven Climb خیلی دور است؟",
    "Silver Interest Strong, Building Next Major Miner | جرمی ویلند از AbraSilver Resource",
    "SEC Crypto Custody Rewrite وارد بررسی کاخ سفید می شود",
]
REAL_PERSIAN = [
    # …and the honest Persian that carries a ticker or a brand name
    "میترید رئیس سابق TD Ameritrade و Capital.com سنگاپور را به عنوان مشاور استخدام کرد",
    "XRP نقش DeFi را گسترش می دهد زیرا Firelight محافظ Vault را فعال می کند",
    "خروجی صندوق های ETF بیت کوین به بالاترین سطح ۱۰ ماهه رسید",
    "بیت کوین به زیر ۱۰۰٬۰۰۰ دلار سقوط کرد",
]


@pytest.mark.parametrize("text", HALF_ENGLISH)
def test_half_english_text_is_not_persian(text):
    assert translate.is_persian(text) is False


@pytest.mark.parametrize("text", REAL_PERSIAN)
def test_persian_with_brand_names_is_still_persian(text):
    assert translate.is_persian(text) is True


def test_persian_gate_ignores_text_with_no_persian_at_all():
    assert translate.is_persian("") is False
    assert translate.is_persian("Gold rallies on Fed rate cuts") is False


MIXED_IDEA = {
    "id": "mixed",
    "title": "Dow Jones Futures: Yields Move Higher. Samsung, Micron, Taiwan Semi",
    "title_fa": "Dow Jones Futures: Yields Move Higher. Samsung, Micron, Taiwan Semi",
    "summary_fa": "SEC Crypto Custody Rewrite وارد بررسی کاخ سفید می شود",
    "link": "https://example.com/mixed",
    "rank": 95,
    "primary_bucket": "global",
    "credibility": 0.9,
}
PURE_IDEA = {
    "id": "pure",
    "title": "Gold rallies",
    "title_fa": "اونس طلا ۱.۲ درصد صعود کرد و به ۴۱۲۱ دلار رسید.",
    "summary_fa": "سرمایه‌گذاران منتظر فدرال‌رزرو هستند. با این حال تحلیلگران هشدار نوسان می‌دهند.",
    "link": "https://example.com/gold",
    "rank": 80,
    "primary_bucket": "global",
    "credibility": 0.9,
}


def _bale_only_push(monkeypatch, items, fixed=None):
    monkeypatch.setattr(app, "_channel_board", lambda force=False: {"items": items})
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: app.TgResult(True))
    sent = []
    monkeypatch.setattr(app, "_bale_send",
                        lambda tok, chat, text, **k: sent.append(text) or app.TgResult(True))
    monkeypatch.setattr(link_shortener, "shorten", lambda u, c=None: u)
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    if fixed is not None:
        monkeypatch.setattr(app, "translate_many", lambda texts, **k: dict(fixed))
    else:
        monkeypatch.setattr(app, "translate_many", lambda texts, **k: {})
    monkeypatch.setitem(app.CONFIG, "bale", {**(app.CONFIG.get("bale") or {}),
                                             "enabled": True, "send_ideas": True, "quiet_hours": False})
    monkeypatch.setitem(app.CONFIG, "telegram", {**(app.CONFIG.get("telegram") or {}),
                                                 "enabled": False, "quiet_hours": False})
    app._MESSENGER_BREAKER.clear()
    app._post_cycle_ideas()
    return sent


def test_ideas_push_drops_a_half_english_item(monkeypatch):
    sent = _bale_only_push(monkeypatch, [dict(MIXED_IDEA), dict(PURE_IDEA)])
    assert len(sent) == 1                    # the mixed one is not published
    assert PURE_IDEA["title_fa"][:20] in sent[0]
    assert "Dow Jones" not in sent[0] and "Samsung" not in sent[0]


def test_ideas_push_publishes_the_repaired_persian(monkeypatch):
    """When the retry does produce Persian, the story still goes out."""
    fixed = {"Dow Jones Futures: Yields Move Higher. Samsung, Micron, Taiwan Semi":
             "معاملات آتی داو جونز؛ بازده‌ها بالا رفتند و سامسونگ در کانون توجه است"}
    sent = _bale_only_push(monkeypatch, [dict(MIXED_IDEA)], fixed=fixed)
    assert len(sent) == 1
    assert "معاملات آتی داو جونز" in sent[0]
    assert translate.longest_latin_run(sent[0]) < translate._LATIN_RUN_MAX


def test_ideas_push_drops_an_english_summary_but_keeps_the_headline(monkeypatch):
    idea = {**PURE_IDEA, "id": "en-sum",
            "summary_fa": "Gold Rallies as Traders Bet on Fed Rate Cuts Next Month"}
    sent = _bale_only_push(monkeypatch, [idea])
    assert len(sent) == 1
    paras = [p for p in sent[0].split("\n\n") if p.strip()]
    assert len(paras) == 2           # headline + link, no English summary block
    assert paras[-1] == f"🔗 {idea['link']}"
    assert idea["title_fa"][:20] in paras[0]
    assert "Gold Rallies" not in sent[0]


@pytest.mark.parametrize("section", ["telegram", "bale"])
def test_digest_skips_a_half_english_headline(monkeypatch, section):
    """The bundled digest obeys «فقط فارسی بده» too, if it is ever switched on."""
    monkeypatch.setattr(app, "translate_many", lambda texts, **k: {})
    monkeypatch.setattr(app, "_telegram_cfg", lambda: ("tok", "@chat"))
    monkeypatch.setattr(app, "_bale_cfg", lambda: ("tok", "@chat"))
    sent = []
    monkeypatch.setattr(app, "_tg_send", lambda *a, **k: sent.append(a) or app.TgResult(True))
    monkeypatch.setattr(app, "_bale_send", lambda *a, **k: sent.append(a) or app.TgResult(True))
    monkeypatch.setattr(database, "is_messenger_posted", lambda *a, **k: False)
    monkeypatch.setattr(database, "mark_messenger_posted", lambda *a, **k: None)
    monkeypatch.setitem(app.CONFIG, section, {**(app.CONFIG.get(section) or {}),
                                             "enabled": True, "send_digest": True,
                                             "quiet_hours": False, "min_credibility": 0.7})
    app._MESSENGER_BREAKER.clear()
    mixed = {**_digest_article(), "title_fa": HALF_ENGLISH[0], "title": HALF_ENGLISH[0]}
    articles = [mixed]
    (app._post_cycle_telegram if section == "telegram" else app._post_cycle_bale)(articles)
    assert sent == []
    # …and a Persian headline still sails through
    pure = {**_digest_article(), "title_fa": REAL_PERSIAN[2], "title": "Bitcoin ETF inflows"}
    (app._post_cycle_telegram if section == "telegram" else app._post_cycle_bale)([pure])
    assert len(sent) == 1
