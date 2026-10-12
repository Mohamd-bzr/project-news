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
                   'id="tgNewsChips"', '/tgnews.js'):
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
