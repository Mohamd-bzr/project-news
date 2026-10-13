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
    # two-word phrases never collapse into one word
    assert post_edit("صرافی رمز ارز معتبر است") == "صرافی رمز ارز معتبر است"
    # different words (different families) are never merged
    assert "بازده" in post_edit("بازده بازار افزایش یافت")
    assert post_edit("کتاب جدید") == "کتاب جدید"


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
