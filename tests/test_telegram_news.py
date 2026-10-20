"""telegram_news — the parser is pure, so it is tested against saved HTML.

The reader behind the dashboard's «اخبار تلگرامی» board fetches the PUBLIC
t.me/s/<handle> preview of a channel. Hitting the live page from the test
suite would make every run depend on Telegram's uptime and markup, so these
tests feed parse_channel_page() a real saved page and a few hand-cut shapes
(reply quote, media-only post, service message) instead.

The one test that does touch the network path monkeypatches requests.get.
"""
from __future__ import annotations

import telegram_news


# A trimmed but structurally faithful t.me/s/ page: one normal post (emoji,
# bold headline, blank lines, an external link and the channel's own footer
# link), one media-only post, one service message.
PAGE = """
<html><body>
<div class="tgme_widget_message_wrap">
  <div class="tgme_widget_message js-widget_message" data-post="newscitypro/16385">
    <div class="tgme_widget_message_bubble">
      <div class="tgme_widget_message_meta">…</div>
      <div class="tgme_widget_message_text js-message_text" dir="auto">
        <tg-emoji emoji-id="5411225014148014586"><i class="emoji"><b>&#x1F534;</b></i></tg-emoji><b>سخنگوی کمیسیون امنیت ملی: شروط هفت‌گانه ایران قطعی است</b><br/><br/>سخنگوی کمیسیون امنیت ملی مجلس گفت شروط قابل عقب‌نشینی نیست.<br/><br/><a href="https://leemeenal.app/news/x/">جزئیات بیشتر</a><br/><a href="https://t.me/newscitypro">&#x1F525; [@newscitypro](https://t.me/newscitypro)</a>
      </div>
      <a class="tgme_widget_message_date" href="https://t.me/newscitypro/16385"><time datetime="2026-10-11T12:37:06+00:00">12:37</time></a>
      <span class="tgme_widget_message_views">3.36K views</span>
    </div>
  </div>
</div>
<div class="tgme_widget_message_wrap">
  <div class="tgme_widget_message" data-post="newscitypro/16388">
    <div class="tgme_widget_message_video">video!</div>
    <a class="tgme_widget_message_date" href="https://t.me/newscitypro/16388"><time datetime="2026-10-11T13:32:00+00:00">13:32</time></a>
    <span class="tgme_widget_message_views">3.65K views</span>
  </div>
</div>
<div class="tgme_widget_message_wrap">
  <div class="tgme_widget_message_service">joined the channel</div>
</div>
</body></html>
"""


def _posts():
    return telegram_news.parse_channel_page(PAGE, "newscitypro")


def _by_id(posts, msg_id):
    return [p for p in posts if p["id"] == msg_id][0]


def test_newest_first_even_though_the_page_is_oldest_first():
    # the fixture lists 16385 then 16388 — Telegram's own page order
    assert [p["id"] for p in _posts()] == ["16388", "16385"]


def test_a_normal_post_keeps_the_persian_text_headline_link_and_time():
    first = _by_id(_posts(), "16385")
    assert first["id"] == "16385"
    assert first["url"] == "https://t.me/newscitypro/16385"
    # headline survives the emoji and the <b>, and the ZWNJ stays intact
    # (the channel opens every headline with an emoji — it stays part of it)
    assert "سخنگوی کمیسیون امنیت ملی" in first["title"]
    assert "عقب‌نشینی نیست" in first["text"]
    # the external link is kept as label + target, never as raw HTML
    assert "جزئیات بیشتر (https://leemeenal.app/news/x/)" in first["text"]
    assert "<" not in first["text"]
    # the channel's own footer link is noise, not content
    assert "t.me/newscitypro)" not in first["text"]
    assert first["time"] == "2026-10-11T12:37:06+00:00"
    assert first["views"] == 3360
    assert first["media"] is None


def test_a_video_only_post_is_kept_and_marked():
    video = _by_id(_posts(), "16388")
    assert video["media"] == "video"
    assert video["text"] == ""
    assert video["views"] == 3650


def test_a_service_message_is_dropped():
    assert sorted(p["id"] for p in _posts()) == ["16385", "16388"]


def test_a_reply_quote_never_becomes_the_post_body():
    page = """
    <div class="tgme_widget_message_wrap">
      <div class="tgme_widget_message" data-post="c/9">
        <div class="tgme_widget_message_reply">
          <div class="tgme_widget_message_text">نقل‌قول ناخوانده</div>
        </div>
        <div class="tgme_widget_message_text">بدنهٔ واقعی پست</div>
      </div>
    </div>"""
    posts = telegram_news.parse_channel_page(page, "c")
    assert len(posts) == 1
    assert posts[0]["text"] == "بدنهٔ واقعی پست"


def test_unreadable_views_become_none_not_a_guess():
    page = """
    <div class="tgme_widget_message_wrap">
      <div class="tgme_widget_message" data-post="c/3">
        <div class="tgme_widget_message_text">خبر</div>
        <span class="tgme_widget_message_views">بازدید؟</span>
      </div>
    </div>"""
    posts = telegram_news.parse_channel_page(page, "c")
    assert posts[0]["views"] is None


def test_the_registry_ships_the_first_channel_and_only_public_handles():
    handles = [s["handle"] for s in telegram_news.SOURCES]
    assert "newscitypro" in handles
    assert all(telegram_news.HANDLE_RE.match(h) for h in handles)


def test_fetch_source_reports_a_bad_handle_instead_of_raising():
    out = telegram_news.fetch_source("../../etc/passwd")
    assert out["ok"] is False
    assert out["error"] == "invalid_handle"


def test_fetch_source_serves_the_cache_and_honours_refresh(monkeypatch):
    telegram_news._CACHE.clear()
    calls = []

    class _Resp:
        text = PAGE

        def raise_for_status(self):
            return None

    def fake_get(url, **kw):
        calls.append(url)
        return _Resp()

    monkeypatch.setattr(telegram_news.requests, "get", fake_get)
    try:
        a = telegram_news.fetch_source("newscitypro")
        b = telegram_news.fetch_source("newscitypro")     # cached: no 2nd GET
        assert a["ok"] is True and a["posts"]
        assert b is a
        assert len(calls) == 1
        assert calls[0] == "https://t.me/s/newscitypro"

        telegram_news.fetch_source("newscitypro", refresh=True)
        assert len(calls) == 2
    finally:
        telegram_news._CACHE.clear()


# ─────────────────────── the dashboard wiring ───────────────────────

def _client_js():
    import pathlib
    return (pathlib.Path(__file__).resolve().parent.parent /
            "web" / "tgnews.js").read_text(encoding="utf-8")


def test_client_is_wired_into_the_dashboard():
    from dashboard_html import APP_HTML
    for needle in ('id="nav-tgnews"', 'id="view-tgnews"', 'id="tgNewsList"',
                   'id="tgNewsChips"', 'id="nav-balenews"', 'id="view-balenews"', '/tgnews.js'):
        assert needle in APP_HTML, f"{needle} is missing from the dashboard"


def test_client_reaches_the_global_escape_helper_through_window():
    import re
    js = _client_js()
    # the local binding may shadow the name (channel.js does the same), but the
    # typeof probe must go through window.esc — a bare `typeof esc` would test
    # the local itself and recurse until the stack dies
    assert "typeof window.esc" in js
    assert not re.search(r"typeof esc\s*===?\s*'function'", js)


def test_client_escapes_every_interpolated_server_field():
    js = _client_js()
    # each field that crosses the wire is passed through esc(...) on its way
    # into the card HTML — a raw p.title/src.handle would be an XSS hole
    for needle in ("esc(p.title", "esc(p.url", "esc(src.handle", "esc(text"):
        assert needle in js, f"{needle} — an unescaped field is being rendered"


def test_the_route_and_shell_asset_exist():
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    assert (root / "web" / "tgnews.js").is_file(), "the client half is missing"
    app_src = (root / "app.py").read_text(encoding="utf-8")
    assert '@app.route("/tgnews.js")' in app_src
    assert '@app.route("/api/telegram_news")' in app_src
    assert '@app.route("/api/telegram_news/test"' in app_src
    assert '@app.route("/api/telegram_news/send"' in app_src
    sw = (root / "web" / "sw.js").read_text(encoding="utf-8")
    assert "'/tgnews.js'" in sw, "the client is not precached as a shell asset"


def test_telegram_news_extra_sources():
    sources = telegram_news.get_sources([{"handle": "testchannel", "title": "Test Channel"}])
    assert any(s["handle"] == "testchannel" for s in sources)
    # duplicate handle is ignored
    dup = telegram_news.get_sources([{"handle": "newscitypro", "title": "Dup"}])
    assert len([s for s in dup if s["handle"].lower() == "newscitypro"]) == 1


def test_telegram_news_dispatch_and_posted_status(monkeypatch):
    import database
    import app

    import uuid
    test_handle = "mockchan"
    test_pid = uuid.uuid4().hex[:8]
    key = f"tgnews_{test_handle}_{test_pid}"

    # Verify initial state not posted
    assert not database.is_messenger_posted(key, "bale_ideas")

    # Mark posted
    database.mark_messenger_posted(key, "bale_ideas")
    assert database.is_messenger_posted(key, "bale_ideas")

def test_clean_for_messenger_strips_footers_and_social_promos():
    raw_sample = (
        "🪙 تحلیل فاندامنتال ارز گرام (تون کوین): رشد GRAM کی شروع میشه؟\n\n"
        "پروژه گرام در آستانه تحولات بزرگ قرار دارد.\n\n"
        "شرایط فاندامنتال پروژه گرام رو بررسی می‌کنیم.\n\n"
        "🔗 مطالعه متن کامل (https://nobitex.ir/mag/gram/)\n\n"
        "❌ نظر شما چیه؟ اگه موافقین 👍 بذارید\n\n"
        "⭕ مجله نوبیتکس رو در شبکه‌های اجتماعی دنبال کنید 👇\n\n"
        "📲 بله (https://ble.ir/join/xyz) | 🌐 تلگرام (https://t.me/xyz)\n"
    )
    title, body = telegram_news.clean_for_messenger(
        title="🪙 تحلیل فاندامنتال ارز گرام (تون کوین): رشد GRAM کی شروع میشه؟",
        text=raw_sample,
        source_title="مجله نوبیتکس",
        source_handle="Nobitexmag",
    )
    assert "تحلیل فاندامنتال ارز گرام" in title
    assert "پروژه گرام در آستانه تحولات بزرگ قرار دارد" in body
    assert "شرایط فاندامنتال پروژه گرام رو بررسی می‌کنیم" in body

    # Strictly no promo or social lines:
    assert "مطالعه متن کامل" not in body
    assert "شبکه‌های اجتماعی" not in body
    assert "دنبال کنید" not in body
    assert "بله (" not in body
    assert "تلگرام (" not in body
    assert "https://" not in body
    assert "مجله نوبیتکس" not in body
    assert "نظر شما چیه" not in body
    assert "👍" not in body




# ─────────────────────── Bale Channel & Delete Tests ───────────────────────

BALE_PAGE = """
<html><body>
<div class="MessageItem_messageWrapper__E9ZFU ChatWrapper_messageBlock__Wrs5L" data-sid="6395891297690950116-101">
 <div class="BaseBubble_bubble__4oHot DefaultBubble_bubble__s_5uz Text_textMessage__nC_tz MessageItem_bubble__38sVg">
  <a class="Preview_preview__B_ivv" href="/chan/old/1">
   <div class="Preview_details__CVlWn">
    <div class="Text_text__Um9IF TextPreview_text_preview___Mz_e"><span>نقل قول قدیمی</span></div>
   </div>
  </a>
  <div class="Text_text__Um9IF">
   <span class="p"><strong>تیتر خبر اول بله</strong></span><br/>
   <span class="p"><img class="emoji" data-codepoints="1f539"/>متن کامل خبر اول در پیام‌رسان بله</span>
   <span class="p"><a class="mention" href="https://ble.ir/chan">@chan</a></span>
  </div>
  <div class="Info_meta___R9G5">
   <div class="Info_ViewWrapper__O75PK"><p class="Info_Text__LVysg">2.5K</p></div>
   <p class="Info_date__fCTQ4">10:45</p>
  </div>
 </div>
</div>
<div class="MessageItem_messageWrapper__E9ZFU" data-sid="6395891297690950116-102">
 <div class="Photo_photo_message__yDO5Q">photo!</div>
 <div class="Text_text__Um9IF"><span>تیتر خبر دوم بله همراه با تصویر</span></div>
 <div class="Info_meta___R9G5">
  <div class="Info_ViewWrapper__O75PK"><p class="Info_Text__LVysg">500</p></div>
  <p class="Info_date__fCTQ4">11:00</p>
 </div>
</div>
</body></html>
"""


def test_parse_bale_channel_page():
    posts = telegram_news.parse_bale_channel_page(BALE_PAGE, "chan")
    # Newest first
    assert len(posts) == 2
    assert posts[0]["id"] == "102"
    assert posts[1]["id"] == "101"

    p101 = posts[1]
    assert "تیتر خبر اول بله" in p101["title"]
    assert "متن کامل خبر اول در پیام‌رسان بله" in p101["text"]
    assert "نقل قول قدیمی" not in p101["text"]
    assert "https://ble.ir/chan" not in p101["text"]
    assert "🔹" in p101["text"]
    assert p101["views"] == 2500
    assert p101["time"] == "10:45"
    assert p101["media"] is None

    p102 = posts[0]
    assert p102["media"] == "photo"
    assert p102["views"] == 500
    assert p102["time"] == "11:00"


def test_bale_fetch_source_with_mock(monkeypatch):
    class _Resp:
        text = BALE_PAGE
        def raise_for_status(self): return None

    monkeypatch.setattr(telegram_news.requests, "get", lambda url, **kw: _Resp())
    src = {"handle": "chan", "title": "Bale Chan", "type": "bale"}
    res = telegram_news.fetch_source("chan", refresh=True, sources=[src])
    assert res["ok"] is True
    assert res["type"] == "bale"
    assert len(res["posts"]) == 2


def test_channel_add_bale_and_delete_endpoints(monkeypatch, tmp_path):
    import app
    # isolate config
    monkeypatch.setitem(app.CONFIG, "telegram_news_sources", [])
    monkeypatch.setitem(app.CONFIG, "telegram_news_deleted_sources", [])
    monkeypatch.setattr(app, "save_config", lambda: None)

    client = app.app.test_client()

    # Add Bale channel
    r1 = client.post("/api/telegram_news/sources", json={
        "handle": "https://ble.ir/bale_test_chan",
        "title": "Bale Test",
        "type": "bale"
    })
    assert r1.status_code == 200
    sources = app.CONFIG.get("telegram_news_sources") or []
    assert any(s["handle"] == "bale_test_chan" and s["type"] == "bale" for s in sources)

    # Delete Bale channel
    r2 = client.post("/api/telegram_news/sources/delete", json={
        "handle": "bale_test_chan"
    })
    assert r2.status_code == 200
    sources_after = app.CONFIG.get("telegram_news_sources") or []
    assert not any(s["handle"] == "bale_test_chan" for s in sources_after)

    # Delete default channel (newscitypro)
    r3 = client.post("/api/telegram_news/sources/delete", json={
        "handle": "newscitypro"
    })
    assert r3.status_code == 200
    deleted = app.CONFIG.get("telegram_news_deleted_sources") or []
    assert "newscitypro" in deleted
    # Verify get_sources no longer includes newscitypro
    active = telegram_news.get_sources(sources_after, deleted)
    assert not any(s["handle"] == "newscitypro" for s in active)


def test_balenews_bot_config_and_test_endpoints(monkeypatch):
    import app
    # Keep main bale config separate
    main_bale_before = {"token": "MAIN_TOKEN_123", "chat": "@main_bale_channel"}
    monkeypatch.setitem(app.CONFIG, "bale", dict(main_bale_before))
    monkeypatch.setitem(app.CONFIG, "balenews_bot", {"token": "", "chat": ""})
    monkeypatch.setattr(app, "save_config", lambda: None)

    client = app.app.test_client()

    # Initial state: balenews bot is empty
    r1 = client.get("/api/balenews/config")
    assert r1.status_code == 200
    assert r1.json.get("has_token") is False
    assert r1.json.get("chat") == ""

    # Save dedicated balenews bot config
    r2 = client.post("/api/balenews/config", json={
        "token": "DEDICATED_BOT_456:DEF",
        "chat": "@dedicated_bale_channel"
    })
    assert r2.status_code == 200
    assert app.CONFIG["balenews_bot"]["chat"] == "@dedicated_bale_channel"
    assert app.CONFIG["balenews_bot"]["token"] == "DEDICATED_BOT_456:DEF"
    # Crucial: MAIN BALE CONFIG IS COMPLETELY UNTOUCHED!
    assert app.CONFIG["bale"] == main_bale_before

    # Secret masking on GET
    r3 = client.get("/api/balenews/config")
    assert r3.json.get("has_token") is True
    assert r3.json.get("token") == "••••••"
    assert r3.json.get("chat") == "@dedicated_bale_channel"

    # Test send endpoint
    sent_calls = []
    class FakeRes:
        error = ""
        def __bool__(self): return True

    monkeypatch.setattr(app, "_bale_send", lambda tok, chat, msg: (sent_calls.append((tok, chat, msg)), FakeRes())[1])

    r4 = client.post("/api/balenews/test", json={})
    assert r4.status_code == 200
    assert len(sent_calls) == 1
    assert sent_calls[0][0] == "DEDICATED_BOT_456:DEF"
    assert sent_calls[0][1] == "@dedicated_bale_channel"


def test_bale_clean_chat_formats():
    from app import _bale_clean_chat
    assert _bale_clean_chat("5544759284") == "5544759284"
    assert _bale_clean_chat("۵۵۴۴۷۵۹۲۸۴") == "5544759284"
    assert _bale_clean_chat("@dolar_taala") == "@dolar_taala"
    assert _bale_clean_chat("dolar_taala") == "@dolar_taala"
    assert _bale_clean_chat("https://ble.ir/dolar_taala") == "@dolar_taala"
    assert _bale_clean_chat("https://ble.ir/s/dolar_taala") == "@dolar_taala"
    assert _bale_clean_chat("ble.ir/s/dolar_taala?test=1") == "@dolar_taala"
    assert _bale_clean_chat("-1005544759284") == "5544759284"
    assert _bale_clean_chat("-5544759284") == "5544759284"
    assert _bale_clean_chat("https://bale.ai/dolar_taala") == "@dolar_taala"
    assert _bale_clean_chat("") == ""


def test_single_sentence_idea_composes_successfully():
    import ideas_post
    item = {
        "title_fa": "رشد بیت‌کوین و بازارهای سهام پس از کاهش نرخ بهره",
        "summary_fa": "ارزش بیت‌کوین در معاملات روز گذشته ۵ درصد افزایش یافت زیرا سرمایه‌گذاران انتظار رشد اقتصادی دارند."
    }
    res = ideas_post.compose_post(item)
    assert res is not None, "Single sentence idea should compose successfully, not return None"
    assert "title" in res
    assert len(res.get("blocks", [])) >= 1
    # Check that block starts with an allowed emoji
    first_block = res["blocks"][0]
    assert any(first_block.startswith(e) for e in ideas_post.PALETTE_EMOJIS)


def test_ideas_dispatch_status_includes_balenews():
    import app
    client = app.app.test_client()
    res = client.get("/api/ideas/dispatch-status")
    assert res.status_code == 200
    data = res.json
    assert data.get("ok") is True
    assert "balenews" in data
    assert "bale" in data
    assert "telegram" in data
    assert "recent_logs" in data


def test_custom_assets_multi_word_keywords():
    import sources
    patterns = sources.build_custom_patterns({
        "BRENT": {"keywords": "brent, brent crude, oil"},
        "N225": {"keywords": "nikkei 225, jp225, japan stock market"}
    })
    found1 = sources.detect_assets("Brent crude oil drops below $108", "", custom=patterns)
    assert "BRENT" in found1
    found2 = sources.detect_assets("Nikkei 225 advances in Tokyo trade", "", custom=patterns)
    assert "N225" in found2


def test_balenews_push_now_endpoint(monkeypatch):
    import app
    monkeypatch.setitem(app.CONFIG, "balenews_bot", {"token": "FAKE:BOT", "chat": "5544759284"})
    client = app.app.test_client()
    res = client.post("/api/balenews/push-now")
    assert res.status_code == 200
    assert res.json.get("ok") is True
