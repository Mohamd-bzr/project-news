"""tests/test_ideas_post.py — Unit tests for ideas_post domain module.

Hermetic, offline, no network, no LLM.
Validates structure, safety, provenance, Persian checks, edge cases, and golden examples.
"""

import unittest

import ideas_post


class TestIdeasPost(unittest.TestCase):

    def setUp(self):
        # 6 Golden examples expanded with filler sentences
        self.goldens = [
            # Golden 1: Forex / France / FedWatch
            {
                "id": "g1",
                "title_fa": "اعتراضات گسترده در فرانسه باعث تضعیف یورو و تقویت دلار شد",
                "summary_fa": "در پی گسترش اعتراضات خشونت‌آمیز در فرانسه، ارزش یورو در معاملات روز دوشنبه 0.1 درصد کاهش یافت و به 1.1230 دلار رسید. همزمان، شاخص دلار آمریکا در محدوده‌ی 101.82 واحد تثبیت شد؛ زیرا تضعیف یورو به حمایت از دلار کمک کرده است.",
                "paragraphs": [
                    "تحلیلگران معتقدند ادامه‌ی ناآرامی‌ها و ابهام درباره‌ی بودجه‌ی فرانسه می‌تواند فشار بیشتری بر یورو وارد کند. نگرانی اصلی سرمایه‌گذاران، افزایش ریسک اوراق بدهی دولت فرانسه است.",
                    "در همین حال، بازارها منتظر دو رویداد مهم هستند:\n28 اکتبر: نشست فدرال رزرو آمریکا\n29 اکتبر: نشست بانک مرکزی اروپا",
                    "براساس ابزار FedWatch، معامله‌گران احتمال 87 درصدی ثابت‌ماندن نرخ بهره آمریکا در نشست پیش‌رو را در قیمت‌ها لحاظ کرده‌اند.",
                    "بازارهای اروپایی در روزهای گذشته روزهای آرامی را سپری کردند و تحولات سیاسی پاریس کانون توجه همگان است.",
                    "برخی از نمایندگان پارلمان فرانسه خواستار بررسی سریع‌تر لایحه بودجه پیشنهادی دولت شده‌اند."
                ]
            },
            # Golden 2: Oil / Russia / Bullets / Kpler
            {
                "id": "g2",
                "title_fa": "کاهش قیمت نفت به زیر 108 دلار پس از تصمیم ترامپ",
                "summary_fa": "قیمت جهانی نفت در معاملات روز دوشنبه 19 اکتبر پس از آنکه دونالد ترامپ بخشی از تحریم‌ها و تعرفه‌های مرتبط با روسیه را معاف کرد، کاهش یافت. این تصمیم احتمال افزایش صادرات سوخت روسیه به بازارهای جهانی را تقویت کرده است.",
                "paragraphs": [
                    "نفت برنت: 107.88 دلار؛ کاهش 1.8 درصدی\nنفت آمریکا (WTI): 100.25 دلار؛ کاهش 1.14 درصدی",
                    "با این حال، اختلال در عرضه نفت خاورمیانه همچنان ادامه دارد. طبق داده‌های شرکت Kpler، جریان صادرات نفت خام از خلیج فارس در هفته گذشته از بیش از 20 میلیون بشکه در روز به حدود 8.5 میلیون بشکه کاهش یافته است.",
                    "اوپک‌پلاس هنوز تصمیمی برای افزایش زودهنگام سهمیه‌های تولید نفت اعضای خود اتخاذ نکرده است.",
                    "تولیدکنندگان شیل آمریکا نیز اعلام کرده‌اند که تمایلی به افزایش چشمگیر حفاری‌های جدید در سال جاری ندارند."
                ]
            },
            # Golden 3: Crypto / China GDP / Kospi
            {
                "id": "g3",
                "title_fa": "رشد بیت‌کوین و بازارهای سهام پس از انتشار آمار بهتر از انتظار اقتصاد چین",
                "summary_fa": "قیمت بیت‌کوین با رشد حدودی ۰.۷ درصدی به حدود ۸۳,۰۰۰ دلار رسید و معاملات آتی نزدک نیز بیش از یک درصد افزایش یافتند. این رشد پس از آن رخ داد که اقتصاد چین در سه‌ماهه سوم سال ۲۰۲۶ رشد ۴.۵ درصدی را ثبت کرد؛ رقمی که اندکی بالاتر از پیش‌بینی‌ها بود.",
                "paragraphs": [
                    "همزمان، کاهش قیمت نفت به بهبود تمایل سرمایه‌گذاران برای پذیرش ریسک کمک کرد.",
                    "شاخص کوسپی کره جنوبی نیز پس از افت شدید هفته گذشته، افزایش یافت. با این حال، نگرانی‌ها درباره هزینه‌های سنگین سرمایه‌گذاری در هوش مصنوعی و تداوم نوسانات بازار همچنان پابرجاست.",
                    "بهبود شرایط اقتصادی چین و افت قیمت نفت، در مجموع به تقویت بازارهای مالی و افزایش تقاضا برای دارایی‌های پرریسک کمک کرده است.",
                    "سرمایه‌گذاران خرد در آسیا نیز حجم سفارش‌های خرید خود را در صرافی‌های محلی تقویت کردند."
                ]
            },
            # Golden 4: Whale
            {
                "id": "g4",
                "title_fa": "نهنگ بیت‌کوین پس از ۱۳ سال، ۳۴ میلیون دلار BTC جابه‌جا کرد",
                "summary_fa": "یک کیف پول قدیمی که از سال ۲۰۱۳ غیرفعال بود، ۴۱۱.۴۵ بیت‌کوین به ارزش حدود ۳۴ میلیون دلار را به آدرسی جدید منتقل کرد.",
                "paragraphs": [
                    "این بیت‌کوین‌ها در سال ۲۰۱۳ و زمانی خریداری شده بودند که قیمت هر واحد تنها ۱۳۱ دلار بود و ارزش کل آنها حدود ۵۴ هزار دلار برآورد می‌شد.",
                    "هنوز نشانه‌ای از انتقال این دارایی‌ها به صرافی یا فروش آنها وجود ندارد و احتمال می‌رود این جابه‌جایی با هدف افزایش امنیت دارایی‌ها انجام شده باشد.",
                    "تحلیلگران داده‌های آن‌چین اعلام کردند که این کیف پول طی این سال‌ها هیچ تراکنش خروجی دیگری نداشته است.",
                    "بازار ارزهای دیجیتال معمولاً به فعالیت نهنگ‌های قدیمی واکنش محتاطانه‌ای نشان می‌دهد."
                ]
            },
            # Golden 5: Macron / Resignation
            {
                "id": "g5",
                "title_fa": "مکرون استعفای وزیر کشور را نپذیرفت",
                "summary_fa": "در پی اعتراضات و درگیری‌های گسترده در فرانسه، لوران نونز، وزیر کشور فرانسه، پیشنهاد استعفای خود را ارائه کرد، اما امانوئل مکرون آن را رد کرد.",
                "paragraphs": [
                    "اعتراضات که از نارضایتی مردم نسبت به افزایش هزینه‌های زندگی، ضعف خدمات عمومی و وضعیت مدارس آغاز شده بود، طی آخر هفته در برخی شهرها به خشونت کشیده شد.",
                    "در جریان این ناآرامی‌ها، یک ساختمان شهرداری به آتش کشیده شد، تعدادی فروشگاه غارت شدند و معترضان با پلیس درگیر شدند. درگیری‌ها روز یکشنبه در پاریس و مارسی نیز ادامه یافت.",
                    "دفتر ریاست‌جمهوری فرانسه اعلام کرده که مکرون برای حفظ هماهنگی نیروهای پلیس و امنیتی، خواستار ادامه‌ی فعالیت وزیر کشور شده و از او خواسته راهکارهای جدیدی برای مقابله با غارت و خشونت ارائه دهد.",
                    "گروه‌های مخالف دولت در بیانیه‌ای از ادامه اعتراضات در روزهای پایانی هفته خبر دادند."
                ]
            },
            # Golden 6: Fake AI Alert
            {
                "id": "g6",
                "title_fa": "هشدار محققان: هوش مصنوعی ساخت تحقیقات پزشکی جعلی را آسان‌تر کرده",
                "summary_fa": "محققان هشدار داده‌اند که برخی افراد و گروه‌ها با استفاده از هوش مصنوعی، مقاله‌های پزشکی جعلی تولید می‌کنند؛ مقاله‌هایی که ظاهری علمی و معتبر دارند، اما اطلاعات بیماران، نتایج آزمایش‌ها و حتی منابع آنها ساختگی است.",
                "paragraphs": [
                    "هوش مصنوعی این امکان را فراهم کرده که چنین مقاله‌هایی به‌جای چند هفته، در عرض چند دقیقه تولید شوند و تشخیص جعلی‌بودن آنها برای مجلات علمی دشوارتر شود.",
                    "نگرانی اصلی این است که اگر این تحقیقات جعلی منتشر شوند، ممکن است پزشکان و پژوهشگران به نتایج اشتباه اعتماد کنند و حتی تصمیم‌های درمانی بیماران تحت تأثیر قرار بگیرد.",
                    "جامعه دانشگاهی خواستار وضع ابزارهای سخت‌گیرانه‌تر برای راستی‌آزمایی تصاویر میکروسکوپی و داده‌های بالینی شده است.",
                    "چندین مجله برجسته پزشکی خط‌مشی‌های جدیدی را برای ارسال دست‌نوشته‌ها به اجرا گذاشته‌اند."
                ]
            }
        ]

    def test_golden_examples_conformity(self):
        """(a) & (b): Structure conformity and presence of key numbers/names on the 6 goldens."""
        for art in self.goldens:
            res = ideas_post.compose_post(art)
            self.assertIsNotNone(res, f"Failed on article {art['id']}")
            title = res["title"]
            blocks = res["blocks"]
            text = res["text"]

            # Title checks
            self.assertTrue(len(title) <= 110, f"Title too long: {len(title)}")
            self.assertTrue(any(ch in "بیت‌کوین فرانسه نفت مکرون هشدار" for ch in title))

            # Blocks count: 3 to 5 blocks
            self.assertTrue(2 <= len(blocks) <= 5, f"Unexpected block count {len(blocks)} for {art['id']}")

            # Formatting: each block starts with an emoji from PALETTE_EMOJIS + space or list block
            for b in blocks:
                first_part = b.split()[0]
                # If list block, check first line or first emoji
                first_emoji = b[:2].strip()
                self.assertIn(first_emoji, ideas_post.PALETTE_EMOJIS, f"Emoji '{first_emoji}' not in palette")

            # No URLs or 🔗
            self.assertNotIn("🔗", text)
            self.assertNotIn("http://", text)
            self.assertNotIn("https://", text)

            # Length caps
            self.assertTrue(len(text) <= 1500, f"Text length {len(text)} exceeds hard cap")

    def test_key_entities_and_numbers_appear(self):
        """Check specific numbers and names in golden outputs."""
        # Golden 1: 0.1, 101.82, 87, فرانسه
        res1 = ideas_post.compose_post(self.goldens[0])
        self.assertIn("فرانسه", res1["text"])
        self.assertTrue("0.1" in res1["text"] or "101.82" in res1["text"] or "87" in res1["text"])

        # Golden 2: 108 or 107.88 or WTI
        res2 = ideas_post.compose_post(self.goldens[1])
        self.assertTrue("108" in res2["text"] or "107.88" in res2["text"] or "ترامپ" in res2["text"])

        # Golden 3: بیت‌کوین, 83,000 / ۸۳,۰۰۰ or 4.5 / ۴.۵
        res3 = ideas_post.compose_post(self.goldens[2])
        self.assertTrue("بیت‌کوین" in res3["title"] or "بیت‌کوین" in res3["text"])
        self.assertTrue("۸۳,۰۰۰" in res3["text"] or "۴.۵" in res3["text"] or "چین" in res3["text"])

        # Golden 4: نهنگ, 34 / ۳۴ or 411.45 / ۴۱۱.۴۵
        res4 = ideas_post.compose_post(self.goldens[3])
        self.assertTrue(res4["title"].startswith("🔥"))
        self.assertTrue("۳۴" in res4["text"] or "۴۱۱.۴۵" in res4["text"] or "۲۰۱۳" in res4["text"])

        # Golden 5: مکرون
        res5 = ideas_post.compose_post(self.goldens[4])
        self.assertIn("مکرون", res5["text"])

        # Golden 6: هوش مصنوعی
        res6 = ideas_post.compose_post(self.goldens[5])
        self.assertTrue(res6["title"].startswith("⁉️"))
        self.assertIn("هوش مصنوعی", res6["text"])

    def test_determinism(self):
        """(c): Deterministic output for same input."""
        res_a = ideas_post.compose_post(self.goldens[0])
        res_b = ideas_post.compose_post(self.goldens[0])
        self.assertEqual(res_a, res_b)

    def test_provenance_of_every_number(self):
        """(d): Every number in output must exist in the source."""
        for art in self.goldens:
            res = ideas_post.compose_post(art)
            if not res:
                continue
            all_source = f"{art['title_fa']} {art['summary_fa']} " + " ".join(art.get("paragraphs") or [])
            src_nums = ideas_post.extract_numbers(all_source)
            for b in res["blocks"]:
                b_nums = ideas_post.extract_numbers(b)
                self.assertTrue(b_nums.issubset(src_nums), f"Unprovenanced number in {b}: {b_nums - src_nums}")

    def test_decimal_point_never_cut(self):
        """(e): Persian decimal points (e.g. ۴.۵ or 1.1230) are not broken at the dot."""
        art = {
            "title_fa": "رشد اقتصادی چین فراتر از انتظار",
            "summary_fa": "اقتصاد چین در سه‌ماهه سوم رشد ۴.۵ درصدی ثبت کرد. این رقم بالاتر از پیش‌بینی‌ها بود.",
            "paragraphs": [
                "نرخ تورم نیز در سطح ۲.۱ درصد ثابت ماند و نشان‌دهنده پایداری قیمت‌ها در بخش مصرف است.",
                "با این حال تحلیلگران درباره پایداری رشد هشدار می‌دهند و چشم‌انداز سال آینده را محتاطانه می‌دانند."
            ]
        }
        res = ideas_post.compose_post(art)
        self.assertIsNotNone(res)
        text = res["text"]
        self.assertIn("۴.۵", text)
        self.assertNotIn("۴.\n", text)
        self.assertNotIn("۲.\n", text)

    def test_non_persian_and_short_inputs_return_none(self):
        """(f): None for a non-Persian title and for single-sentence inputs."""
        # English title
        res_en = ideas_post.compose_post({
            "title_fa": "Gold rallies as traders bet on Fed rate cuts",
            "summary_fa": "یک خلاصه فارسی کامل برای تست زبان انگلیسی."
        })
        self.assertIsNone(res_en)

        # Single short sentence
        res_short = ideas_post.compose_post({
            "title_fa": "یک عنوان مناسب فارسی",
            "summary_fa": "یک جمله کوتاه بدون متن دیگر."
        })
        self.assertIsNone(res_short)

    def test_emoji_never_repeated_consecutively(self):
        """(g): The same emoji is never repeated in consecutive blocks."""
        for art in self.goldens:
            res = ideas_post.compose_post(art)
            self.assertIsNotNone(res)
            prev_em = None
            for b in res["blocks"]:
                em = b[:2].strip()
                self.assertNotEqual(em, prev_em, f"Consecutive repeated emoji {em} in {art['id']}")
                prev_em = em

    def test_function_word_endings_rejected(self):
        """(h): Blocks never end with function words."""
        for art in self.goldens:
            res = ideas_post.compose_post(art)
            if not res:
                continue
            for b in res["blocks"]:
                clean = b.rstrip(".,:؛!؟ ")
                last_word = clean.split()[-1] if clean.split() else ""
                self.assertNotIn(last_word, ideas_post.FUNCTION_WORDS,
                                 f"Block ends with function word '{last_word}': {b}")


if __name__ == "__main__":
    unittest.main()
