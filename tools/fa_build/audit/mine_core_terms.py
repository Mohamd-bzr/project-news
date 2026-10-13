#!/usr/bin/env python3
"""
tools/fa_build/audit/mine_core_terms.py
=======================================
Extracts whole-word occurrences of candidate finance/crypto/oil/tech terms from
articles in .mohmd_news.db (read-only SQLite URI) and aligns them with their Persian
engine translations from title_fa and summary_fa.

Filters:
  - frequency >= 20
  - at least 2 Persian variants each with >= 15% share
Ranks by:
  - frequency * inconsistency (1 - top_variant_share)
Cross-references:
  - data/fa/terms.tsv
  - data/fa/entities.tsv
"""
import csv
import json
import math
import re
import sqlite3
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[3]
DB_PATH = Path("E:/freebuff/.mohmd_news.db")
TERMS_PATH = REPO / "data" / "fa" / "terms.tsv"
ENTITIES_PATH = REPO / "data" / "fa" / "entities.tsv"

FA_LETTER = r"[\u0600-\u06ff\u200c]"

def make_wt(pattern):
    """Whole token regex for Persian pattern"""
    return re.compile(rf"(?<!{FA_LETTER}){pattern}(?!{FA_LETTER})")

# Comprehensive seed list per domain
# (en_canonical, en_regex, domain, context_rule, [(variant_name, [persian_regexes])])
CANDIDATE_DEFINITIONS = [
    # ── 1. Macro & Central Banks ──────────────────────────────────────────
    ("rate cut", r"\brate cuts?\b", "macro", "سیاست پولی و نرخ‌های بهره", [
        ("کاهش نرخ بهره", [r"کاهش نرخ بهره"]),
        ("کاهش نرخ", [r"کاهش نرخ(?! بهره| سود)"]),
        ("کاهش نرخ سود", [r"کاهش نرخ سود"]),
        ("برش نرخ", [r"برش نرخ"]),
    ]),
    ("rate hike", r"\brate hikes?\b", "macro", "سیاست پولی و نرخ‌های بهره", [
        ("افزایش نرخ بهره", [r"افزایش نرخ بهره"]),
        ("افزایش نرخ", [r"افزایش نرخ(?! بهره| سود)"]),
        ("افزایش نرخ سود", [r"افزایش نرخ سود"]),
    ]),
    ("interest rate", r"\binterest rates?\b", "macro", "نرخ بهره بانکی/سیاستی", [
        ("نرخ بهره", [r"نرخ بهره", r"نرخ‌های بهره"]),
        ("نرخ سود", [r"نرخ سود(?! بانکی)"]),
        ("نرخ سود بانکی", [r"نرخ سود بانکی"]),
    ]),
    ("inflation", r"\binflation\b", "macro", "شاخص‌های تورمی و اقتصاد کلان", [
        ("تورم", [r"تورم(?!ی)"]),
        ("تورمی", [r"تورمی"]),
    ]),
    ("central bank", r"\bcentral banks?\b", "macro", "نهاد پولی مرکزی", [
        ("بانک مرکزی", [r"بانک مرکزی", r"بانک‌های مرکزی"]),
    ]),
    ("monetary policy", r"\bmonetary polic(?:y|ies)\b", "macro", "سیاست‌های پولی بانک‌های مرکزی", [
        ("سیاست پولی", [r"سیاست پولی", r"سیاست‌های پولی"]),
        ("خط‌مشی پولی", [r"خط‌مشی پولی", r"خط مشی پولی"]),
    ]),
    ("balance sheet", r"\bbalance sheets?\b", "macro", "ترازنامه مالی شرکت‌ها و بانک مرکزی", [
        ("ترازنامه", [r"ترازنامه", r"ترازنامه‌ها"]),
        ("بیلان", [r"بیلان"]),
        ("صورت مالی", [r"صورت مالی", r"صورت‌های مالی"]),
    ]),
    ("yields", r"\b(?:treasury\s+)?yields?\b", "macro", "بازده اوراق قرضه و خزانه‌داری", [
        ("بازدهی", [r"بازدهی"]),
        ("بازده", [r"بازده(?!ی)"]),
        ("سود اوراق", [r"سود اوراق"]),
        ("نرخ بازده", [r"نرخ بازده"]),
    ]),
    ("recession", r"\brecession(?:ary)?\b", "macro", "رکود اقتصادی", [
        ("رکود", [r"رکود(?! اقتصادی)"]),
        ("رکود اقتصادی", [r"رکود اقتصادی"]),
        ("کسادی", [r"کسادی"]),
    ]),
    ("hawkish", r"\bhawkish\b", "macro", "سیاست پولی انقباضی و لحن سخت‌گیرانه", [
        ("انقباضی", [r"انقباضی"]),
        ("شاهینی", [r"شاهینی"]),
        ("هاوکیش", [r"هاوکیش"]),
    ]),
    ("dovish", r"\bdovish\b", "macro", "سیاست پولی انبساطی و لحن ملایم", [
        ("انبساطی", [r"انبساطی"]),
        ("کبوترانه", [r"کبوترانه"]),
        ("داویش", [r"داویش"]),
    ]),
    ("tightening", r"\btightening\b", "macro", "تشدید انقباض پولی", [
        ("انقباض پولی", [r"انقباض پولی", r"سیاست انقباضی"]),
        ("سخت‌گیرانه", [r"سخت‌گیرانه", r"تشدید"]),
    ]),

    # ── 2. Markets & Equities ─────────────────────────────────────────────
    ("equities", r"\bequities\b", "equities", "بازار سهام و اوراق بهادار", [
        ("سهام", [r"سهام"]),
        ("دارایی‌های سهامی", [r"دارایی‌های سهامی"]),
        ("اوراق بهادار", [r"اوراق بهادار"]),
    ]),
    ("shares", r"\bshares\b", "equities", "سهم‌ها و مالکیت سهام", [
        ("سهام", [r"سهام"]),
        ("سهم‌ها", [r"سهم‌ها", r"سهم"]),
    ]),
    ("dividend", r"\bdividends?\b", "equities", "سود نقدی تقسیمی سهام", [
        ("سود سهام", [r"سود سهام"]),
        ("سود نقدی", [r"سود نقدی"]),
        ("سود تقسیمی", [r"سود تقسیمی"]),
    ]),
    ("valuation", r"\bvaluations?\b", "equities", "ارزش‌گذاری دارایی‌ها و شرکت‌ها", [
        ("ارزش‌گذاری", [r"ارزش‌گذاری", r"ارزش گذاری"]),
        ("ارزیابی", [r"ارزیابی"]),
    ]),
    ("market cap", r"\bmarket caps?\b|\bmarket capitaliz?ations?\b", "equities", "ارزش کل بازار", [
        ("ارزش بازار", [r"ارزش بازار"]),
        ("مارکت کپ", [r"مارکت کپ"]),
        ("سرمایه بازار", [r"سرمایه بازار"]),
    ]),
    ("ipo", r"\bipos?\b|\binitial public offerings?\b", "equities", "عرضه اولیه عمومی سهام", [
        ("عرضه اولیه", [r"عرضه اولیه", r"عرضه اولیه سهام"]),
        ("IPO", [r"\bIPO\b"]),
        ("عرضه عمومی اولیه", [r"عرضه عمومی اولیه"]),
    ]),
    ("buyback", r"\bbuybacks?\b|\bshare buybacks?\b", "equities", "بازخرید سهام توسط شرکت", [
        ("بازخرید سهام", [r"بازخرید سهام", r"بازخرید"]),
        ("خرید مجدد", [r"خرید مجدد"]),
    ]),
    ("rally", r"\brall(?:y|ies)\b", "equities", "صعود و جهش قیمتی پیوسته", [
        ("رالی", [r"رالی"]),
        ("افزایش قیمت", [r"افزایش قیمت", r"رشد قیمت"]),
        ("جهش", [r"جهش"]),
        ("صعود", [r"صعود"]),
    ]),
    ("selloff", r"\bselloffs?\b|\bsell-offs?\b", "equities", "موج فروش سنگین و افت قیمت", [
        ("موج فروش", [r"موج فروش"]),
        ("فروش گسترده", [r"فروش گسترده"]),
        ("ریزش", [r"ریزش"]),
        ("فروش", [r"فروش(?! گسترده| فوری)"]),
    ]),
    ("bull market", r"\bbull markets?\b", "equities", "بازار صعودی و روند گاوی", [
        ("بازار صعودی", [r"بازار صعودی"]),
        ("بازار گاوی", [r"بازار گاوی"]),
    ]),
    ("bear market", r"\bbear markets?\b", "equities", "بازار نزولی و روند خرسی", [
        ("بازار نزولی", [r"بازار نزولی"]),
        ("بازار خرسی", [r"بازار خرسی"]),
    ]),
    ("correction", r"\bcorrections?\b", "equities", "اصلاح قیمتی در روند", [
        ("اصلاح", [r"اصلاح(?! قیمت)"]),
        ("اصلاح قیمت", [r"اصلاح قیمت"]),
        ("تصحیح", [r"تصحیح"]),
    ]),
    ("all-time high", r"\ball-time highs?\b|\bath\b", "equities", "سقف و اوج تاریخی قیمت", [
        ("سقف تاریخی", [r"سقف تاریخی"]),
        ("بالاترین رقم تاریخی", [r"بالاترین رقم تاریخی", r"بالاترین سطح تاریخی"]),
        ("اوج تاریخی", [r"اوج تاریخی"]),
        ("ATH", [r"\bATH\b"]),
    ]),
    ("liquidity", r"\bliquidity\b", "equities", "نقدینگی و جریان وجوه بازار", [
        ("نقدینگی", [r"نقدینگی"]),
        ("نقدشوندگی", [r"نقدشوندگی"]),
    ]),
    ("volatility", r"\bvolatilit(?:y|ies)\b", "equities", "نوسانات و شدت تغییر قیمت", [
        ("نوسان", [r"نوسان(?!‌پذیری)", r"نوسانات"]),
        ("نوسان‌پذیری", [r"نوسان‌پذیری", r"نوسان پذیری"]),
    ]),

    # ── 3. Forex ──────────────────────────────────────────────────────────
    ("forex", r"\bforex\b|\bforeign exchange\b", "forex", "بازار تبادل ارز خارجی", [
        ("فارکس", [r"فارکس"]),
        ("ارز خارجی", [r"ارز خارجی", r"ارزهای خارجی"]),
        ("معاملات ارزی", [r"معاملات ارزی"]),
    ]),
    ("currency", r"\bcurrenc(?:y|ies)\b", "forex", "واحد پول و ارز ملی", [
        ("ارز", [r"ارز(?! خارجی)", r"ارزها"]),
        ("واحد پول", [r"واحد پول"]),
    ]),
    ("dollar index", r"\bdollar index\b|\bdxy\b", "forex", "شاخص برابری دلار آمریکا", [
        ("شاخص دلار", [r"شاخص دلار"]),
        ("شاخص دلار آمریکا", [r"شاخص دلار آمریکا"]),
        ("DXY", [r"\bDXY\b"]),
    ]),
    ("safe haven", r"\bsafe havens?\b", "forex", "دارایی امن در شرایط بحرانی", [
        ("پناهگاه امن", [r"پناهگاه امن"]),
        ("دارایی امن", [r"دارایی امن"]),
        ("مامن امن", [r"مامن امن"]),
    ]),
    ("spread", r"\bspreads?\b", "forex", "اختلاف قیمت خرید و فروش / اسپرد", [
        ("اسپرد", [r"اسپرد"]),
        ("گسترش", [r"گسترش"]),
        ("اختلاف قیمت", [r"اختلاف قیمت"]),
    ]),

    # ── 4. Oil & Energy ───────────────────────────────────────────────────
    ("opec", r"\bopec\b|\bopec\+\b", "oil", "سازمان اوپک و تولیدکنندگان متحد", [
        ("اوپک", [r"اوپک(?! پلاس|\+)"]),
        ("اوپک پلاس", [r"اوپک پلاس", r"اوپک‌پلاس", r"اوپک\+"]),
    ]),
    ("brent", r"\bbrent(?:\s+crude)?\b", "oil", "نفت خام شاخص برنت دریای شمال", [
        ("برنت", [r"برنت(?! نفت)"]),
        ("نفت برنت", [r"نفت برنت"]),
        ("نفت خام برنت", [r"نفت خام برنت"]),
    ]),
    ("wti", r"\bwti(?:\s+crude)?\b", "oil", "نفت خام شاخص وست تگزاس اینترمدیت", [
        ("WTI", [r"\bWTI\b"]),
        ("وست تگزاس", [r"وست تگزاس", r"نفت وست تگزاس"]),
    ]),
    ("crude oil", r"\bcrude(?:\s+oil)?\b", "oil", "نفت خام استخراجی", [
        ("نفت خام", [r"نفت خام"]),
        ("نفت", [r"نفت(?! خام| برنت)"]),
    ]),
    ("refinery", r"\brefiner(?:y|ies)\b", "oil", "تاسیسات پالایش نفت و میعانات", [
        ("پالایشگاه", [r"پالایشگاه", r"پالایشگاه‌ها"]),
        ("تصفیه‌خانه", [r"تصفیه‌خانه"]),
    ]),
    ("natural gas", r"\bnatural gas\b", "oil", "گاز طبیعی و حامل‌های انرژی", [
        ("گاز طبیعی", [r"گاز طبیعی"]),
        ("گاز", [r"گاز(?! طبیعی)"]),
    ]),

    # ── 5. Technology & AI ────────────────────────────────────────────────
    ("chips", r"\bchips?\b", "tech", "تراشه‌ها و مدارهای مجتمع الکترونیکی", [
        ("تراشه‌ها", [r"تراشه‌ها", r"تراشه"]),
        ("چیپ‌ها", [r"چیپ‌ها", r"چیپ"]),
    ]),
    ("guidance", r"\bearnings guidance\b|\bguidance\b", "tech", "پیش‌بینی رسمی عملکرد شرکت توسط مدیران", [
        ("پیش‌بینی سود", [r"پیش‌بینی سود", r"پیش بینی سود"]),
        ("راهنمای سود", [r"راهنمای سود"]),
        ("رهنمود", [r"رهنمود"]),
        ("پیش‌بینی", [r"پیش‌بینی(?! سود)", r"پیش بینی(?! سود)"]),
    ]),
    ("data center", r"\bdata centers?\b", "tech", "مراکز داده و زیرساخت ابری", [
        ("مرکز داده", [r"مرکز داده", r"مراکز داده"]),
        ("دیتاسنتر", [r"دیتاسنتر", r"دیتا سنتر"]),
    ]),

    # ── 6. Technical Analysis & Smart Money ───────────────────────────────
    ("support", r"\bsupport\b", "ta", "سطح حمایت قیمتی در تحلیل تکنیکال", [
        ("حمایت", [r"حمایت(?!ی)"]),
        ("پشتیبانی", [r"پشتیبانی"]),
        ("سطح حمایت", [r"سطح حمایت", r"سطوح حمایت"]),
        ("حمایتی", [r"حمایتی"]),
    ]),
    ("resistance", r"\bresistance\b", "ta", "سطح مقاومت قیمتی در تحلیل تکنیکال", [
        ("مقاومت", [r"مقاومت(?!ی)"]),
        ("سطح مقاومت", [r"سطح مقاومت", r"سطوح مقاومت"]),
        ("مقاومتی", [r"مقاومتی"]),
    ]),
    ("breakout", r"\bbreakouts?\b", "ta", "شکست سطوح کلیدی قیمتی", [
        ("شکست", [r"شکست(?! صعودی)"]),
        ("بریک‌اوت", [r"بریک‌اوت", r"بریک اوت"]),
        ("شکست صعودی", [r"شکست صعودی"]),
    ]),
    ("pullback", r"\bpullbacks?\b", "ta", "بازگشت اصلاحی کوتاه‌مدت به سطح شکسته شده", [
        ("پولبک", [r"پولبک", r"پول بک"]),
        ("عقب‌نشینی", [r"عقب‌نشینی"]),
        ("اصلاح", [r"اصلاح"]),
    ]),
    ("trendline", r"\btrendlines?\b|\btrend lines?\b", "ta", "خط رسم شده اتصال اوج‌ها یا کف‌ها", [
        ("خط روند", [r"خط روند", r"خطوط روند"]),
        ("ترندلاین", [r"ترندلاین", r"ترند لاین"]),
    ]),
    ("divergence", r"\bdivergences?\b", "ta", "عدم تطابق جهت نمودار قیمت و اندیکاتور", [
        ("واگرایی", [r"واگرایی"]),
        ("اختلاف روند", [r"اختلاف"]),
    ]),
    ("moving average", r"\bmoving averages?\b|\bma\b", "ta", "اندیکاتور میانگین متحرک قیمت", [
        ("میانگین متحرک", [r"میانگین متحرک", r"میانگین‌های متحرک"]),
        ("مووینگ اوریج", [r"مووینگ اوریج"]),
    ]),
    ("rsi", r"\brsi\b", "ta", "اندیکاتور شاخص قدرت نسبی", [
        ("RSI", [r"\bRSI\b"]),
        ("شاخص قدرت نسبی", [r"شاخص قدرت نسبی"]),
    ]),
    ("macd", r"\bmacd\b", "ta", "اندیکاتور میانگین متحرک همگرا/واگرا", [
        ("MACD", [r"\bMACD\b"]),
        ("مکدی", [r"مکدی"]),
    ]),
    ("fibonacci", r"\bfibonacci\b", "ta", "نسبت‌های اصلاحی و گسترشی فیبوناچی", [
        ("فیبوناچی", [r"فیبوناچی"]),
        ("سطوح فیبوناچی", [r"سطوح فیبوناچی"]),
    ]),
    ("oversold", r"\boversold\b", "ta", "ناحیه اشباع فروش در اندیکاتورها", [
        ("فروش بیش از حد", [r"فروش بیش از حد"]),
        ("اشباع فروش", [r"اشباع فروش"]),
        ("اورسولد", [r"اورسولد"]),
    ]),

    # ── 7. Fundamental Analysis ───────────────────────────────────────────
    ("earnings", r"\bearnings\b", "fa", "گزارش سود و عملکرد مالی شرکت‌ها", [
        ("درآمد", [r"درآمد"]),
        ("سود", [r"سود(?! سهام)"]),
        ("عایدی", [r"عایدی"]),
    ]),
    ("revenue", r"\brevenues?\b", "fa", "کل درآمد حاصل از فروش عملیاتی", [
        ("درآمد", [r"درآمد(?!ها)"]),
        ("درآمدها", [r"درآمدها"]),
        ("فروش", [r"فروش"]),
    ]),
    ("cash flow", r"\bcash flows?\b", "fa", "جریان ورود و خروج نقدینگی شرکت", [
        ("جریان نقدی", [r"جریان نقدی"]),
        ("جریان های نقدی", [r"جریان های نقدی", r"جریان‌های نقدی"]),
        ("گردش وجوه نقد", [r"گردش وجوه نقد"]),
    ]),

    # ── 8. Crypto ─────────────────────────────────────────────────────────
    ("etf", r"\betfs?\b", "crypto", "صندوق سرمایه‌گذاری قابل معامله در بورس", [
        ("ETF", [r"\bETF\b", r"ETFها", r"ETF های"]),
        ("صندوق قابل معامله", [r"صندوق قابل معامله", r"صندوق‌های قابل معامله"]),
        ("صندوق ETF", [r"صندوق ETF", r"صندوق‌های ETF"]),
    ]),
    ("stablecoin", r"\bstablecoins?\b", "crypto", "ارز دیجیتال با ارزش پایدار/وابسته به ارز ملی", [
        ("استیبل کوین", [r"استیبل کوین(?!‌ها)"]),
        ("استیبل‌کوین", [r"استیبل‌کوین"]),
        ("ارز باثبات", [r"ارز باثبات", r"ارز دیجیتال باثبات"]),
    ]),
    ("wallet", r"\bwallets?\b", "crypto", "کیف پول ذخیره‌سازی دارایی دیجیتال", [
        ("کیف پول", [r"کیف پول", r"کیف‌پول"]),
        ("والت", [r"والت"]),
    ]),
    ("staking", r"\bstaking\b", "crypto", "سپرده‌گذاری دارایی در پروتکل اثبات سهام", [
        ("سرمایه‌گذاری", [r"سرمایه‌گذاری", r"سرمایه گذاری"]),
        ("استیکینگ", [r"استیکینگ"]),
        ("سهامداری", [r"سهامداری"]),
        ("سپرده‌گذاری", [r"سپرده‌گذاری", r"سپرده گذاری"]),
    ]),
    ("custody", r"\bcustod(?:y|ian|ians)\b", "crypto", "خدمات نگهداری و امانتداری نهادی دارایی", [
        ("حضانت", [r"حضانت"]),
        ("نگهداری", [r"نگهداری"]),
        ("کاستودی", [r"کاستودی"]),
        ("Custody", [r"\bCustody\b"]),
    ]),
    ("ledger", r"\bledgers?\b", "crypto", "دفتر کل توزیع‌شده یا برند کیف پول سخت‌افزاری", [
        ("Ledger", [r"\bLedger\b"]),
        ("لجر", [r"لجر"]),
        ("دفتر کل", [r"دفتر کل"]),
    ]),
    ("defi", r"\bdefi\b|\bdecentralized finance\b", "crypto", "امور مالی غیرمتمرکز مبتنی بر قرارداد هوشمند", [
        ("DeFi", [r"\bDeFi\b"]),
        ("دیفای", [r"دیفای", r"دی‌فای"]),
        ("امور مالی غیرمتمرکز", [r"امور مالی غیرمتمرکز"]),
    ]),
    ("halving", r"\bhalvings?\b", "crypto", "رویداد نصف شدن پاداش بلاک در بیت‌کوین", [
        ("نصف شدن", [r"نصف شدن(?! پاداش)", r"نصف شدن پاداش"]),
        ("هاوینگ", [r"هاوینگ"]),
        ("هالوینگ", [r"هالوینگ"]),
    ]),
    ("node", r"\bnodes?\b", "crypto", "رایانه‌های متصل به شبکه بلاک‌چین", [
        ("گره", [r"گره", r"گره‌ها"]),
        ("نود", [r"نود", r"نودها"]),
    ]),
]

def load_existing():
    terms_set = set()
    if TERMS_PATH.exists():
        with open(TERMS_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                en = (row.get("en") or "").strip().lower()
                if en:
                    terms_set.add(en)

    entities_set = set()
    if ENTITIES_PATH.exists():
        with open(ENTITIES_PATH, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                en = (row.get("en") or "").strip().lower()
                if en:
                    entities_set.add(en)

    return terms_set, entities_set

def mine_terms():
    terms_set, entities_set = load_existing()

    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    cur = con.cursor()
    articles = cur.execute("SELECT title, title_fa, summary, summary_fa FROM articles").fetchall()
    con.close()

    print(f"Loaded {len(articles)} articles from read-only SQLite database.")

    # Compile regexes
    compiled = []
    for en_key, en_pat, domain, ctx_rule, variants in CANDIDATE_DEFINITIONS:
        c_en = re.compile(en_pat, re.IGNORECASE)
        c_vars = [(var_name, [re.compile(p) for p in pats]) for var_name, pats in variants]
        compiled.append((en_key, c_en, domain, ctx_rule, c_vars))

    stats = defaultdict(lambda: {"freq": 0, "variants": Counter(), "unmatched": 0})

    for title, title_fa, summary, summary_fa in articles:
        pairs = []
        if title and title_fa:
            pairs.append((title, title_fa))
        if summary and summary_fa:
            pairs.append((summary, summary_fa))

        for en_text, fa_text in pairs:
            for en_key, c_en, domain, ctx_rule, c_vars in compiled:
                m = c_en.findall(en_text)
                if not m:
                    continue
                cnt = len(m)
                stats[en_key]["freq"] += cnt

                matched = None
                for var_name, pats in c_vars:
                    if any(p.search(fa_text) for p in pats):
                        matched = var_name
                        break
                if matched:
                    stats[en_key]["variants"][matched] += cnt
                else:
                    stats[en_key]["unmatched"] += cnt

    results = []
    for en_key, c_en, domain, ctx_rule, c_vars in compiled:
        st = stats[en_key]
        freq = st["freq"]
        if freq < 20:
            continue

        var_counts = st["variants"]
        total_classified = sum(var_counts.values())
        if total_classified < 5:
            continue

        shares = {var: c / total_classified for var, c in var_counts.items()}
        # Criteria: at least 2 variants with >= 15% share
        qualifying = [v for v, s in shares.items() if s >= 0.15]
        if len(qualifying) < 2:
            continue

        top_share = max(shares.values()) if shares else 0
        inconsistency = 1.0 - top_share
        rank_score = freq * inconsistency

        sorted_vars = sorted(shares.items(), key=lambda x: -x[1])
        recommended = sorted_vars[0][0]

        # Recommended curation: for crypto terms with bad machine translations,
        # choose the standard technical term:
        if en_key == "staking":
            recommended = "استیکینگ"
        elif en_key == "rate cut":
            recommended = "کاهش نرخ بهره"
        elif en_key == "rate hike":
            recommended = "افزایش نرخ بهره"
        elif en_key == "halving":
            recommended = "هاوینگ"
        elif en_key == "custody":
            recommended = "حضانت"
        elif en_key == "spread":
            recommended = "اسپرد"
        elif en_key == "support":
            recommended = "حمایت"
        elif en_key == "bull market":
            recommended = "بازار صعودی"
        elif en_key == "bear market":
            recommended = "بازار نزولی"
        elif en_key == "brent":
            recommended = "نفت برنت"
        elif en_key == "node":
            recommended = "نود"
        elif en_key == "oversold":
            recommended = "اشباع فروش"
        elif en_key == "yields":
            recommended = "بازدهی"
        elif en_key == "ipo":
            recommended = "عرضه اولیه"
        elif en_key == "etf":
            recommended = "صندوق ETF"
        elif en_key == "stablecoin":
            recommended = "استیبل‌کوین"
        elif en_key == "breakout":
            recommended = "شکست صعودی"
        elif en_key == "pullback":
            recommended = "پولبک"
        elif en_key == "all-time high":
            recommended = "سقف تاریخی"
        elif en_key == "guidance":
            recommended = "پیش‌بینی سود"
        elif en_key == "tightening":
            recommended = "انقباض پولی"
        elif en_key == "data center":
            recommended = "مرکز داده"

        results.append({
            "en": en_key,
            "domain": domain,
            "context_rule": ctx_rule,
            "freq": freq,
            "classified": total_classified,
            "variants": sorted_vars,
            "qualifying": qualifying,
            "recommended": recommended,
            "rank_score": rank_score,
            "in_terms": en_key in terms_set,
            "in_entities": en_key in entities_set,
        })

    results.sort(key=lambda x: -x["rank_score"])

    # Export to data/fa/core_terms_candidates.json
    out_candidates = []
    for idx, r in enumerate(results, 1):
        bad_vars = [v for v, _ in r["variants"] if v != r["recommended"]]
        out_candidates.append({
            "id": idx,
            "en": r["en"],
            "domain": r["domain"],
            "freq": r["freq"],
            "classified": r["classified"],
            "score": round(r["rank_score"], 1),
            "variants": [{"term": v, "share": round(s, 3)} for v, s in r["variants"]],
            "recommended": r["recommended"],
            "context_rule": r["context_rule"],
            "bad_variants": bad_vars,
            "in_terms": r["in_terms"],
            "in_entities": r["in_entities"],
        })

    json_path = REPO / "data" / "fa" / "core_terms_candidates.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out_candidates, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(out_candidates)} candidate cards to {json_path}")

    return results

if __name__ == "__main__":
    res = mine_terms()
    print(f"\nFinal shortlist of candidate core terms: {len(res)} items.\n")
    for i, r in enumerate(res, 1):
        vars_str = " | ".join([f"{v}: {s:.1%}" for v, s in r["variants"]])
        col = " [terms.tsv]" if r["in_terms"] else ""
        col += " [entities.tsv]" if r["in_entities"] else ""
        print(f"Card {i:2d}: {r['en']} ({r['domain']}, freq={r['freq']}, score={r['rank_score']:.1f}){col}")
        print(f"   Variants: {vars_str}")
        print(f"   Recommended: {r['recommended']}")
        print(f"   Context: {r['context_rule']}\n")
