"""Phase 2: fa_lexicon + fa_postedit (deterministic, offline, no network).

Covers the contract that Phase 3 will rely on: pure functions, idempotency,
URL/e-mail safety, unambiguous-only Latin replacement, and the load budgets.
"""
import time
import tracemalloc

import fa_lexicon
import fa_postedit
from fa_lexicon import Lexicon, load_wordfreq, lexicon
from fa_postedit import post_edit

SAMPLES = [
    "قیمت بیت کوین امروز 3.5 درصد کاهش یافت و به 84000 دلار رسید.",
    "فدرال رزرو نرخ بهره را تغییر نداد؛ Jerome Powell گفت تورم کنترل شده است.",
    "بازار سهام نزدک در سال 2026 رشد کرد (https://example.com/q?a=1&b=2)",
    "کتاب های جدید وارد بازار شدند و می توانند فروش خوبی داشته باشند.",
    "بزرگ ترین صرافی رمزارز، Ethereum و Solana را فهرست کرد.",
    "قیمت طلا با وجود تورم افزایش یافت؛ به گفتهٔ تحلیل‌گران، روند ادامه دارد.",
    "فایل را از www.example.com/2026/file-2.html دانلود کنید یا به info@example.com ایمیل بزنید.",
]


def test_lexicon_loads_under_budget():
    lex = Lexicon()
    tracemalloc.start()
    t0 = time.perf_counter()
    table = lex.table
    elapsed = time.perf_counter() - t0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(table) > 3000          # entities + terms bundle is committed
    assert elapsed < 2.0, f"cold load {elapsed:.2f}s > 2s budget"
    assert peak < 60 * 1024 * 1024, f"peak {peak/1e6:.0f}MB > budget"


def test_lexicon_known_unambiguous_lookups():
    lex = lexicon()
    assert lex.fa_for("inflation") == "تورم"
    assert lex.fa_for("central bank") == "بانک مرکزی"
    # bitcoin has two TYPOGRAPHY variants only -> one family -> ZWNJ form
    assert lex.fa_for("bitcoin") == "بیت\u200cکوین"


def test_lexicon_missing_and_ambiguous_are_none():
    lex = lexicon()
    assert lex.fa_for("zzz-not-a-term") is None
    # 'bar' has genuinely different renderings (بار / نوار شمعی) -> None
    assert lex.fa_for("bar") is None


def test_wordfreq_thresholded_slice():
    wf = load_wordfreq(min_total=1000)
    assert wf and "تورم" in wf
    wiki, feed, total = wf["تورم"]
    assert total >= 1000 and feed > 0


def test_arabic_letters_and_tatweel_fixed():
    assert post_edit("كوين و يورو") == "کوین و یورو"
    assert post_edit("بـازار") == "بازار"


def test_zwnj_mi_ha_tar():
    assert post_edit("او می رود") == "او می\u200cرود"
    assert post_edit("او نمی رود") == "او نمی\u200cرود"
    assert post_edit("کتاب ها") == "کتاب\u200cها"
    assert post_edit("کتاب هایش") == "کتاب\u200cهایش"
    assert post_edit("بزرگ تر") == "بزرگ\u200cتر"
    # lexicalized comparatives join WITHOUT ZWNJ
    assert post_edit("بیش تر") == "بیشتر"
    assert post_edit("کم تر") == "کمتر"
    # real words starting with ها are untouched
    assert post_edit("گفت هاشمی") == "گفت هاشمی"


def test_digits_converted_but_urls_protected():
    s = post_edit("سال 2026 و 3.5 درصد")
    assert "۲۰۲۶" in s and "۳.۵" in s and "2026" not in s
    url = "https://example.com/2026/q?a=1&b=2"
    out = post_edit(f"لینک {url} را باز کنید")
    assert url in out                       # URL byte-identical
    mail = "info@example.com"
    assert mail in post_edit(f"به {mail} بنویسید 2 بار")


def test_latin_residue_unambiguous_only():
    out = post_edit("قیمت Ethereum افزایش یافت")
    assert "اتریوم" in out and "Ethereum" not in out
    # ticker-shaped ALL-CAPS <=5 chars is never replaced
    assert "MSTR" in post_edit("سهام MSTR افت کرد")
    # unknown token is kept as-is (never fabricated)
    assert "Qwertyxyz" in post_edit("برند Qwertyxyz معرفی شد")


def test_post_edit_is_idempotent():
    for s in SAMPLES:
        once = post_edit(s)
        twice = post_edit(once)
        assert once == twice, f"not idempotent: {s!r}\n1: {once!r}\n2: {twice!r}"


def test_fa_spelling_variants_canonicalized():
    assert post_edit("قیمت بیت کوین بالا رفت") == "قیمت بیت\u200cکوین بالا رفت"
    # the NO-SEPARATOR joined spelling is NOT rewritten: merging/splitting
    # words is a REVIEW.md decision; only space<->ZWNJ is pure typography
    assert post_edit("قیمت بیتکوین بالا رفت") == "قیمت بیتکوین بالا رفت"
    # two-word phrases never collapse into one word without English source (item 1a)
    assert post_edit("صرافی رمز ارز معتبر است") == "صرافی رمز ارز معتبر است"
    assert post_edit("بازار رمز ارزها نوسان دارد") == "بازار رمز ارزها نوسان دارد"
    # different words (different families) are never merged
    assert "بازده" in post_edit("بازده بازار افزایش یافت")
    assert post_edit("کتاب جدید") == "کتاب جدید"


def test_acronym_and_digit_inconsistencies_pinned():
    # Item 1b: All-caps acronyms <= 5 chars are NOT replaced from Latin residue
    assert post_edit("پرونده با SEC در جریان است") == "پرونده با SEC در جریان است"
    assert post_edit("بیانیه FED منتشر شد") == "بیانیه FED منتشر شد"
    assert post_edit("تصمیم ECB اعلام شد") == "تصمیم ECB اعلام شد"
    # NASDAQ is vetted in entities.tsv and allowed to replace
    assert post_edit("نماد در (NASDAQ: AAPL)") == "نماد در (نزدک: AAPL)"

    # Item 1c: Persian digits are never converted to Latin
    assert post_edit("نرخ ۳۵ درصد اعلام شد") == "نرخ ۳۵ درصد اعلام شد"
    assert post_edit("ساعت ۱۷:۳۵ به وقت تهران") == "ساعت ۱۷:۳۵ به وقت تهران"
    assert post_edit("شماره ۳۵") == "شماره ۳۵"


def test_none_and_empty_passthrough():
    assert post_edit(None) is None
    assert post_edit("") == ""


def test_real_corpus_titles_converge():
    """Engine-shaped sentences end up fully Persian and stable."""
    s = ("Bitcoin price today is down 3.5% and trading at 84000 USD; "
         "https://example.org/a/2026 traders say می تواند رشد کند "
         "و کتاب ها هم فروش رفتند.")
    out = post_edit(s)
    assert "https://example.org/a/2026" in out
    assert "۳.۵" in out and "۸۴۰۰۰" in out
    assert "می\u200cتواند" in out and "کتاب\u200cها" in out
    assert post_edit(out) == out


def test_latin_residue_9_defect_regressions():
    """Regression tests for the 9 examples where general word replacements were wrong."""
    # 1. Gold -> زر in fund/product name prevented
    assert "Gold" in post_edit("یادداشت‌های مرتبط با VanEck Gold Miners ETF منتشر شد")
    assert "زر" not in post_edit("یادداشت‌های مرتبط با VanEck Gold Miners ETF منتشر شد")

    # 2. Gold -> زر and ETF expansion prevented
    s2 = post_edit("معاملات با Physical Gold Etf (AAAU)")
    assert "Physical Gold Etf" in s2
    assert "صندوق قابل معامله در بورس(ETF)" not in s2
    assert "زر" not in s2

    # 3. Strike -> اصابت prevented in capitalized run
    s3 = post_edit("متن صورتجلسه Fed Minutes Strike Hawkish منتشر شد")
    assert "Strike" in s3
    assert "اصابت" not in s3

    # 4. Premium -> حق بیمه prevented in fund/product name
    s4 = post_edit("گزارش سود صندوق Equity Premium Income ETF")
    assert "Premium" in s4
    assert "حق بیمه" not in s4

    # 5. 1win Markets mangled brand prevented (win -> وینک avoided)
    s5 = post_edit("افزایش قیمت در پلتفرم 1win Markets گزارش شد")
    assert "win" in s5
    assert "وینک" not in s5

    # 6. The -> دِ prevented in publication name
    s6 = post_edit("گزارش منتشر شده در The Coin Republic")
    assert "The Coin Republic" in s6
    assert "دِ" not in s6

    # 7. Top -> تاپ prevented in fund name
    s7 = post_edit("سود سهام Roundhill Top WeeklyPay ETF اعلام شد")
    assert "Top" in s7
    assert "تاپ" not in s7

    # 8. Fetch.ai dotted brand rewriting prevented
    s8 = post_edit("هک پلتفرم‌های Fetch.ai and NuNet گزارش شد")
    assert "Fetch.ai" in s8
    assert "فچ ای‌آی" not in s8

    # 9. NEAR -> نیر پروتکل word addition prevented in ETF span
    s9 = post_edit("تأیید درخواست Bitwise NEAR ETF در بورس")
    assert "Bitwise NEAR ETF" in s9
    assert "نیر پروتکل" not in s9


def test_latin_residue_vetted_entities_and_projects_work():
    """Good proper name replacements continue to happen."""
    assert post_edit("پروژه Ripple") == "پروژه ریپل"
    assert post_edit("شبکه Cardano") == "شبکه کاردانو"
    assert post_edit("قیمت Solana") == "قیمت سولانا"
    assert post_edit("ارز Ethereum") == "ارز اتریوم"
    assert post_edit("شبکه Bitcoin") == "شبکه بیت\u200cکوین"
    assert post_edit("سهام Citigroup") == "سهام سیتی\u200cگروپ"
    assert post_edit("بانک Standard Chartered") == "بانک استاندارد چارترد"


def test_protected_latin_span_entity_replacement():
    """Item 4: Multi-word entities from entities.tsv are replaced inside protected spans."""
    # Standard Chartered Back OKX -> Standard Chartered is an entity (len > 1), Back OKX stays Latin
    assert post_edit("Standard Chartered Back OKX") == "استاندارد چارترد Back OKX"
    # VanEck Gold Miners ETF -> VanEck not in entities.tsv, single words (Gold, Miners) not replaced
    assert post_edit("VanEck Gold Miners ETF") == "VanEck Gold Miners ETF"
    # Goldman Sachs Physical Gold Etf (AAAU) -> Goldman Sachs is replaced, remainder stays Latin
    assert post_edit("Goldman Sachs Physical Gold Etf (AAAU)") == "گلدمن ساکس Physical Gold Etf (AAAU)"


def test_enforce_terms_all_rules():
    """Item 3: Pin all owner decisions (D1-D5 positive/negative, approved cards, review rules)."""
    from fa_postedit import enforce_terms, apply_custody_review, apply_yield_review

    # D1: cryptocurrency / cryptocurrencies / crypto / digital assets
    assert enforce_terms("قیمت رمزارز کاهش یافت", "cryptocurrency price dropped") == "قیمت ارز دیجیتال کاهش یافت"
    assert enforce_terms("قیمت رمز ارز کاهش یافت", "crypto price dropped") == "قیمت ارز دیجیتال کاهش یافت"
    assert enforce_terms("بازار رمزارزها صعودی شد", "cryptocurrencies market surged") == "بازار ارزهای دیجیتال صعودی شد"
    assert enforce_terms("بازار رمز ارزها صعودی شد", "digital assets market surged") == "بازار ارزهای دیجیتال صعودی شد"
    assert enforce_terms("ارزهای رمزنگاری شده محبوب", "popular digital asset options") == "ارزهای دیجیتال محبوب"
    assert enforce_terms("معرفی رمزارزی جدید", "launching a new crypto") == "معرفی ارز دیجیتالی جدید"
    # D1 کریپتو preserved: never rewritten to ارز دیجیتال
    assert enforce_terms("آزمایشگاه کریپتو برای آینده", "Morgan Stanley builds crypto lab") == "آزمایشگاه کریپتو برای آینده"
    assert post_edit("سرمایه‌گذاری در کریپتو", source_en="investing in crypto") == "سرمایه‌گذاری در کریپتو"
    # D1 negative: without crypto/cryptocurrency/digital asset in source, no replacement
    assert enforce_terms("بازار رمزارزها", "stock market update") == "بازار رمزارزها"

    # D2: bull / bear market
    assert enforce_terms("ورود به بازار گاوی", "entering a bull market") == "ورود به بازار صعودی"
    assert enforce_terms("تحلیل بازارهای گاوی", "analysis of bull markets") == "تحلیل بازارهای صعودی"
    assert enforce_terms("آغاز بازار خرسی", "start of a bear market") == "آغاز بازار نزولی"
    assert enforce_terms("تحلیل بازارهای خرسی", "bear markets history") == "تحلیل بازارهای نزولی"

    # D5: coin names (ZWNJ, never space)
    assert enforce_terms("خرید بیت کوین و دوج کوین", "buying Bitcoin and Dogecoin") == "خرید بیت‌کوین و دوج‌کوین"
    assert enforce_terms("قیمت لایت کوین و استیبل کوین", "Litecoin and stablecoin prices") == "قیمت لایت‌کوین و استیبل‌کوین"
    # D5 negative: generic word + کوین must NOT be replaced
    assert enforce_terms("این کوین در حال رشد است", "this coin is growing") == "این کوین در حال رشد است"
    assert enforce_terms("خرید یک کوین جدید", "buying a coin") == "خرید یک کوین جدید"
    assert enforce_terms("آن کوین و هر کوین دیگر", "that coin and every other coin") == "آن کوین و هر کوین دیگر"

    # Support (TA context vs non-TA)
    ta_src = "Bitcoin breaks key support level on price chart"
    assert enforce_terms("شکست سطح پشتیبانی کلیدی", ta_src) == "شکست سطح حمایت کلیدی"
    non_ta_src = "Contact our customer support team 24/7"
    assert enforce_terms("تماس با تیم پشتیبانی مشتری", non_ta_src) == "تماس با تیم پشتیبانی مشتری"

    # Staking (سهامداری only, never سرمایه‌گذاری)
    staking_src = "Ethereum staking rewards increase"
    assert enforce_terms("پاداش سهامداری اتریوم افزایش یافت", staking_src) == "پاداش استیکینگ اتریوم افزایش یافت"
    assert enforce_terms("سرمایه‌گذاری در اتریوم سودآور است", staking_src) == "سرمایه‌گذاری در اتریوم سودآور است"

    # Oversold
    oversold_src = "RSI indicator signals oversold territory"
    assert enforce_terms("اندیکاتور در منطقه فروش بیش از حد است", oversold_src) == "اندیکاتور در منطقه اشباع فروش است"

    # D3 Review (custody)
    # Positive case: حضانت in financial/crypto context -> نگهداری امن
    assert apply_custody_review("خدمات حضانت دارایی دیجیتال", "digital asset custody service") == "خدمات نگهداری امن دارایی دیجیتال"
    assert apply_custody_review("حضانت نهادی بیت‌کوین", "institutional bitcoin custody solutions") == "نگهداری امن نهادی بیت‌کوین"
    # Negative cases: child custody, in custody (police) -> untouched
    assert apply_custody_review("دعوای حضانت فرزند", "child custody hearing") == "دعوای حضانت فرزند"
    assert apply_custody_review("متهم در بازداشت و نگهداری پلیس است", "suspect remains in custody at police station") == "متهم در بازداشت و نگهداری پلیس است"
    # Standalone نگهداری and self-custody wallet: standalone نگهداری must NOT be replaced
    assert apply_custody_review("پلتفرم نگهداری بیت کوین", "bitcoin custody platform") == "پلتفرم نگهداری بیت کوین"
    assert apply_custody_review("کیف پول خود نگهداری ارز دیجیتال", "self-custody crypto wallet") == "کیف پول خود نگهداری ارز دیجیتال"

    # D4 Review (yields)
    assert apply_yield_review("بازدهی شرکت عالی بود", "the business performed well") == "بازدهی شرکت عالی بود"
    assert apply_yield_review("کاهش بازدهی اوراق ۱۰ ساله خزانه‌داری", "10-year treasury yields decline") == "کاهش بازده اوراق ۱۰ ساله خزانه‌داری"
    assert enforce_terms("افزایش بازدهی اوراق قرضه خزانه‌داری", "Treasury bond yields rise") == "افزایش بازده اوراق قرضه خزانه‌داری"
    assert enforce_terms("بازدهی سهام شرکت خوب بود", "corporate performance was strong") == "بازدهی سهام شرکت خوب بود"


    # Native Persian (source_en is None): NEVER changes anything
    assert enforce_terms("رمزارزها و بازار گاوی", None) == "رمزارزها و بازار گاوی"
    assert post_edit("رمزارزها و بازار گاوی", source_en=None) == "رمزارزها و بازار گاوی"

    # Idempotency
    t = "بازار رمزارزها و بازار گاوی و بیت کوین"
    s = "cryptocurrencies and bull market with Bitcoin"
    res1 = enforce_terms(t, s)
    res2 = enforce_terms(res1, s)
    assert res1 == res2
    assert res1 == "بازار ارزهای دیجیتال و بازار صعودی و بیت‌کوین"


def test_fa_eval_sample_size_verdict_gate():
    """Item 1: Verdict gate requires >= 30 human opinion rows."""
    from tools.fa_eval import evaluate_opinion_verdict

    # Case 1: < 30 rows -> INSUFFICIENT DATA
    dummy_rows = [{"pref": "post_ok"}] * 29
    verdict, reasons = evaluate_opinion_verdict(dummy_rows, raw_better_rate=0.0, chrf_post=80.0, chrf_raw=70.0)
    assert verdict == "INSUFFICIENT DATA - no verdict"
    assert "30 required" in reasons[0]

    # Case 2: >= 30 rows and passes conditions -> ENABLE
    valid_rows = [{"pref": "post_ok"}] * 30
    verdict, reasons = evaluate_opinion_verdict(valid_rows, raw_better_rate=0.05, chrf_post=80.0, chrf_raw=70.0)
    assert verdict == "ENABLE"

    # Case 3: >= 30 rows but fails raw_better threshold -> DO NOT ENABLE
    verdict, reasons = evaluate_opinion_verdict(valid_rows, raw_better_rate=0.15, chrf_post=80.0, chrf_raw=70.0)
    assert verdict == "DO NOT ENABLE"


