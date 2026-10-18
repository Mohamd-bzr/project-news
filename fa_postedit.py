#!/usr/bin/env python3
"""
fa_postedit — deterministic, idempotent Persian post-editing (Phase 2)
======================================================================
Pure stdlib. No network. Never imports `app`. No threads, no timers, no
writes. `post_edit(text)` is a pure function: same input -> same output,
and post_edit(post_edit(x)) == post_edit(x) for every input (tested).

Every rule below exists because docs/fa_audit.md measured the defect in the
engine's published output; the rule list is that defect list, fixed:

  audit §7 finding                        rule
  --------------------------------------  ----------------------------------
  Arabic yeh/kaf, alef maksura      -> 1   _fix_arabic_letters
  tatweel (ـ)                      -> 2   _fix_arabic_letters
  «می رود» (missing ZWNJ, 43.2%)   -> 3   _zwnj_mi
  «کتاب ها» (missing ZWNJ, 18.8%)  -> 4   _zwnj_ha
  «بزرگ تر» (missing ZWNJ, 3.1%)   -> 5   _zwnj_tar
  ASCII digits in FA text          -> 6   _to_persian_digits (URL/email safe)
  Latin residue in published text  -> 7   _replace_latin (lexicon, exact +
                                          unambiguous only)
  FA spelling variants («بیت کوین»
    vs «بیت‌کوین», audit §6)        -> 8   _canonicalize_fa (lexicon families)
  stray spacing / punct spacing    -> 9   _spacing

Order matters for idempotency: Latin replacement runs BEFORE the ZWNJ rules,
so a replacement that creates «می X» is fixed inside the same call and pass
2 finds nothing to change.

Safety contract (audit §7 / §9):
  * URLs, e-mails and bare domains are protected spans: never touched by
    digit conversion or Latin replacement (the existing fa_digits bug
    corrupted 101 published URLs; this must not repeat it).
  * ALL-CAPS tokens of <=5 chars (tickers: MSTR, US500, BTC...) are never
    replaced — too ambiguous by construction.
  * The lexicon decides: fa_for() returns None for missing OR ambiguous
    keys, and the original token is kept. Nothing is ever guessed.
  * post_edit(None) is None; post_edit("") is "".
"""
import re
import unicodedata

from fa_lexicon import ZWNJ, canon_sep, lexicon

# ----------------------------------------------------------------- helpers
_AR_YEH = "\u064a"      # ي
_FA_YEH = "\u06cc"      # ی
_AR_KAF = "\u0643"      # ك
_FA_KAF = "\u06a9"      # ک
_ALEF_MAKSURA = "\u0649"  # ى
_TATWEEL = "\u0640"

_PERSIAN_LETTER = r"\u0621-\u063a\u0641-\u064a\u067e\u0686\u0698\u06a9\u06af\u06cc"

_DIGIT_MAP = str.maketrans("0123456789", "\u06f0\u06f1\u06f2\u06f3\u06f4"
                           "\u06f5\u06f6\u06f7\u06f8\u06f9")

# protected spans: URLs, www, e-mails, bare domains with a path-less TLD
_PROTECT_RE = re.compile(
    r"(https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.-]+"
    r"|\b[\w-]+\.(?:com|net|org|io|ir|co|gov|edu|app|xyz|crypto"
    r"|me|tv|us|uk|de|ru|cn|jp|in|br|tr)\b)")

# Latin tokens for residue replacement (keeps intra-word . - ' for names)
_LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[.'-][A-Za-z0-9]+)*")

# Persian tokens for spelling-variant canonicalization (letters + ZWNJ)
_FA_TOKEN_RE = re.compile(
    r"[\u0621-\u063a\u0641-\u064a\u067e\u0686\u0698\u06a9\u06af\u06cc\u200c]+")

# ZWNJ typography patterns (all operate on Persian letters only)
_RE_MI = re.compile(r"(?<![%s])\b(\u0646?\u0645\u06cc) (?=[%s])"
                    % (_PERSIAN_LETTER, _PERSIAN_LETTER))
# plural/possessive suffixes, longest-first; the negative lookahead keeps
# real words that merely START with ها/های (هاشمی, هاشمي...) untouched
_RE_HA = re.compile(r"(?<=[%s]) (?=(?:\u0647\u0627\u06cc\u0646\u0645\u0627\u0646"
                    r"|\u0647\u0627\u06cc\u0634\u0627\u0646|\u0647\u0627\u06cc"
                    r"\u0634|\u0647\u0627\u06cc\u06cc|\u0647\u0627\u06cc"
                    r"|\u0647\u0627)(?![%s]))"
                    % (_PERSIAN_LETTER, _PERSIAN_LETTER))
# lexicalized comparatives: single word, NO ZWNJ («بیشتر», «کمتر», «بهترین»)
_TAR_NO_ZWNJ = {"\u0628\u06cc\u0634", "\u06a9\u0645", "\u0628\u0647"}
_RE_TAR = re.compile(r"(?P<w>[%s]+) (?=(?:\u062a\u0631|\u062a\u0631\u06cc"
                     r"\u0646)(?![%s]))" % (_PERSIAN_LETTER, _PERSIAN_LETTER))
_RE_ZWNJ_SPACE = re.compile(r" *\u200c *")
_RE_ZWNJ_RUN = re.compile(r"\u200c{2,}")
_RE_SPACE_BEFORE_PUNCT = re.compile(r" +([،؟؛,.!?:])(?![A-Za-z0-9])")
_RE_MULTI_SPACE = re.compile(r" {2,}")


def _fix_arabic_letters(s):
    return (s.replace(_AR_YEH, _FA_YEH).replace(_ALEF_MAKSURA, _FA_YEH)
             .replace(_AR_KAF, _FA_KAF).replace(_TATWEEL, ""))


def _zwnj_mi(s):
    """«می رود»/«نمی رود» -> «می‌رود»/«نمی‌رود» (standalone only)."""
    return _RE_MI.sub(lambda m: m.group(1) + ZWNJ, s)


def _zwnj_ha(s):
    """«کتاب ها/های/هایی» -> «کتاب‌ها/های/هایی» (suffix only)."""
    return _RE_HA.sub(ZWNJ, s)


def _zwnj_tar(s):
    """«بزرگ تر/ترین» -> «بزرگ‌تر/ترین»; lexicalized: «بیش تر»->«بیشتر»."""
    def sub(m):
        w = m.group("w")
        joiner = "" if w in _TAR_NO_ZWNJ else ZWNJ
        return w + joiner
    return _RE_TAR.sub(sub, s)


def _to_persian_digits(s):
    """ASCII digits -> ۰-۹ OUTSIDE protected spans only."""
    return s.translate(_DIGIT_MAP)


# Latin tokens and product/fund span protections
_PRODUCT_KW_RE = re.compile(r"\b(ETF|ETN|Fund|Trust|Notes)\b", re.IGNORECASE)
_LATIN_SPAN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.'\"&/-]*(?:\s+[A-Za-z0-9][A-Za-z0-9.'\"&/-]*)*")
_CLEAN_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]+)(?![A-Za-z0-9])")
_COMPOUND_TOKEN_RE = re.compile(r"[0-9.-]")


def _is_protected_latin_span(span_text, lex):
    """Leaves Latin spans that look like fund/product names untouched unless
    the whole span is an exact entities.tsv entry."""
    if lex.is_exact_entity(span_text):
        return False
    words = re.findall(r"\b[A-Za-z0-9]+\b", span_text)
    if len(words) >= 3 and all(w[0].isupper() for w in words):
        return True                    # capitalised run of 3+ tokens
    if _PRODUCT_KW_RE.search(span_text):
        return True                    # contains ETF|ETN|Fund|Trust|Notes
    return False


def _replace_latin_in_span(span, lex):
    """Replaces clean Latin words inside an unprotected span."""
    # Find whole word tokens in span. Tokens with digits/dots/hyphens are skipped.
    raw_tokens = list(re.finditer(r"\b\S+\b", span))
    clean_tokens = []
    for t in raw_tokens:
        tok_str = t.group(0)
        # Never touch tokens that contain digits, dots or hyphens inside a name (1win, Fetch.ai)
        if _COMPOUND_TOKEN_RE.search(tok_str) or not tok_str.isalpha():
            continue
        clean_tokens.append(t)

    if not clean_tokens:
        return span

    result, cursor, i = [], 0, 0
    while i < len(clean_tokens):
        replaced = None
        for width in (3, 2, 1):
            if i + width > len(clean_tokens):
                continue
            window = clean_tokens[i:i + width]
            # Ensure window tokens are contiguous in span
            win_start = window[0].start()
            win_end = window[-1].end()
            inter = span[win_start:win_end]
            expected_phrase = " ".join(t.group(0) for t in window)
            if inter != expected_phrase:
                continue
            fa = _lookup(expected_phrase, lex, window)
            if fa is not None:
                replaced = (fa, win_start, win_end)
                i += width
                break
        if replaced is None:
            i += 1
            continue
        fa, start, end = replaced
        result.append(span[cursor:start])
        result.append(fa)
        cursor = end
    result.append(span[cursor:])
    return "".join(result)


def _replace_latin_in_protected_span(span, lex):
    """Replaces exact multi-word entities (or whole-span single entities) from entities.tsv
    inside a protected span, leaving the rest of the span intact."""
    raw_tokens = list(re.finditer(r"\b\S+\b", span))
    clean_tokens = []
    for t in raw_tokens:
        tok_str = t.group(0)
        if _COMPOUND_TOKEN_RE.search(tok_str) or not tok_str.isalpha():
            continue
        clean_tokens.append(t)

    if not clean_tokens:
        return span

    result, cursor, i = [], 0, 0
    max_w = min(len(clean_tokens), 6)
    while i < len(clean_tokens):
        replaced = None
        for width in range(max_w, 0, -1):
            if i + width > len(clean_tokens):
                continue
            window = clean_tokens[i:i + width]
            win_start = window[0].start()
            win_end = window[-1].end()
            inter = span[win_start:win_end]
            expected_phrase = " ".join(t.group(0) for t in window)
            if inter != expected_phrase:
                continue
            if width == 1 and span.strip() != expected_phrase:
                continue
            if any(t.group(0).isupper() and 2 <= len(t.group(0)) <= 5 for t in window):
                continue
            if not lex.is_exact_entity(expected_phrase):
                continue
            fa = lex.latin_fa_for(expected_phrase)
            if fa is not None:
                replaced = (fa, win_start, win_end)
                i += width
                break
        if replaced is None:
            i += 1
            continue
        fa, start, end = replaced
        result.append(span[cursor:start])
        result.append(fa)
        cursor = end
    result.append(span[cursor:])
    return "".join(result)


def _replace_latin(part, lex):
    """Greedy longest-match (3/2/1 tokens) unambiguous residue replacement."""
    def _sub_span(m):
        span = m.group(0)
        if _is_protected_latin_span(span, lex):
            return _replace_latin_in_protected_span(span, lex)
        return _replace_latin_in_span(span, lex)

    return _LATIN_SPAN_RE.sub(_sub_span, part)


def _canonicalize_fa(part, lex):
    """Greedy 3/2/1-token windows: collapse TYPOGRAPHY variants of the same
    lexicon family to their canonical representative (space <-> ZWNJ, e.g.
    «بیت کوین» -> «بیت‌کوین»). Word boundaries are preserved: «رمز ارز»
    (two words) never merges into «رمزارز» (one word) — that is a REVIEW.md
    decision, not an automatic one."""
    fa_map = lex.fa_windows
    if not fa_map:
        return part
    tokens = list(_FA_TOKEN_RE.finditer(part))
    if not tokens:
        return part
    result, cursor, i = [], 0, 0
    while i < len(tokens):
        replaced = None
        for width in (3, 2, 1):
            if i + width > len(tokens):
                continue
            window = tokens[i:i + width]
            text_win = " ".join(t.group(0) for t in window)
            hit = fa_map.get(canon_sep(text_win))
            if hit is not None and hit[0] != text_win:
                replaced = (hit[0], window[0].start(), window[-1].end())
                i += width
                break
        if replaced is None:
            i += 1
            continue
        fa, start, end = replaced
        result.append(part[cursor:start])
        result.append(fa)
        cursor = end
    result.append(part[cursor:])
    return "".join(result)


def _lookup(phrase, lex, window):
    """Lexicon lookup with safety gates. None = keep original."""
    low = phrase.lower()
    if not low or len(low) < 3:
        return None
    # Ticker-shaped (any uppercase token 2-5 chars), ETF, ETN are never replaced or expanded
    if any(t.group(0).isupper() and 2 <= len(t.group(0)) <= 5 for t in window) or low in {"etf", "etn"}:
        return None
    fa = lex.latin_fa_for(low)
    if fa is None and low.endswith("'s"):
        fa = lex.latin_fa_for(low[:-2])
    return fa


def _protect_and_map(text, fn):
    """Apply fn to every NON-protected span; keep protected spans verbatim."""
    parts, last = [], 0
    for m in _PROTECT_RE.finditer(text):
        parts.append(fn(text[last:m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(fn(text[last:]))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Core term enforcement (Owner decisions D1-D5 + approved terms)
# ---------------------------------------------------------------------------
_FA_WORD_BOUND_LEFT = r"(?<![" + _PERSIAN_LETTER + r"\u200c])"
_FA_WORD_BOUND_RIGHT = r"(?![" + _PERSIAN_LETTER + r"\u200c])"

# D5: coin names compound prefixes (approved coin compounds: بیت، دوج، لایت، استیبل، آلت، میم + coin names from TSV)
_COIN_PREFIXES = r"(?:بیت|دوج|لایت|استیبل|آلت|میم|بایننس|فایل|شیت|پپه)"
_RE_COIN_SPACE = re.compile(
    _FA_WORD_BOUND_LEFT + f"({_COIN_PREFIXES})" + r" +کوین"
)

# TA context keywords for support rule
_RE_TA_CONTEXT = re.compile(
    r"\b(resistance|level|levels|break|breakout|breaks|chart|charts|price|prices"
    r"|trend|bounce|zone|zones|floor|ceiling|technical|ta|moving average|rsi|indicator)\b",
    re.IGNORECASE,
)

# Bad variants for D1 (cryptocurrency)
_RE_D1_PLURAL_INDEF = re.compile(
    _FA_WORD_BOUND_LEFT + r"(?:رمزارز|رمز ارز|ارزهای رمزنگاری[\u200c ]?شده)هایی" + _FA_WORD_BOUND_RIGHT
)
_RE_D1_PLURAL_INDEF_EH = re.compile(
    _FA_WORD_BOUND_LEFT + r"ارزهای رمزنگاری[\u200c ]?شده‌ای" + _FA_WORD_BOUND_RIGHT
)
_RE_D1_PLURAL = re.compile(
    _FA_WORD_BOUND_LEFT + r"(?:(?:رمزارز|رمز ارز|ارزهای رمزنگاری[\u200c ]?شده)(?:ها|های)|ارزهای رمزنگاری[\u200c ]?شده)" + _FA_WORD_BOUND_RIGHT
)
_RE_D1_SING_INDEF_EH = re.compile(
    _FA_WORD_BOUND_LEFT + r"ارز رمزنگاری[\u200c ]?شده‌ای" + _FA_WORD_BOUND_RIGHT
)
_RE_D1_SING_INDEF_YEH = re.compile(
    _FA_WORD_BOUND_LEFT + r"(?:رمزارز|رمز ارز)ی" + _FA_WORD_BOUND_RIGHT
)
_RE_D1_SING = re.compile(
    _FA_WORD_BOUND_LEFT + r"(?:رمزارز|رمز ارز|ارز رمزنگاری[\u200c ]?شده)" + _FA_WORD_BOUND_RIGHT
)

# D2 Bull / Bear market
_RE_D2_BULL_PLURAL = re.compile(_FA_WORD_BOUND_LEFT + r"بازارهای گاوی" + _FA_WORD_BOUND_RIGHT)
_RE_D2_BULL_SING = re.compile(_FA_WORD_BOUND_LEFT + r"بازار گاوی" + _FA_WORD_BOUND_RIGHT)
_RE_D2_BEAR_PLURAL = re.compile(_FA_WORD_BOUND_LEFT + r"بازارهای خرسی" + _FA_WORD_BOUND_RIGHT)
_RE_D2_BEAR_SING = re.compile(_FA_WORD_BOUND_LEFT + r"بازار خرسی" + _FA_WORD_BOUND_RIGHT)

# Support (TA context)
_RE_SUPPORT_PLURAL_HAYE = re.compile(_FA_WORD_BOUND_LEFT + r"پشتیبانی‌های" + _FA_WORD_BOUND_RIGHT)
_RE_SUPPORT_PLURAL_HA = re.compile(_FA_WORD_BOUND_LEFT + r"پشتیبانی‌ها" + _FA_WORD_BOUND_RIGHT)
_RE_SUPPORT_SING = re.compile(_FA_WORD_BOUND_LEFT + r"پشتیبانی" + _FA_WORD_BOUND_RIGHT)

# Staking (سهامداری only, never سرمایه‌گذاری)
_RE_STAKING_PLURAL_HAYE = re.compile(_FA_WORD_BOUND_LEFT + r"سهامداری‌های" + _FA_WORD_BOUND_RIGHT)
_RE_STAKING_PLURAL_HA = re.compile(_FA_WORD_BOUND_LEFT + r"سهامداری‌ها" + _FA_WORD_BOUND_RIGHT)
_RE_STAKING_SING = re.compile(_FA_WORD_BOUND_LEFT + r"سهامداری" + _FA_WORD_BOUND_RIGHT)

# Oversold
_RE_OVERSOLD = re.compile(_FA_WORD_BOUND_LEFT + r"فروش بیش از حد" + _FA_WORD_BOUND_RIGHT)

# D3 (custody) — STATUS: review (disabled in enforce_terms)
_RE_CUSTODY_EN = re.compile(r"\bcustod(?:y|ian|ial)\b", re.IGNORECASE)
_RE_CUSTODY_CTX = re.compile(
    r"\b(crypto|bitcoin|digital asset|etf|wallet|institutional|exchange|bank|service|solution|provider|platform)\b",
    re.IGNORECASE,
)
_RE_CUSTODY_NEG = re.compile(r"\b(child|in custody|police|arrest|detain|jail|prison)\b", re.IGNORECASE)
_RE_HESANAT = re.compile(_FA_WORD_BOUND_LEFT + r"حضانت" + _FA_WORD_BOUND_RIGHT)
_RE_NEGAHDARI = re.compile(_FA_WORD_BOUND_LEFT + r"نگهداری" + _FA_WORD_BOUND_RIGHT)


def apply_custody_review(text_fa: str, source_en: str) -> str:
    """D3 custody rule (for review/eval). Replaces only حضانت -> نگهداری امن in finance context."""
    if not source_en or not _RE_CUSTODY_EN.search(source_en):
        return text_fa
    if not _RE_CUSTODY_CTX.search(source_en) or _RE_CUSTODY_NEG.search(source_en):
        return text_fa
    return _RE_HESANAT.sub("نگهداری امن", text_fa)


# D4 (yield/yields) — STATUS: review (disabled in enforce_terms)
_RE_YIELD_EN = re.compile(r"\byields?\b", re.IGNORECASE)
_RE_YIELD_CTX = re.compile(
    r"\b(treasury|bond|bonds|note|notes|10-year|2-year|rate|rates|curve|basis points|bps|dividend|dividends)\b",
    re.IGNORECASE,
)
_RE_BAZDEHI = re.compile(_FA_WORD_BOUND_LEFT + r"بازدهی" + _FA_WORD_BOUND_RIGHT)


def apply_yield_review(text_fa: str, source_en: str) -> str:
    """D4 yield rule (for review/eval). Replaces بازدهی with بازده in finance context."""
    if not source_en or not _RE_YIELD_EN.search(source_en):
        return text_fa
    if not _RE_YIELD_CTX.search(source_en):
        return text_fa
    return _RE_BAZDEHI.sub("بازده", text_fa)


def _enforce_terms_free(text_fa: str, source_en: str) -> str:
    """Core terms replacement on text outside protected spans."""
    res = text_fa

    # D5 coin names: only on English-source texts (source_en is not None)
    res = _RE_COIN_SPACE.sub(lambda m: m.group(1) + ZWNJ + "کوین", res)

    # D1: cryptocurrency / cryptocurrencies / crypto / digital assets
    if re.search(r"\b(?:crypto[\s-]?currenc(?:y|ies)|crypto|digital\s+assets?)\b", source_en, re.IGNORECASE):
        res = _RE_D1_PLURAL_INDEF.sub("ارزهای دیجیتالی", res)
        res = _RE_D1_PLURAL_INDEF_EH.sub("ارزهای دیجیتالی", res)
        res = _RE_D1_PLURAL.sub("ارزهای دیجیتال", res)
        res = _RE_D1_SING_INDEF_EH.sub("ارز دیجیتالی", res)
        res = _RE_D1_SING_INDEF_YEH.sub("ارز دیجیتالی", res)
        res = _RE_D1_SING.sub("ارز دیجیتال", res)

    # D2: bull market / bear market
    if re.search(r"\bbull\s+markets?\b", source_en, re.IGNORECASE):
        res = _RE_D2_BULL_PLURAL.sub("بازارهای صعودی", res)
        res = _RE_D2_BULL_SING.sub("بازار صعودی", res)
    if re.search(r"\bbear\s+markets?\b", source_en, re.IGNORECASE):
        res = _RE_D2_BEAR_PLURAL.sub("بازارهای نزولی", res)
        res = _RE_D2_BEAR_SING.sub("بازار نزولی", res)

    # Support (TA context only)
    if re.search(r"\bsupport\b", source_en, re.IGNORECASE) and _RE_TA_CONTEXT.search(source_en):
        res = _RE_SUPPORT_PLURAL_HAYE.sub("حمایت‌های", res)
        res = _RE_SUPPORT_PLURAL_HA.sub("حمایت‌ها", res)
        res = _RE_SUPPORT_SING.sub("حمایت", res)

    # Staking (سهامداری only, never سرمایه‌گذاری)
    if re.search(r"\bstaking\b", source_en, re.IGNORECASE):
        res = _RE_STAKING_PLURAL_HAYE.sub("استیکینگ‌های", res)
        res = _RE_STAKING_PLURAL_HA.sub("استیکینگ‌ها", res)
        res = _RE_STAKING_SING.sub("استیکینگ", res)

    # Oversold
    if re.search(r"\boversold\b", source_en, re.IGNORECASE):
        res = _RE_OVERSOLD.sub("اشباع فروش", res)

    # D4: yield / yields
    if _RE_YIELD_EN.search(source_en) and _RE_YIELD_CTX.search(source_en):
        res = _RE_BAZDEHI.sub("بازده", res)

    return res


def enforce_terms(text_fa: str, source_en: str | None = None) -> str:
    """Enforce owner-decided core terms on English-source translations.
    Idempotent, safe, never touches native-Persian texts or protected spans."""
    if not text_fa or not source_en:
        return text_fa
    return _protect_and_map(text_fa, lambda p: _enforce_terms_free(p, source_en))


def post_edit(text, lex=None, source_en=None):
    """Deterministic Persian post-editing. Pure, idempotent, safe."""
    if text is None:
        return None
    if not isinstance(text, str) or not text:
        return text
    s = unicodedata.normalize("NFC", text)

    # 1-2 + 7 + 8 + 6: within NON-protected spans only (URLs/e-mails are
    # never touched — the audit's fa_digits bug corrupted 101 published URLs)
    lex = lex or lexicon()

    def _free(part):
        part = _fix_arabic_letters(part)
        part = _replace_latin(part, lex)
        part = _canonicalize_fa(part, lex)
        if source_en:
            part = _enforce_terms_free(part, source_en)
        return _to_persian_digits(part)

    s = _protect_and_map(s, _free)

    # 3-5: ZWNJ typography
    s = _RE_ZWNJ_SPACE.sub(ZWNJ, s)
    s = _RE_ZWNJ_RUN.sub(ZWNJ, s)
    s = _zwnj_mi(s)
    s = _zwnj_ha(s)
    s = _zwnj_tar(s)

    # 8: spacing
    s = _RE_SPACE_BEFORE_PUNCT.sub(r"\1", s)
    s = _RE_MULTI_SPACE.sub(" ", s)
    s = s.strip(" \t\r\n" + ZWNJ)
    return s
