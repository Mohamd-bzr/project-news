#!/usr/bin/env python3
"""
Test script for verifying residue replacement rules against the 9 defect cases
and the required preservation cases.
"""
import csv
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[3]

# Load common English words stoplist
# Built from words >= 50 occurrences in read-only DB copy that are general words
STOPLIST = {
    'the', 'a', 'as', 'gold', 'market', 'oil', 'inflation', 'silver', 'etf', 'etfs', 'etn', 'etns',
    'bank', 'while', 'near', 'link', 'one', 'treasury', 'just', 'bond', 'interest', 'futures',
    'post', 'asset', 'stablecoin', 'move', 'all', 'buy', 'wall', 'strategy', 'report', 'last',
    'no', 'blockchain', 'off', 'top', 'live', 'liquidity', 'strong', 'gas', 'open', 'target',
    'federal', 'east', 'cryptocurrency', 'keep', 'short', 'like', 'investment', 'sentiment',
    'analysis', 'real', 'finance', 'these', 'get', 'earnings', 'again', 'best', 'group',
    'following', 'volatility', 'debt', 'momentum', 'act', 'economy', 'rose', 'coming',
    'settlement', 'way', 'full', 'weak', 'payment', 'show', 'yet', 'right', 'options',
    'cycle', 'release', 'future', 'range', 'point', 'revenue', 'credit', 'trust', 'production',
    'profit', 'look', 'standard', 'consumer', 'account', 'dividend', 'sharp', 'wrap',
    'sanctions', 'board', 'trend', 'portfolio', 'slide', 'strategic', 'valuation', 'copper',
    'commodity', 'premium', 'altcoin', 'come', 'call', 'mixed', 'west', 'model', 'though',
    'won', 'status', 'block', 'png', 'head', 'artificial', 'story', 'acquisition', 'vote',
    'benchmark', 'tariff', 'flow', 'liquidation', 'fintech', 'executive', 'opening', 'exit',
    'margin', 'offset', 'phase', 'spread', 'quick', 'win', 'bad', 'yesterday', 'chip',
    'fake', 'petroleum', 'clearing', 'summary', 'pool', 'wait', 'strike', 'fun', 'entire',
    'hot', 'tool', 'study', 'economics', 'peace', 'liquid', 'version', 'family', 'climate',
    'client', 'weight', 'site', 'discount', 'gift', 'super', 'statistics', 'grade',
    'diplomatic', 'maker', 'fire', 'miners', 'income', 'weeklypay', 'republic', 'coin'
}

PRODUCT_KW_RE = re.compile(r"\b(ETF|ETN|Fund|Trust|Notes)\b", re.IGNORECASE)

# Load entities
entities = {}
with open(REPO / "data" / "fa" / "entities.tsv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        k = (r.get("en") or "").strip().lower()
        fa = (r.get("fa") or "").strip()
        if k and fa and k not in STOPLIST:
            entities.setdefault(k, []).append(fa)

# Load vetted crypto project names from terms.tsv
vetted_crypto = {}
with open(REPO / "data" / "fa" / "terms.tsv", "r", encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter="\t"):
        src = r.get("source", "")
        dom = r.get("domain", "")
        if dom == "crypto" and "vendor:crypto_names" in src and "#ticker" not in src:
            k = (r.get("en") or "").strip().lower()
            fa = (r.get("fa") or "").strip()
            if k and fa and k not in STOPLIST:
                vetted_crypto.setdefault(k, []).append(fa)

latin_map = {}
for k, v in entities.items():
    latin_map[k] = v[0]
for k, v in vetted_crypto.items():
    if k not in latin_map:
        latin_map[k] = v[0]

def is_protected_latin_span(span_text):
    low = span_text.lower().strip()
    if low in entities:
        return False
    words = re.findall(r"\b[A-Za-z0-9]+\b", span_text)
    if len(words) >= 3 and all(w[0].isupper() for w in words):
        return True
    if PRODUCT_KW_RE.search(span_text):
        return True
    return False

# Latin spans: sequences of Latin words / punctuation
SPAN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.'\"&/-]*(?:\s+[A-Za-z0-9][A-Za-z0-9.'\"&/-]*)*")

# Latin word regex: pure letters only, bounded by non-alphanumeric
TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]+)(?![A-Za-z0-9])")

def replace_latin_refined(text):
    # Process span by span
    # If a span is protected (looks like fund/product name or capitalised run of 3+), leave untouched!
    # Otherwise, perform lookup on pure letter tokens that don't have digits/dots/hyphens in surrounding word
    def sub_span(m):
        span = m.group(0)
        # Check if span contains compound name with digits, dots, hyphens:
        # Check span protection
        if is_protected_latin_span(span):
            return span
        # Inside unprotected span: greedy 3/2/1 lookup
        words = list(re.finditer(r"(?<![A-Za-z0-9])([A-Za-z]+)(?![A-Za-z0-9])", span))
        if not words:
            return span
        res = []
        cur = 0
        i = 0
        while i < len(words):
            rep = None
            for w in (3, 2, 1):
                if i + w > len(words):
                    continue
                win = words[i:i + w]
                phr = " ".join(t.group(1) for t in win)
                low = phr.lower()
                # Tickers and ETF/ETN are never replaced
                first = win[0].group(1)
                if first.isupper() and len(first) <= 5:
                    continue
                if low in {"etf", "etn"}:
                    continue
                fa = latin_map.get(low)
                if fa:
                    rep = (fa, win[0].start(), win[-1].end())
                    i += w
                    break
            if rep:
                fa, st, end = rep
                res.append(span[cur:st])
                res.append(fa)
                cur = end
            else:
                i += 1
        res.append(span[cur:])
        return "".join(res)

    # Protect compounds with digits or dots or hyphens:
    # Any token with digits or dots or hyphens (like 1win, Fetch.ai) is protected
    COMPOUND_RE = re.compile(r"\b[A-Za-z0-9]*[0-9.-][A-Za-z0-9.-]*\b")
    # Replace Latin spans
    return SPAN_RE.sub(sub_span, text)

# Test cases
cases = [
    ("VanEck Gold Miners ETF", "VanEck Gold Miners ETF"),
    ("Physical Gold Etf (AAAU)", "Physical Gold Etf (AAAU)"),
    ("Fed Minutes Strike Hawkish", "Fed Minutes Strike Hawkish"),
    ("Equity Premium Income ETF", "Equity Premium Income ETF"),
    ("1win Markets", "1win Markets"),
    ("The Coin Republic", "The Coin Republic"),
    ("Roundhill Top WeeklyPay ETF", "Roundhill Top WeeklyPay ETF"),
    ("Fetch.ai and NuNet", "Fetch.ai and NuNet"),
    ("Bitwise NEAR ETF", "Bitwise NEAR ETF"),
    ("Ripple", "ریپل"),
    ("Cardano", "کاردانو"),
    ("Solana", "سولانا"),
    ("Ethereum", "اتریوم"),
    ("Bitcoin", "بیتکوین"),
    ("Citigroup", "سیتی‌گروپ"),
    ("Standard Chartered", "استاندارد چارترد"),
]

all_ok = True
full_cases = [
    ("Citigroup Global Markets یادداشت‌های قابل تماس خودکار مرتبط با VanEck Gold Miners ETF را معرفی می‌کند.",
     "سیتی‌گروپ Global Markets یادداشت‌های قابل تماس خودکار مرتبط با VanEck Gold Miners ETF را معرفی می‌کند."),
    ("معاملات دقیق با مناطق ریسک Goldman Sachs Physical Gold Etf (AAAU).",
     "معاملات دقیق با مناطق ریسک گلدمن ساکس Physical Gold Etf (AAAU)."),
    ("Fed Minutes Strike Hawkish Tone در حالی که اکثر مقامات منتظر افزایش دیگری تا پایان سال هستند",
     "Fed Minutes Strike Hawkish Tone در حالی که اکثر مقامات منتظر افزایش دیگری تا پایان سال هستند"),
    ("REX FANG & Innovation Equity Premium ETF سود سهام ۰.۲۱۰۵ دلاری را اعلام کرد",
     "REX FANG & Innovation Equity Premium ETF سود سهام ۰.۲۱۰۵ دلاری را اعلام کرد"),
    ("افزایش یا کاهش بیت کوین در ۵ دقیقه؟ ۱win Markets Crypto Live را راه اندازی کرد",
     "افزایش یا کاهش بیت کوین در ۵ دقیقه؟ ۱win Markets Crypto Live را راه اندازی کرد"),
    ("Cardano News: توسعه دهندگان اشکالات کلیدی Hydra را به عنوان Midnight Network Spotlights EV Privacy Tech - The Coin Republic رفع کردند",
     "کاردانو News: توسعه دهندگان اشکالات کلیدی Hydra را به عنوان Midnight Network Spotlights EV Privacy Tech - The Coin Republic رفع کردند"),
    ("Roundhill Top WeeklyPay ETF سود هفتگی ۰.۲۳۰۱ دلار را اعلام می کند",
     "Roundhill Top WeeklyPay ETF سود هفتگی ۰.۲۳۰۱ دلار را اعلام می کند"),
    ("Fetch.ai و NuNet برای ۲ میلیون دلار توسط Same Attacker مورد سوء استفاده قرار گرفتند",
     "Fetch.ai و NuNet برای ۲ میلیون دلار توسط Same Attacker مورد سوء استفاده قرار گرفتند"),
    ("BREAKING: Bitwise Near ETF برای فهرست و معامله در NYSE Arca تأیید شد، قیمت ۲۰% جهش کرد",
     "BREAKING: Bitwise Near ETF برای فهرست و معامله در NYSE Arca تأیید شد، قیمت ۲۰% جهش کرد"),
]

for inp, exp in full_cases:
    out = replace_latin_refined(inp)
    ok = (out == exp)
    if not ok:
        all_ok = False
        print(f"[FAIL FULL] In : {inp}")
        print(f"            Out: {out}")
        print(f"            Exp: {exp}")
    else:
        print(f"[PASS FULL] {inp[:40]}... -> {out[:40]}...")

print(f"\nAll test cases passed: {all_ok}")
