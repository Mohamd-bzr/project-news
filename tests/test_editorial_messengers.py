"""tests/test_editorial_messengers.py — Tests for the 17 financial editorial standards
across Telegram, Bale messenger, and Content Studio.
"""

import json
import pytest
import news_editorial
import app
import content_studio as cs


@pytest.fixture
def client():
    app.app.config["TESTING"] = True
    return app.app.test_client()


def test_detect_market_emoji_mapping():
    """Verify accurate detection of market emoji tags per Section 5 & 6."""
    assert news_editorial.detect_market_emoji({"title": "خبر فوری: سقوط بازارها"}) == "🚨"
    assert news_editorial.detect_market_emoji({"title": "بیانیه بانک مرکزی درباره نرخ بهره", "assets": []}) == "🏦"
    assert news_editorial.detect_market_emoji({"title": "گزارش تورم CPI آمریکا کمتر از انتظار", "assets": []}) == "📊"
    assert news_editorial.detect_market_emoji({"title": "قیمت اونس طلا صعود کرد", "assets": ["XAU"]}) == "🟡"
    assert news_editorial.detect_market_emoji({"title": "نقره جهانی افزایش یافت", "assets": ["XAG"]}) == "⚪"
    assert news_editorial.detect_market_emoji({"title": "قیمت نفت برنت در بازار جهانی", "assets": ["BRENT"]}) == "🛢️"
    assert news_editorial.detect_market_emoji({"title": "شاخص دلار آمریکا تقویت شد", "assets": ["DXY"]}) == "💵"
    assert news_editorial.detect_market_emoji({"title": "بیت‌کوین به ۹۲ هزار دلار رسید", "assets": ["BTC"]}) == "₿"
    assert news_editorial.detect_market_emoji({"title": "سقوط شدید قیمت مسکن", "assets": []}) == "📉"
    assert news_editorial.detect_market_emoji({"title": "رکورد تاریخی و جهش شدید بازار سهام", "assets": []}) == "📈"


def test_clean_editorial_title():
    """Verify title cleaning and word capping (10-15 words, clickbait removed)."""
    raw = "🚨 خبر فوری | 🟡 طلا با عبور از ۴۴۰۰ دلار رکورد جدیدی در معاملات بازارهای آسیایی و جهانی ثبت کرد"
    cleaned = news_editorial.clean_editorial_title(raw, max_words=12)
    assert not cleaned.startswith("🚨")
    assert not cleaned.startswith("🟡")
    assert "طلا با عبور از ۴۴۰۰ دلار" in cleaned
    assert len(cleaned.split()) <= 13


def test_format_editorial_summary_preserves_numbers():
    """Verify that numbers and drivers are never chopped and kept within 2-4 sentences."""
    summary = (
        "طلا در معاملات امروز ۱.۴ درصد افزایش یافت و به ۲۶۸۰ دلار رسید. "
        "افت دلار آمریکا و بازده اوراق قرضه دلیل اصلی این رشد بود. "
        "سرمایه‌گذاران منتظر انتشار آمار اشتغال ماهانه هستند. "
        "این در حالی است که پیش‌بینی‌ها از تداوم سیاست‌های انبساطی حکایت دارند."
    )
    body, takeaway = news_editorial.format_editorial_summary(summary, min_sents=2, max_sents=4)
    assert "۱.۴ درصد" in body
    assert "۲۶۸۰ دلار" in body
    assert len(body) > 30


def test_format_editorial_post_telegram_and_bale():
    """Verify standard post structure for both Telegram (HTML) and Bale (Markdown)."""
    article = {
        "title": "طلا صعود کرد و از ۲۶۸۰ دلار گذشت",
        "summary": "قیمت طلا امروز ۱.۵ درصد جهش کرد. افت شاخص دلار محرک اصلی فلز زرد بود.",
        "source_name": "رویترز",
        "assets": ["XAU"],
        "link": "https://example.com/gold-surge"
    }

    # Telegram format
    tg_post = news_editorial.format_editorial_post(article, target="telegram_html")
    assert tg_post.startswith("🟡")
    assert "<b>طلا صعود کرد" in tg_post
    assert "۱.۵ درصد" in tg_post
    assert "رویترز" in tg_post
    assert '<a href="https://example.com/gold-surge">' in tg_post

    # Bale format
    bale_post = news_editorial.format_editorial_post(article, target="bale")
    assert bale_post.startswith("🟡")
    assert "**طلا صعود کرد" in bale_post
    assert "۱.۵ درصد" in bale_post
    assert "رویترز" in bale_post
    assert "[مشاهده متن کامل خبر](https://example.com/gold-surge)" in bale_post


def test_tg_and_bale_render_digest_adhere_to_standard():
    """Verify that _tg_render_digest and _bale_render_digest render with market emojis and clean format."""
    articles = [
        {
            "id": "1",
            "title": "صعود اونس طلا به ۲۷۰۰ دلار",
            "summary": "طلا در معاملات امروز با رشد ۱.۲ درصدی همراه شد. دلار تحت فشار قرار گرفت.",
            "source_name": "بلومبرگ",
            "credibility": 0.88,
            "assets": ["XAU"],
            "published_ts": 1700000000,
            "link": "https://bloomberg.com/gold"
        },
        {
            "id": "2",
            "title": "تصمیم فدرال رزرو درباره نرخ بهره",
            "summary": "بانک مرکزی نرخ بهره را بدون تغییر در ۵.۲۵ درصد حفظ کرد.",
            "source_name": "رویترز",
            "credibility": 0.92,
            "assets": [],
            "published_ts": 1700000000,
            "link": "https://reuters.com/fed"
        }
    ]

    # TG digest
    tg_digest = app._tg_render_digest(articles, {"language": "fa", "emoji": True, "template": app.TG_TEMPLATE_DEFAULT})
    assert "🟡" in tg_digest
    assert "🏦" in tg_digest
    assert "۱.۲" in tg_digest or "1.2" in tg_digest
    assert "۵.۲۵" in tg_digest or "5.25" in tg_digest

    # Bale digest
    bale_digest = app._bale_render_digest(articles, {"language": "fa", "emoji": True, "template": app.BALE_TEMPLATE_DEFAULT})
    assert "🟡" in bale_digest
    assert "🏦" in bale_digest
    assert "**" in bale_digest


def test_content_studio_draft_follows_editorial_standard():
    """Verify that the template fallback in content_studio uses market emojis and standard structure."""
    art = {
        "title": "رکوردشکنی قیمت نفت برنت در بازارهای جهانی",
        "summary": "قیمت نفت برنت با رشد ۲.۸ درصدی به ۸۵ دلار رسید. کاهش ذخایر سوخت عامل اصلی افزایش قیمت بود.",
        "source_name": "اوپک",
        "assets": ["BRENT"],
        "credibility": 0.85
    }

    d1 = cs.template_draft(art)
    assert d1["caption"].startswith("🛢️")
    assert "۸۵ دلار" in d1["caption"]
    assert "اوپک" in d1["caption"]


def test_studio_publish_bale_endpoint(client):
    """Test /api/studio/publish/bale endpoint for validation and dry run."""
    # Empty payload
    r1 = client.post("/api/studio/publish/bale", json={})
    assert r1.status_code == 400

    # Without bale configured
    orig_bale = app.CONFIG.get("bale")
    try:
        app.CONFIG["bale"] = {"token": "", "chat": ""}
        r2 = client.post("/api/studio/publish/bale", json={"text": "تست خبر مالی"})
        assert r2.status_code == 400
        assert "bale not configured" in r2.get_json()["error"]

        # With mock credentials, test dry run
        app.CONFIG["bale"] = {"token": "123:ABC", "chat": "@my_channel"}
        r3 = client.post("/api/studio/publish/bale", json={"text": "🟡 **طلا به رکورد رسید**\n\nمتن خبر", "confirm": False})
        assert r3.status_code == 200
        data3 = r3.get_json()
        assert data3["dry_run"] is True
        assert "پیش‌نمایش" in data3["hint"]
    finally:
        if orig_bale:
            app.CONFIG["bale"] = orig_bale
        else:
            app.CONFIG.pop("bale", None)


def test_database_messenger_posted_dedup():
    """Verify messenger_posted database table correctly records and checks posted IDs."""
    import uuid
    import database
    # unique id + cleanup: the test writes to the real .mohmd_news.db, so a
    # fixed id left a row behind that failed the next run's first assertion
    test_id = f"test_art_dedup_{uuid.uuid4().hex[:12]}"
    try:
        assert not database.is_messenger_posted(test_id, "telegram")
        database.mark_messenger_posted(test_id, "telegram")
        assert database.is_messenger_posted(test_id, "telegram")
        # Bale platform is tracked separately
        assert not database.is_messenger_posted(test_id, "bale")
        database.mark_messenger_posted(test_id, "bale")
        assert database.is_messenger_posted(test_id, "bale")
    finally:
        with database.get_connection() as conn:
            conn.execute("DELETE FROM messenger_posted WHERE article_id = ?;", (test_id,))


def test_single_news_render_no_batch_header():
    """Verify that when rendering an individual news item, batch header is omitted."""
    article = {
        "id": "single_1",
        "title": "رشد ۳ درصدی سهام تسلا",
        "summary": "سهام تسلا پس از گزارش مالی سه ماهه سوم با جهش ۳ درصدی همراه شد.",
        "source_name": "رویترز",
        "credibility": 0.85,
        "assets": [],
        "published_ts": 1700000000
    }
    tg_text = app._tg_render_digest([article], {"language": "fa", "emoji": True, "template": app.TG_TEMPLATE_DEFAULT})
    assert "خبرهای معتبر چرخه اخیر" not in tg_text
    assert "MOHMD NEWS" not in tg_text
    assert "رشد ۳ درصدی" in tg_text

    bale_text = app._bale_render_digest([article], {"language": "fa", "emoji": True, "template": app.BALE_TEMPLATE_DEFAULT})
    assert "معتبرترین خبرهای بازار" not in bale_text
    assert "رشد ۳ درصدی" in bale_text


def test_studio_autopost_now_endpoint(client, monkeypatch):
    """Test /api/studio/autopost/now endpoint."""
    with app.STATE_LOCK:
        app.STATE["articles"] = [{
            "id": "studio_art_1",
            "title": "افزایش تاریخی ذخایر طلای بانک‌های مرکزی",
            "title_fa": "افزایش تاریخی ذخایر طلای بانک‌های مرکزی",
            "summary": "بانک‌های مرکزی جهان بیش از ۱۰۰۰ تن طلا به ذخایر خود اضافه کردند.",
            "summary_fa": "بانک‌های مرکزی جهان بیش از ۱۰۰۰ تن طلا به ذخایر خود اضافه کردند.",
            "source_name": "بلومبرگ",
            "credibility": 0.90,
            "assets": ["XAU"],
            "published_ts": 1700000000
        }]

    # Mock _tg_send so we don't hit live telegram API
    monkeypatch.setattr(app, "_tg_send", lambda token, chat, text, silent=False: app.TgResult(True))
    
    orig_tg = app.CONFIG.get("telegram")
    try:
        app.CONFIG["telegram"] = {"token": "123:MOCK", "chat": "-100123456"}
        r = client.post("/api/studio/autopost/now")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True
        assert "طلای بانک‌های مرکزی" in data["title"]
        assert "🟡" in data["text"] or "🏦" in data["text"]
    finally:
        if orig_tg:
            app.CONFIG["telegram"] = orig_tg
        else:
            app.CONFIG.pop("telegram", None)

