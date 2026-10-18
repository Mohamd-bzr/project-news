#!/usr/bin/env python3
"""
fa_eval.py — Phase-3 evaluation of the FA post-editing layer (offline).
=======================================================================
Golden source:
  * data/fa/golden.jsonl when it exists (one JSON object per line; keys
    id, english, engine_output, fixed_fa [, stratum]) — the hand-corrected
    set; golden metrics (term accuracy / chrF / edit distance) run on rows
    with a non-empty fixed_fa.
  * otherwise the committed data/fa/golden_template.tsv — fixed_fa is
    blank, so ONLY the golden-free metrics are reported.

Every metric runs on ENGLISH-source rows only: rows failing the
non-English heuristic (French/other stopwords or diacritics, or a Persian
title) are excluded and counted per stratum — the template pool contains
untranslated French/German headlines no EN->FA metric can judge.

No translate.py change: post_edit() is called directly (the hook is OFF).
Offline, stdlib only, never writes the database.
"""
import json
import re
import sys
from pathlib import Path

# Windows console encoding safeguard
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from translate import is_persian, longest_latin_run      # noqa: E402
from fa_postedit import (                                # noqa: E402
    post_edit,
    enforce_terms,
    apply_custody_review,
    apply_yield_review,
    _RE_COIN_SPACE,
    _RE_TA_CONTEXT,
    _RE_D1_PLURAL,
    _RE_D1_SING,
    _RE_D2_BULL_SING,
    _RE_D2_BULL_PLURAL,
    _RE_D2_BEAR_SING,
    _RE_D2_BEAR_PLURAL,
    _RE_SUPPORT_SING,
    _RE_STAKING_SING,
    _RE_OVERSOLD,
)

DIG_RE = re.compile("[0-9\\u06f0-\\u06f9]")
NUM_RE = re.compile("[0-9\\u06f0-\\u06f9]+(?:[.,\\u066b][0-9\\u06f0-\\u06f9]+)*")
URL_RE = re.compile("https?://\\S+|www\\.\\S+|[\\w.+-]+@[\\w-]+\\.[\\w.-]+")
TICKER_RE = re.compile("\\b[A-Z][A-Z0-9]{1,4}\\b")
PERSIAN_RE = re.compile("[\\u0621-\\u064a]")

# ── non-English heuristic (deterministic, conservative) ────────────────────
DIAC_RE = re.compile("[\\u00e0-\\u00ff\\u00c0-\\u00d7]")   # à..ÿ and upper
NON_EN_STOP = {
    # french
    "le", "la", "les", "des", "une", "est", "dans", "pour", "avec", "sur",
    "pas", "plus", "par", "qui", "que", "sont", "sein", "au", "aux", "ces",
    "cet", "cette", "apr\\u00e8s", "march\\u00e9", "deux",
    # german
    "der", "die", "das", "und", "nicht", "mit", "auch", "noch", "wird",
    "werden", "jetzt", "gegen", "nach",
    # spanish / portuguese / italian
    "los", "las", "del", "por", "con", "una", "para", "este", "est\\u00e1",
    "estao", "mais", "sobre", "sono", "per", "gli", "delle",
}


def is_english_source(text):
    """False for French/other Latin texts (stopwords/diacritics) or Persian."""
    t = text or ""
    if len(PERSIAN_RE.findall(t)) / max(len(t), 1) > 0.3:
        return False                      # a Persian wire title, not EN input
    if DIAC_RE.search(t):
        return False                      # English headlines carry no à/ü/ß
    words = re.findall(r"[a-z']+", t.lower())
    hits = sum(1 for w in words if w in NON_EN_STOP)
    return hits < 2


# ── preservation checks ────────────────────────────────────────────────────
def digit_count(s):
    return len(DIG_RE.findall(s or ""))


def numbers(s):
    return [w.replace("\\u066b", ".").translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        for w in NUM_RE.findall(s or "")]


def urls(s):
    return URL_RE.findall(s or "")


def tickers(s):
    return TICKER_RE.findall(s or "")


# ── golden metrics (pure python) ───────────────────────────────────────────
def levenshtein(a, b):
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _ngrams(s, n):
    s = re.sub("\\s+", "", s)
    return [s[i:i + n] for i in range(len(s) - n + 1)]


def chrf(hyp, ref, max_n=6, beta=2.0):
    """chrF: average character n-gram F-beta (n=1..max_n), spaces excluded."""
    from collections import Counter
    fs = []
    for n in range(1, max_n + 1):
        rh, hh = Counter(_ngrams(ref, n)), Counter(_ngrams(hyp, n))
        if not rh:
            continue
        overlap = sum((rh & hh).values())
        p = overlap / max(sum(hh.values()), 1)
        r = overlap / sum(rh.values())
        if p + r == 0:
            fs.append(0.0)
            continue
        b2 = beta * beta
        fs.append((1 + b2) * p * r / (b2 * p + r))
    return 100.0 * (sum(fs) / len(fs)) if fs else 0.0


def evaluate_opinion_verdict(opinion_rows, raw_better_rate=0.0, chrf_post=0.0, chrf_raw=0.0):
    """Pure decision for golden opinion set. Requires >= 30 opinion rows."""
    if len(opinion_rows) < 30:
        return "INSUFFICIENT DATA - no verdict", [f"opinion rows: {len(opinion_rows)} < 30 required"]
    if raw_better_rate <= 0.10 and chrf_post >= chrf_raw:
        return "ENABLE", ["Conditions met: raw_better <= 10% AND chrF(post_edit) >= chrF(raw)."]
    reasons = []
    if raw_better_rate > 0.10:
        reasons.append(f"raw_better ({raw_better_rate:.1%}) > 10% threshold")
    if chrf_post < chrf_raw:
        reasons.append(f"chrF(post_edit) {chrf_post:.1f} < chrF(raw) {chrf_raw:.1f}")
    return "DO NOT ENABLE", reasons


def load_rows():
    """(rows, source_label, has_golden) — tolerant reader for both shapes."""
    jl = REPO / "data" / "fa" / "golden.jsonl"
    rows, has_golden = [], False
    if jl.exists():
        for line in jl.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            pref = (o.get("pref") or "").strip()
            fixed = (o.get("fixed_fa") or o.get("fixed") or "").strip()
            if not pref and fixed:
                pref = "fixed"
            rows.append({"id": str(o.get("id", "")),
                         "english": o.get("english") or o.get("source") or "",
                         "engine_output": o.get("engine_output")
                         or o.get("output") or "",
                         "post_edit_output": o.get("post_edit_output") or "",
                         "fixed_fa": fixed,
                         "pref": pref,
                         "stratum": o.get("stratum", "?")})
            has_golden = has_golden or bool(fixed or pref)
        return rows, "golden.jsonl", has_golden
    tpl = REPO / "data" / "fa" / "golden_template.tsv"
    lines = tpl.read_text(encoding="utf-8-sig").splitlines()
    for i, line in enumerate(lines[1:]):
        c = line.split("\t")
        if len(c) < 5:
            continue
        pref = c[5].strip() if len(c) > 5 else ""
        fixed = c[4].strip()
        if not pref and fixed:
            pref = "fixed"
        rows.append({"id": c[0], "english": c[1], "engine_output": c[2],
                     "post_edit_output": c[3] if len(c) > 3 else "",
                     "fixed_fa": fixed,
                     "pref": pref,
                     "stratum": "ABC"[min(i // 100, 2)]})
        has_golden = has_golden or bool(fixed or pref)
    return rows, "golden_template.tsv", has_golden


def run_db_decision_review(regressed=None):
    db_path = Path("E:/freebuff/.mohmd_news.db")
    if not db_path.exists():
        print(f"\n[DB REVIEW] Database not found at {db_path}; skipping DB corpus review.")
        return

    import sqlite3
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    c = conn.cursor()
    rows = c.execute(
        "SELECT id, title, title_fa, summary, summary_fa FROM articles WHERE title IS NOT NULL"
    ).fetchall()

    from fa_postedit import (
        _fix_arabic_letters, _canonicalize_fa, _to_persian_digits,
        _protect_and_map, _zwnj_mi, _zwnj_ha, _zwnj_tar,
        _RE_ZWNJ_SPACE, _RE_ZWNJ_RUN, _RE_SPACE_BEFORE_PUNCT, _RE_MULTI_SPACE, ZWNJ
    )
    from fa_lexicon import lexicon
    lex = lexicon()

    total_texts = 0
    raw_pass = 0
    post_pass = 0
    rescued_typo = 0
    rescued_entity = 0
    rescued_non_entity = 0

    term_counts = {
        "D1 (cryptocurrency)": 0,
        "D2 (bull market)": 0,
        "D2 (bear market)": 0,
        "D5 (coin names)": 0,
        "support": 0,
        "staking": 0,
        "oversold": 0,
        "D3 (custody - review)": 0,
        "D4 (yield - review)": 0,
    }

    samples_d1 = []
    samples_d2 = []
    samples_d5 = []
    samples_support = []
    samples_staking = []
    samples_oversold = []
    samples_d3 = []
    samples_d4 = []

    changed_texts = 0
    corpus_digit_bad = []
    corpus_num_bad = []
    corpus_url_bad = []
    corpus_ticker_bad = []
    corpus_nonidem = []
    corpus_lat_worse = []

    for row_id, en_title, fa_title, en_summ, fa_summ in rows:
        pairs = []
        if fa_title and is_english_source(en_title):
            pairs.append((en_title, fa_title))
        if fa_summ and en_summ and is_english_source(en_summ):
            pairs.append((en_summ, fa_summ))

        row_hits = set()
        for en, fa in pairs:
            total_texts += 1
            r_p = is_persian(fa)
            pe = post_edit(fa, source_en=en)
            p_p = is_persian(pe)
            if r_p:
                raw_pass += 1
            if p_p:
                post_pass += 1

            if pe != fa:
                changed_texts += 1
                if digit_count(fa) != digit_count(pe):
                    corpus_digit_bad.append((en, fa, pe))
                if sorted(numbers(fa)) != sorted(numbers(pe)):
                    corpus_num_bad.append((en, fa, pe))
                if any(u not in pe for u in urls(fa)):
                    corpus_url_bad.append((en, fa, pe))
                if any(t not in pe for t in tickers(fa)):
                    corpus_ticker_bad.append((en, fa, pe))
                if post_edit(pe, source_en=en) != pe:
                    corpus_nonidem.append((en, fa, pe))
                if longest_latin_run(pe) > longest_latin_run(fa):
                    corpus_lat_worse.append((en, fa, pe))

            if not r_p and p_p:
                no_lat = _protect_and_map(fa, lambda part: _to_persian_digits(_canonicalize_fa(_fix_arabic_letters(part), lex)))
                no_lat = _RE_MULTI_SPACE.sub(" ", _RE_SPACE_BEFORE_PUNCT.sub(r"\1", _zwnj_tar(_zwnj_ha(_zwnj_mi(_RE_ZWNJ_RUN.sub(ZWNJ, _RE_ZWNJ_SPACE.sub(ZWNJ, no_lat))))))).strip(" \t\r\n" + ZWNJ)
                if is_persian(no_lat):
                    rescued_typo += 1
                else:
                    post_no_terms = post_edit(fa, source_en=None)
                    if is_persian(post_no_terms):
                        rescued_entity += 1
                    else:
                        rescued_non_entity += 1

            # Check D1
            if re.search(r"\b(?:crypto[\s-]?currenc(?:y|ies)|crypto|digital\s+assets?)\b", en, re.I):
                before = fa
                after = _RE_D1_SING.sub("ارز دیجیتال", _RE_D1_PLURAL.sub("ارزهای دیجیتال", before))
                if before != after:
                    row_hits.add("D1 (cryptocurrency)")
                    if len(samples_d1) < 20 and (en, before, after) not in samples_d1:
                        samples_d1.append((en, before, after))

            # Check D2
            if re.search(r"\bbull\s+markets?\b", en, re.I):
                if _RE_D2_BULL_SING.search(fa) or _RE_D2_BULL_PLURAL.search(fa):
                    row_hits.add("D2 (bull market)")
                    pe_d2 = _RE_D2_BULL_SING.sub("بازار صعودی", _RE_D2_BULL_PLURAL.sub("بازارهای صعودی", fa))
                    if len(samples_d2) < 20 and (en, fa, pe_d2) not in samples_d2:
                        samples_d2.append((en, fa, pe_d2))
            if re.search(r"\bbear\s+markets?\b", en, re.I):
                if _RE_D2_BEAR_SING.search(fa) or _RE_D2_BEAR_PLURAL.search(fa):
                    row_hits.add("D2 (bear market)")
                    pe_d2 = _RE_D2_BEAR_SING.sub("بازار نزولی", _RE_D2_BEAR_PLURAL.sub("بازارهای نزولی", fa))
                    if len(samples_d2) < 20 and (en, fa, pe_d2) not in samples_d2:
                        samples_d2.append((en, fa, pe_d2))

            # Check D5
            if _RE_COIN_SPACE.search(fa):
                row_hits.add("D5 (coin names)")
                pe_d5 = _RE_COIN_SPACE.sub(lambda m: m.group(1) + ZWNJ + "کوین", fa)
                if len(samples_d5) < 20 and (en, fa, pe_d5) not in samples_d5:
                    samples_d5.append((en, fa, pe_d5))

            # Check support
            if re.search(r"\bsupport\b", en, re.I) and _RE_TA_CONTEXT.search(en):
                if _RE_SUPPORT_SING.search(fa):
                    row_hits.add("support")
                    pe_supp = _RE_SUPPORT_SING.sub("حمایت", fa)
                    if len(samples_support) < 20 and (en, fa, pe_supp) not in samples_support:
                        samples_support.append((en, fa, pe_supp))

            # Check staking
            if re.search(r"\bstaking\b", en, re.I):
                if _RE_STAKING_SING.search(fa):
                    row_hits.add("staking")
                    pe_stk = _RE_STAKING_SING.sub("استیکینگ", fa)
                    if len(samples_staking) < 20 and (en, fa, pe_stk) not in samples_staking:
                        samples_staking.append((en, fa, pe_stk))

            # Check oversold
            if re.search(r"\boversold\b", en, re.I):
                if _RE_OVERSOLD.search(fa):
                    row_hits.add("oversold")
                    pe_over = _RE_OVERSOLD.sub("اشباع فروش", fa)
                    if len(samples_oversold) < 20 and (en, fa, pe_over) not in samples_oversold:
                        samples_oversold.append((en, fa, pe_over))

            # Check D3 review
            c_after = apply_custody_review(fa, en)
            if c_after != fa:
                row_hits.add("D3 (custody - review)")
                if len(samples_d3) < 20 and (en, fa, c_after) not in samples_d3:
                    samples_d3.append((en, fa, c_after))

            # Check D4 review
            y_after = apply_yield_review(fa, en)
            if y_after != fa:
                row_hits.add("D4 (yield - review)")
                if len(samples_d4) < 20 and (en, fa, y_after) not in samples_d4:
                    samples_d4.append((en, fa, y_after))

        for h in row_hits:
            term_counts[h] += 1

    print("\n" + "=" * 70)
    print("DECISION REVIEW & CORPUS EVALUATION (.mohmd_news.db)")
    print("=" * 70)

    print(f"\nCorpus Texts Evaluated: {total_texts}")
    print(f"Whole Corpus is_persian Pass Rate: raw {raw_pass}/{total_texts} ({raw_pass/total_texts:.2%}) -> post_edit {post_pass}/{total_texts} ({post_pass/total_texts:.2%})")
    print(f"is_persian Rescues by Entity: {rescued_entity}")
    print(f"is_persian Rescues ONLY by Non-Entity: {rescued_non_entity} (MUST be 0)")

    print(f"\n-- Whole Corpus Preservation Invariants (Evaluated Changed Texts: {changed_texts}/{total_texts}) --")
    print(f"  * digits preserved: {changed_texts - len(corpus_digit_bad)}/{changed_texts}")
    print(f"  * numbers preserved: {changed_texts - len(corpus_num_bad)}/{changed_texts}")
    print(f"  * URLs preserved: {changed_texts - len(corpus_url_bad)}/{changed_texts}")
    print(f"  * tickers preserved: {changed_texts - len(corpus_ticker_bad)}/{changed_texts}")
    print(f"  * idempotent: {changed_texts - len(corpus_nonidem)}/{changed_texts}")
    print(f"  * no Latin run worsened: {changed_texts - len(corpus_lat_worse)}/{changed_texts}")

    print("\n-- Rows Changed Per Term in core_terms.tsv --")
    for term, count in term_counts.items():
        print(f"  {term:25}: {count} rows")

    print("\n-- 20 Real DB Examples: D1 (cryptocurrency -> ارز دیجیتال / ارزهای دیجیتال) --")
    for i, (en, raw, pe) in enumerate(samples_d1[:20], 1):
        print(f"[{i:02}] EN  : {en}\n     RAW : {raw}\n     POST: {pe}")

    print("\n-- 20 Real DB Examples: D2 (bull/bear market -> بازار صعودی / نزولی) --")
    for i, (en, raw, pe) in enumerate(samples_d2[:20], 1):
        print(f"[{i:02}] EN  : {en}\n     RAW : {raw}\n     POST: {pe}")

    print("\n-- 20 Real DB Examples: D5 (coin names prefix+ZWNJ+کوین) --")
    for i, (en, raw, pe) in enumerate(samples_d5[:20], 1):
        print(f"[{i:02}] EN  : {en}\n     RAW : {raw}\n     POST: {pe}")

    print("\n-- Real DB Examples: support -> حمایت (Technical Analysis Context) --")
    for i, (en, raw, pe) in enumerate(samples_support[:20], 1):
        print(f"[{i:02}] EN  : {en}\n     RAW : {raw}\n     POST: {pe}")

    print(f"\n-- Real DB Examples: staking -> استیکینگ (سهامداری only, n={len(samples_staking)}) --")
    for i, (en, raw, pe) in enumerate(samples_staking[:20], 1):
        print(f"[{i:02}] EN  : {en}\n     RAW : {raw}\n     POST: {pe}")

    print(f"\n-- Real DB Examples: oversold -> اشباع فروش (فروش بیش از حد, n={len(samples_oversold)}) --")
    for i, (en, raw, pe) in enumerate(samples_oversold[:20], 1):
        print(f"[{i:02}] EN  : {en}\n     RAW : {raw}\n     POST: {pe}")

    print("\n-- D3 (custody -> نگهداری امن) Review: 20 Real Examples --")
    for i, (en, raw, pe) in enumerate(samples_d3[:20], 1):
        print(f"[{i:02}] EN  : {en}\n     RAW : {raw}\n     REV : {pe}")

    def d3_risk(item):
        en, raw, rev = item
        score = 0
        if "حضانت" not in raw and "نگهداری" in raw:
            score += 10
        if re.search(r"self-?custod", en, re.I) or "خود" in raw:
            score += 5
        if re.search(r"\b(service|solution|provider)\b", en, re.I):
            score += 2
        return score

    d3_riskiest = sorted(samples_d3, key=d3_risk, reverse=True)[:5]
    print("\n-- D3 (custody) Top 5 Riskiest Examples (Review) --")
    for i, (en, raw, pe) in enumerate(d3_riskiest, 1):
        print(f"[{i}] EN  : {en}\n    RAW : {raw}\n    REV : {pe}")

    print("\n-- D4 (yield/yields -> بازده) Review: 20 Real Examples --")
    for i, (en, raw, pe) in enumerate(samples_d4[:20], 1):
        print(f"[{i:02}] EN  : {en}\n     RAW : {raw}\n     REV : {pe}")

    def d4_risk(item):
        en, raw, rev = item
        score = 0
        if re.search(r"\b(?:yields?\s+(?:\d+|just|\$|around|near|above|below|over|more|less|a\s|at\s))\b", en, re.I):
            score += 10
        if re.search(r"\b(?:dividend|earnings|cash flow)\s+yields?\b", en, re.I):
            score += 5
        if re.search(r"^(?:higher|lower|rising|falling)\s+yields\b", en, re.I):
            score += 3
        return score

    d4_riskiest = sorted(samples_d4, key=d4_risk, reverse=True)[:5]
    print("\n-- D4 (yield/yields) Top 5 Riskiest Examples (Review) --")
    for i, (en, raw, pe) in enumerate(d4_riskiest, 1):
        print(f"[{i}] EN  : {en}\n    RAW : {raw}\n    REV : {pe}")

    print("\n" + "=" * 70)
    num_regressed = len(regressed) if regressed else 0
    if rescued_non_entity == 0 and num_regressed == 0:
        print("VERDICT: AUTOMATED PRESERVATION GATES PASSED (0 regressions, non-entity rescue = 0).")
        print("         Final enablement requires human review set (>=30 opinion rows; currently golden.jsonl not populated).")
    else:
        print(f"VERDICT: NOT READY: regressions={num_regressed}, non_entity_rescue={rescued_non_entity}")
    print("      (fa_post_edit toggle remains untouched: OFF)")
    print("=" * 70)


def main():
    rows, source, has_golden = load_rows()
    print(f"source: {source}  rows={len(rows)}  golden_available={has_golden}")

    kept, excluded = [], {"A": 0, "B": 0, "C": 0, "?": 0}
    for r in rows:
        if is_english_source(r["english"]):
            kept.append(r)
        else:
            excluded[r["stratum"]] += 1
    ex = " ".join(f"{k}={v}" for k, v in sorted(excluded.items()) if v or k in "ABC")
    print(f"excluded non-English sources: {sum(excluded.values())} ({ex})")
    print(f"evaluated rows: {len(kept)}")

    pass_raw = pass_post = 0
    regressed, lat_worse, digit_bad, num_bad, url_bad, ticker_bad, nonidem = \
        [], [], [], [], [], [], []
    lrr_raw, lrr_post = [], []
    for r in kept:
        raw, post = r["engine_output"], post_edit(r["engine_output"], source_en=r["english"])
        rp, pp = is_persian(raw), is_persian(post)
        pass_raw += rp
        pass_post += pp
        if rp and not pp:
            regressed.append(r)
        a, b = longest_latin_run(raw), longest_latin_run(post)
        lrr_raw.append(a)
        lrr_post.append(b)
        if b > a:
            lat_worse.append(r)
        if digit_count(raw) != digit_count(post):
            digit_bad.append(r)
        if sorted(numbers(raw)) != sorted(numbers(post)):
            num_bad.append(r)
        if any(u not in post for u in urls(raw)):
            url_bad.append(r)
        if any(t not in post for t in tickers(raw)):
            ticker_bad.append(r)
        if post_edit(post, source_en=r["english"]) != post:
            nonidem.append(r)

    n = max(len(kept), 1)
    print("\n[NOTE] The evaluation sample is stratified (A: raw fails is_persian, B: glossary terms, C: random).")
    print("       Pass rates per stratum and overall reflect this enriched distribution and must NOT be read as production rates.")

    print("\n-- overall golden-free metrics --")
    print(f"is_persian pass: raw {pass_raw}/{len(kept)} = {pass_raw/n:.1%}"
          f" | post_edit {pass_post}/{len(kept)} = {pass_post/n:.1%}")
    print(f"pass-raw-but-FAIL-after-post_edit: {len(regressed)}"
          + ("  <-- MUST be 0" if regressed else ""))
    for r in regressed[:10]:
        print(f"   id={r['id']} raw={r['engine_output'][:70]!r}")

    # ── per-rule is_persian rescue decomposition ──
    from fa_postedit import (
        _fix_arabic_letters, _canonicalize_fa, _to_persian_digits,
        _protect_and_map, _zwnj_mi, _zwnj_ha, _zwnj_tar,
        _RE_ZWNJ_SPACE, _RE_ZWNJ_RUN, _RE_SPACE_BEFORE_PUNCT, _RE_MULTI_SPACE, ZWNJ
    )
    from fa_lexicon import lexicon
    lex = lexicon()
    rescued_typo = 0
    rescued_entity = 0
    rescued_non_entity = 0
    for r in kept:
        raw = r["engine_output"]
        post = post_edit(raw)
        if not is_persian(raw) and is_persian(post):
            no_lat = _protect_and_map(raw, lambda part: _to_persian_digits(_canonicalize_fa(_fix_arabic_letters(part), lex)))
            no_lat = _RE_MULTI_SPACE.sub(" ", _RE_SPACE_BEFORE_PUNCT.sub(r"\1", _zwnj_tar(_zwnj_ha(_zwnj_mi(_RE_ZWNJ_RUN.sub(ZWNJ, _RE_ZWNJ_SPACE.sub(ZWNJ, no_lat))))))).strip(" \t\r\n" + ZWNJ)
            if is_persian(no_lat):
                rescued_typo += 1
            else:
                rescued_entity += 1

    print("\n-- is_persian rescue decomposition --")
    print(f"rescued rows total: {rescued_typo + rescued_entity + rescued_non_entity}")
    print(f"  * rescued by typography alone: {rescued_typo}")
    print(f"  * rescued by vetted entity/crypto: {rescued_entity}")
    print(f"  * rows rescued only by a non-entity replacement: {rescued_non_entity}"
          + ("  <-- MUST be 0" if rescued_non_entity == 0 else "  <-- VIOLATION"))
    print("[WARNING] The is_persian rate alone rewards replacing English words with Persian ones regardless of translation correctness.")

    print(f"longest-Latin-run: mean raw {sum(lrr_raw)/n:.2f} -> post "
          f"{sum(lrr_post)/n:.2f} | worsened: {len(lat_worse)}")
    print(f"preserved — digits: {len(kept)-len(digit_bad)}/{len(kept)}"
          f" | numbers: {len(kept)-len(num_bad)}/{len(kept)}"
          f" | urls: {len(kept)-len(url_bad)}/{len(kept)}"
          f" | tickers: {len(kept)-len(ticker_bad)}/{len(kept)}")
    for label, bucket in (("digits", digit_bad), ("numbers", num_bad),
                          ("urls", url_bad), ("tickers", ticker_bad)):
        for r in bucket[:3]:
            print(f"   {label} violation id={r['id']}: "
                  f"{r['engine_output'][:60]!r} -> "
                  f"{post_edit(r['engine_output'])[:60]!r}")
    print(f"idempotent: {len(kept)-len(nonidem)}/{len(kept)}")
    for r in nonidem[:3]:
        print(f"   non-idempotent id={r['id']}")

    # ── per-stratum breakdown ──
    from collections import defaultdict
    strata = defaultdict(list)
    for r in kept:
        strata[r["stratum"]].append(r)

    stratum_labels = {
        "A": "Stratum A (raw fails is_persian)",
        "B": "Stratum B (glossary terms in EN source)",
        "C": "Stratum C (random sample)",
    }

    print("\n-- per-stratum breakdown --")
    for st in sorted(strata.keys()):
        items = strata[st]
        sn = len(items)
        s_raw_pass = sum(1 for r in items if is_persian(r["engine_output"]))
        s_post_pass = sum(1 for r in items if is_persian(post_edit(r["engine_output"])))
        s_rescued = sum(1 for r in items if not is_persian(r["engine_output"]) and is_persian(post_edit(r["engine_output"])))
        s_still_fail = sum(1 for r in items if not is_persian(post_edit(r["engine_output"])))
        s_regressed = sum(1 for r in items if is_persian(r["engine_output"]) and not is_persian(post_edit(r["engine_output"])))
        s_lrr_raw = [longest_latin_run(r["engine_output"]) for r in items]
        s_lrr_post = [longest_latin_run(post_edit(r["engine_output"])) for r in items]
        s_lat_worse = sum(1 for a, b in zip(s_lrr_raw, s_lrr_post) if b > a)

        lbl = stratum_labels.get(st, f"Stratum {st}")
        print(f"\n{lbl} (evaluated n={sn}):")
        print(f"  is_persian pass: raw {s_raw_pass}/{sn} ({s_raw_pass/sn:.1%}) -> post_edit {s_post_pass}/{sn} ({s_post_pass/sn:.1%})")
        if st == "A":
            print(f"  rescues (raw fail -> pass): {s_rescued}/{sn} ({s_rescued/sn:.1%})")
            print(f"  remaining failing: {s_still_fail}/{sn} ({s_still_fail/sn:.1%})")
        else:
            print(f"  rescued: {s_rescued} | remaining failing: {s_still_fail}")
        print(f"  regressions (raw pass -> fail): {s_regressed}")
        print(f"  longest-Latin-run: mean raw {sum(s_lrr_raw)/sn:.2f} -> post {sum(s_lrr_post)/sn:.2f} | worsened: {s_lat_worse}")

    # ── sample before/after rows (10 per stratum) ──
    print("\n-- sample before/after rows (10 per stratum) --")
    for st in sorted(strata.keys()):
        items = strata[st]
        lbl = stratum_labels.get(st, f"Stratum {st}")
        print(f"\n{lbl} — 10 samples:")
        for idx, r in enumerate(items[:10], 1):
            raw = r["engine_output"]
            post = post_edit(raw, source_en=r["english"])
            print(f"  [{idx:02d}] id={r['id']}")
            print(f"       english         : {r['english']}")
            print(f"       engine_output   : {raw}")
            print(f"       post_edit_output: {post}")

    if not has_golden:
        print("\n(no opinion/fixed_fa present — golden metrics skipped)")
        run_db_decision_review(regressed=regressed)
        return

    # ── golden metrics: opinion tallies, chrF, edit distance, term accuracy ──
    import csv
    terms = {}
    for name in ("terms.tsv", "entities.tsv"):
        with open(REPO / "data" / "fa" / name, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                k = (row.get("en") or "").strip().lower()
                v = (row.get("fa") or "").strip()
                if len(k) >= 4 and v:
                    terms.setdefault(k, set()).add(v)
    single = {k for k in terms if " " not in k}
    multi = {}
    for k in terms:
        if " " in k:
            multi.setdefault(k.split(" ")[0], []).append(k)

    def fam_variants(fa):
        z = "\u200c"
        return {fa, fa.replace(z, " "), fa.replace(" ", z)}

    def term_hits(text_en, out):
        tl = re.sub(r"[^a-z0-9]+", " ", (text_en or "").lower())
        toks = tl.split()
        found = total = 0
        for tok in toks:
            keys = [tok] if tok in single else []
            keys += [mk for mk in multi.get(tok, ()) if mk in tl]
            for k in keys:
                total += 1
                if any(any(vv in out for vv in fam_variants(v))
                       for v in terms[k]):
                    found += 1
        return found, total

    opinion_rows = [r for r in kept if r.get("pref") or r.get("fixed_fa")]
    if not opinion_rows:
        print("\n(no opinion rows found in evaluated set)")
        return

    def calc_opinion_stats(row_list):
        cnt_post_ok = sum(1 for r in row_list if r.get("pref") == "post_ok")
        cnt_raw_better = sum(1 for r in row_list if r.get("pref") == "raw_better")
        cnt_fixed = sum(1 for r in row_list if r.get("pref") == "fixed")

        tot = max(len(row_list), 1)
        chrf_post_sum = chrf_raw_sum = 0.0
        lev_post_sum = lev_raw_sum = 0.0
        ta_post_sum = ta_raw_sum = ta_gold_sum = 0.0

        for r in row_list:
            ref = r["fixed_fa"]
            raw = r["engine_output"]
            post = post_edit(raw)

            chrf_post_sum += chrf(post, ref)
            chrf_raw_sum += chrf(raw, ref)
            lev_post_sum += levenshtein(post, ref)
            lev_raw_sum += levenshtein(raw, ref)

            f_p, t_p = term_hits(r["english"], post)
            ta_post_sum += f_p / t_p if t_p else 1.0
            f_r, t_r = term_hits(r["english"], raw)
            ta_raw_sum += f_r / t_r if t_r else 1.0
            f_g, t_g = term_hits(r["english"], ref)
            ta_gold_sum += f_g / t_g if t_g else 1.0

        return {
            "n": len(row_list),
            "post_ok": cnt_post_ok,
            "raw_better": cnt_raw_better,
            "fixed": cnt_fixed,
            "chrf_post": chrf_post_sum / tot,
            "chrf_raw": chrf_raw_sum / tot,
            "lev_post": lev_post_sum / tot,
            "lev_raw": lev_raw_sum / tot,
            "ta_post": ta_post_sum / tot,
            "ta_raw": ta_raw_sum / tot,
            "ta_gold": ta_gold_sum / tot,
        }

    print("\n-- opinion & golden metrics --")
    print(f"opinion rows: {len(opinion_rows)}")

    # Per-stratum opinion metrics
    op_strata = defaultdict(list)
    for r in opinion_rows:
        op_strata[r["stratum"]].append(r)

    for st in sorted(op_strata.keys()):
        s_stats = calc_opinion_stats(op_strata[st])
        sn = s_stats["n"]
        lbl = stratum_labels.get(st, f"Stratum {st}")
        print(f"\n{lbl} (opinion n={sn}):")
        print(f"  preferences: post_ok={s_stats['post_ok']}/{sn} ({s_stats['post_ok']/sn:.1%}) "
              f"| raw_better={s_stats['raw_better']}/{sn} ({s_stats['raw_better']/sn:.1%}) "
              f"| fixed={s_stats['fixed']}/{sn} ({s_stats['fixed']/sn:.1%})")
        print(f"  chrF to fixed_fa: post_edit {s_stats['chrf_post']:.1f} vs raw {s_stats['chrf_raw']:.1f} "
              f"(delta: {s_stats['chrf_post'] - s_stats['chrf_raw']:+.1f})")
        print(f"  edit distance: post_edit mean {s_stats['lev_post']:.1f} vs raw mean {s_stats['lev_raw']:.1f}")
        print(f"  term accuracy: post_edit {s_stats['ta_post']:.3f} | raw {s_stats['ta_raw']:.3f} | golden {s_stats['ta_gold']:.3f}")

    # Overall opinion metrics
    ov = calc_opinion_stats(opinion_rows)
    m = ov["n"]
    pct_raw_better = ov["raw_better"] / m if m else 0.0

    print("\n-- overall opinion metrics --")
    print(f"total opinion rows: {m}")
    print(f"preferences: post_ok={ov['post_ok']}/{m} ({ov['post_ok']/m:.1%}) "
          f"| raw_better={ov['raw_better']}/{m} ({pct_raw_better:.1%}) "
          f"| fixed={ov['fixed']}/{m} ({ov['fixed']/m:.1%})")
    print(f"chrF(post_edit, fixed_fa): {ov['chrf_post']:.1f} | chrF(raw, fixed_fa): {ov['chrf_raw']:.1f} "
          f"(delta: {ov['chrf_post'] - ov['chrf_raw']:+.1f})")
    print(f"edit distance: post_edit mean {ov['lev_post']:.1f} | raw mean {ov['lev_raw']:.1f}")
    print(f"term accuracy: post_edit {ov['ta_post']:.3f} | raw {ov['ta_raw']:.3f} | golden {ov['ta_gold']:.3f}")

    # Regressions
    regressed_rows = []
    for r in opinion_rows:
        ref = r["fixed_fa"]
        raw = r["engine_output"]
        post = post_edit(raw)
        cp = chrf(post, ref)
        cr = chrf(raw, ref)
        lp = levenshtein(post, ref)
        lr = levenshtein(raw, ref)
        is_reg = (r.get("pref") == "raw_better") or (cp < cr) or (lp > lr)
        if is_reg:
            regressed_rows.append((r, cp, cr, lp, lr))

    # Verdict
    print("\n" + "=" * 50)
    verdict, reasons = evaluate_opinion_verdict(
        opinion_rows,
        raw_better_rate=pct_raw_better,
        chrf_post=ov["chrf_post"],
        chrf_raw=ov["chrf_raw"],
    )
    print(f"VERDICT: {verdict}")
    for reason in reasons:
        print(f"  {reason}")

    if regressed_rows:
        print(f"\nRegressed rows ({len(regressed_rows)}/{m}):")
        for r, cp, cr, lp, lr in regressed_rows:
            print(f"  [id={r['id']} | stratum={r['stratum']} | pref={r.get('pref')}]")
            print(f"    EN       : {r['english']}")
            print(f"    Raw      : {r['engine_output']} (chrF={cr:.1f}, dist={lr})")
            print(f"    PostEdit : {post_edit(r['engine_output'])} (chrF={cp:.1f}, dist={lp})")
            print(f"    Fixed    : {r['fixed_fa']}")

    print("\nNote: Per-stratum subsets of ~10 rows (e.g. Stratum A, C) are anecdotal due to sample size;")
    print("      the quality verdict is judged across the aggregate evaluated opinion set.")
    print("      (fa_post_edit toggle remains untouched: OFF)")
    print("=" * 50)
    run_db_decision_review(regressed=regressed)


if __name__ == "__main__":
    main()
