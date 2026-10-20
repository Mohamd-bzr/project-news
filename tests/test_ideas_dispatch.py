import unittest
from unittest.mock import patch, MagicMock
import news_editorial
import app
from app import _post_cycle_ideas, _post_cycle_alerts


class TestIdeasDispatch(unittest.TestCase):
    def test_ideas_summary_character_budget(self):
        long_persian = (
            "داده‌های سیتی (Citi) نشان می‌دهد خرید کالاهای لوکس با کارت اعتباری در آمریکا برای سومین ماه پیاپی "
            "کاهش یافته است. این هزینه‌کرد در سپتامبر نسبت به سال قبل 6% کمتر شده؛ در حالی که کاهش ماه‌های جولای و آگوست "
            "هر کدام حدود 4% بود. با این حال بیشترین ضعف در بخش ساعت و جواهرات لوکس دیده شده، در حالی که پوشاک و کالاهای "
            "چرمی کمی بهتر عمل کرده‌اند. تحلیلگران می‌گویند نگرانی درباره‌ی اقتصاد آمریکا و نزدیک شدن انتخابات میان‌دوره‌ای "
            "باعث شده مصرف‌کنندگان محتاط‌تر خرج کنند و از خریدهای گران‌قیمت اجتناب کنند. این روند می‌تواند فروش شرکت‌های "
            "بزرگ اروپایی را تحت فشار شدیدی قرار دهد."
        )
        lead, caveat = news_editorial.ideas_summary(long_persian, max_chars=510)
        total_len = len(lead) + len(caveat) + (1 if caveat else 0)
        self.assertTrue(lead)
        self.assertTrue(caveat)
        self.assertLessEqual(total_len, 515)
        self.assertGreaterEqual(total_len, 450)

    def test_user_example_structure(self):
        article = {
            "title_fa": "آمریکایی‌ها برای کالاهای لوکس کمتر خرج می‌کنند",
            "summary_fa": (
                "داده‌های سیتی (Citi) نشان می‌دهد خرید کالاهای لوکس با کارت اعتباری در آمریکا برای سومین ماه پیاپی کاهش یافته است. "
                "این هزینه‌کرد در سپتامبر نسبت به سال قبل 6% کمتر شده؛ در حالی که کاهش ماه‌های جولای و آگوست هر کدام حدود 4% بود. "
                "بیشترین ضعف در بخش ساعت و جواهرات لوکس دیده شده، در حالی که پوشاک و کالاهای چرمی کمی بهتر عمل کرده‌اند. "
                "تحلیلگران می‌گویند نگرانی درباره‌ی اقتصاد آمریکا و نزدیک شدن انتخابات میان‌دوره‌ای باعث شده مصرف‌کنندگان محتاط‌تر خرج کنند."
            ),
            "link": "https://www.tgju.org/news/123456",
        }
        emoji = news_editorial.detect_market_emoji(article)
        self.assertEqual(emoji, "🇺🇸")

        lead, caveat = news_editorial.ideas_summary(article["summary_fa"], max_chars=510)
        self.assertTrue(lead)
        self.assertTrue(caveat)

    @patch("link_shortener.shorten", side_effect=lambda u, *a, **k: u)
    @patch("app._channel_board")
    @patch("app._tg_send")
    @patch("app._bale_send")
    @patch("app._telegram_cfg", return_value=("tok", "@chat"))
    @patch("app._bale_cfg", return_value=("tok", "@chat"))
    @patch("database.is_messenger_posted", return_value=False)
    @patch("database.mark_messenger_posted")
    def test_dispatch_ideas_to_both_messengers(self, mock_mark, mock_posted, mock_bale_cfg, mock_tg_cfg, mock_bale, mock_tg, mock_board, mock_shorten):
        mock_board.return_value = {
            "items": [
                {
                    "id": "test_idea_1",
                    "title": "US Luxury Spending Drops",
                    "title_fa": "آمریکایی‌ها برای کالاهای لوکس کمتر خرج می‌کنند",
                    "summary_fa": (
                        "داده‌های سیتی (Citi) نشان می‌دهد خرید کالاهای لوکس در آمریکا کاهش یافته است. "
                        "اما بیشترین افت در جواهرات و ساعت دیده می‌شود."
                    ),
                    "link": "https://www.tgju.org/news/test-1",
                    "primary_bucket": "global",
                }
            ]
        }
        mock_tg.return_value = MagicMock(ok=True)
        mock_bale.return_value = MagicMock(ok=True)

        _post_cycle_ideas()

        # Verify Telegram send called with bold title, emoji lead, ‼️ caveat, text link, and inline button
        self.assertTrue(mock_tg.called)
        tg_args, tg_kwargs = mock_tg.call_args
        tg_text = tg_args[2]
        self.assertIn("<b>آمریکایی‌ها برای کالاهای لوکس کمتر خرج می‌کنند</b>", tg_text)
        self.assertIn("🇺🇸 ", tg_text)
        self.assertIn("‼️ ", tg_text)
        self.assertNotIn("🔗", tg_text)
        self.assertIsNone(tg_kwargs.get("reply_markup"))

        # Verify Bale send called with bold title, emoji lead, ‼️ caveat, NO link, and NO inline button
        self.assertTrue(mock_bale.called)
        bale_args, bale_kwargs = mock_bale.call_args
        bale_text = bale_args[2]
        self.assertIn("*آمریکایی‌ها برای کالاهای لوکس کمتر خرج می‌کنند*", bale_text)
        self.assertIn("🇺🇸 ", bale_text)
        self.assertIn("‼️ ", bale_text)
        self.assertNotIn("🔗", bale_text)
        self.assertIsNone(bale_kwargs.get("reply_markup"))

    @patch("app._post_cycle_ideas")
    @patch("app._post_cycle_telegram")
    @patch("app._post_cycle_bale")
    def test_post_cycle_alerts_ideas_only(self, mock_bale, mock_tg, mock_ideas):
        _post_cycle_alerts([])
        self.assertTrue(mock_ideas.called)
        self.assertFalse(mock_tg.called)
        self.assertFalse(mock_bale.called)

    @patch("app._channel_board")
    @patch("app._tg_send")
    @patch("app._bale_send")
    @patch("app.translate_many", return_value={})
    @patch("database.is_messenger_posted", return_value=False)
    @patch("database.mark_messenger_posted")
    def test_english_ideas_skipped_strictly(self, mock_mark, mock_posted, mock_trans, mock_bale, mock_tg, mock_board):
        # Ideas with only English content and failed translation must be dropped completely
        mock_board.return_value = {
            "items": [
                {
                    "id": "english_idea_1",
                    "title": "Federal Reserve Cuts Interest Rates Unexpectedly",
                    "title_fa": "",  # Empty
                    "summary": "The Federal Reserve announced an unexpected emergency interest rate cut today.",
                    "summary_fa": "",
                    "link": "https://www.bloomberg.com/news/123",
                    "primary_bucket": "global",
                },
                {
                    "id": "english_idea_2",
                    "title": "Tech stocks rally",
                    "title_fa": "Tech stocks rally",  # Still English
                    "summary_fa": "Silicon valley companies saw major gains across the board.",  # English
                    "link": "https://www.reuters.com/news/456",
                    "primary_bucket": "tech",
                }
            ]
        }
        _post_cycle_ideas()

        # Both English articles must be rejected, neither TG nor Bale should be called
        self.assertFalse(mock_tg.called)
        self.assertFalse(mock_bale.called)
        self.assertFalse(mock_mark.called)

    def test_ideas_summary_no_half_sentence_chopping(self):
        # A single complex sentence must not be chopped in half leaving a dangling '، و'
        anthropic_sentence = (
            "طبق گزارش‌ها، آنتروپیک قصد دارد تا قبل از عید شکرگزاری در نزدک فهرست شود، و "
            "یک شرکت مشاوره نزولی به سرمایه‌گذاران پیشنهاد می‌کند که از این فهرست خارج شوند."
        )
        lead, caveat = news_editorial.ideas_summary(anthropic_sentence, max_chars=1000)
        self.assertFalse(lead.endswith("، و"))
        self.assertFalse(lead.endswith("،"))
        self.assertFalse(lead.endswith("و"))
        # Must be complete
        self.assertEqual(lead, anthropic_sentence)
        self.assertEqual(caveat, "")


    @patch("app._tg_send")
    @patch("app._bale_send")
    def test_messenger_ideas_only_skips_all_other_senders(self, mock_bale, mock_tg):
        with patch.dict(app.CONFIG, {"messenger_ideas_only": True}):
            app._post_cycle_telegram([{"id": "a1"}])
            app._post_cycle_bale([{"id": "a2"}])
            app._post_cycle_tgnews()
            app._studio_autopost()
            self.assertFalse(mock_tg.called)
            self.assertFalse(mock_bale.called)

    @patch("link_shortener.shorten", side_effect=lambda u, *a, **k: u)
    @patch("app._channel_board")
    @patch("app._tg_send")
    @patch("app._bale_send")
    @patch("app._telegram_cfg", return_value=("tok", "@chat"))
    @patch("app._bale_cfg", return_value=("tok", "@chat"))
    @patch("database.is_messenger_posted", return_value=False)
    @patch("database.mark_messenger_posted")
    def test_messenger_ideas_only_still_sends_ideas(self, mock_mark, mock_posted, mock_bale_cfg, mock_tg_cfg, mock_bale, mock_tg, mock_board, mock_shorten):
        mock_board.return_value = {
            "items": [{
                "id": "idea_keep",
                "title_fa": "تست ارسال ایده در حالت فقط ایده",
                "summary_fa": "متن تستی که باید حتما ارسال شود و متوقف نگردد.",
                "link": "https://example.com/keep",
                "primary_bucket": "global",
            }]
        }
        mock_tg.return_value = MagicMock(ok=True)
        mock_bale.return_value = MagicMock(ok=True)
        with patch.dict(app.CONFIG, {"messenger_ideas_only": True}):
            _post_cycle_ideas()
            self.assertTrue(mock_tg.called)
            self.assertTrue(mock_bale.called)

    def test_manual_single_idea_send_works(self):
        with app.app.test_client() as client:
            with patch("app._bale_cfg", return_value=("tok", "@chat")),                  patch("app._bale_send", return_value=MagicMock(ok=True)) as mock_send,                  patch("database.is_messenger_posted", return_value=False),                  patch("database.mark_messenger_posted"),                  patch("app._channel_board", return_value={"items": [{
                     "id": "single_idea_1",
                     "title_fa": "تست ارسال تکی ایده دستی",
                     "summary_fa": "توضیحات ایده برای ارسال دستی.",
                     "link": "https://example.com/single"
                 }]}):
                r = client.post("/api/ideas/send-single", json={"id": "single_idea_1", "platform": "bale"})
                self.assertEqual(r.status_code, 200)
                self.assertTrue(mock_send.called)
                args, kwargs = mock_send.call_args
                self.assertNotIn("🔗", args[2])
                self.assertIsNone(kwargs.get("reply_markup"))

    def test_ideas_post_v2_false_uses_old_composer_without_links(self):
        idea = {
            "id": "v1_test",
            "title_fa": "آمریکایی‌ها برای کالاهای لوکس کمتر خرج می‌کنند",
            "summary_fa": (
                "داده‌های سیتی (Citi) نشان می‌دهد خرید کالاهای لوکس در آمریکا کاهش یافته است. "
                "اما بیشترین افت در جواهرات و ساعت دیده می‌شود."
            ),
            "link": "https://example.com/v1",
        }
        with patch.dict(app.CONFIG, {"ideas_post_v2": False}):
            rendered = app._render_content_idea(idea, is_telegram=False)
            self.assertIn("*آمریکایی‌ها برای کالاهای لوکس کمتر خرج می‌کنند*", rendered)
            self.assertIn("🇺🇸 ", rendered)
            self.assertIn("‼️ ", rendered)
            self.assertNotIn("🔗", rendered)
            self.assertNotIn("https://example.com/v1", rendered)

    def test_ideas_post_v2_true_uses_compose_post(self):
        idea = {
            "id": "v2_test",
            "title_fa": "نهنگ بیت‌کوین پس از ۱۳ سال، ۳۴ میلیون دلار BTC جابه‌جا کرد",
            "summary_fa": (
                "یک کیف پول قدیمی که از سال ۲۰۱۳ غیرفعال بود، ۴۱۱.۴۵ بیت‌کوین به ارزش حدود ۳۴ میلیون دلار را به آدرسی جدید منتقل کرد. "
                "این بیت‌کوین‌ها در سال ۲۰۱۳ خریداری شده بودند."
            ),
            "link": "https://example.com/v2",
        }
        with patch.dict(app.CONFIG, {"ideas_post_v2": True}):
            rendered = app._render_content_idea(idea, is_telegram=False)
            self.assertIn("*🔥نهنگ بیت‌کوین", rendered)
            self.assertNotIn("🔗", rendered)


if __name__ == "__main__":
    unittest.main()


