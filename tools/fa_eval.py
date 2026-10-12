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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from translate import is_persian, longest_latin_run      # noqa: E402
from fa_postedit import post_edit                        # noqa: E402

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
            fixed = (o.get("fixed_fa") or o.get("fixed") or "").strip()
            rows.append({"id": str(o.get("id", "")),
                         "english": o.get("english") or o.get("source") or "",
                         "engine_output": o.get("engine_output")
                         or o.get("output") or "",
                         "fixed_fa": fixed,
                         "stratum": o.get("stratum", "?")})
            has_golden = has_golden or bool(fixed)
        return rows, "golden.jsonl", has_golden
    tpl = REPO / "data" / "fa" / "golden_template.tsv"
    lines = tpl.read_text(encoding="utf-8-sig").splitlines()
    for i, line in enumerate(lines[1:]):
        c = line.split("\t")
        if len(c) < 5:
            continue
        rows.append({"id": c[0], "english": c[1], "engine_output": c[2],
                     "fixed_fa": c[4].strip(),
                     "stratum": "ABC"[min(i // 100, 2)]})
        has_golden = has_golden or bool(c[4].strip())
    return rows, "golden_template.tsv", has_golden


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
        raw, post = r["engine_output"], post_edit(r["engine_output"])
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
        if post_edit(post) != post:
            nonidem.append(r)

    n = max(len(kept), 1)
    print("\n-- golden-free metrics --")
    print(f"is_persian pass: raw {pass_raw}/{len(kept)} = {pass_raw/n:.1%}"
          f" | post_edit {pass_post}/{len(kept)} = {pass_post/n:.1%}")
    print(f"pass-raw-but-FAIL-after-post_edit: {len(regressed)}"
          + ("  <-- MUST be 0" if regressed else ""))
    for r in regressed[:10]:
        print(f"   id={r['id']} raw={r['engine_output'][:70]!r}")
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

    if not has_golden:
        print("\n(no fixed_fa present — golden metrics skipped)")
        return

    # ── golden metrics: term accuracy, chrF, edit distance ──
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
        z = "\\u200c"
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

    gold = [r for r in kept if r["fixed_fa"]]
    ta_post = ta_gold = g_chrf = g_lev_post = g_lev_raw = 0.0
    for r in gold:
        f, t = term_hits(r["english"], post_edit(r["engine_output"]))
        ta_post += f / t if t else 1.0
        f2, t2 = term_hits(r["english"], r["fixed_fa"])
        ta_gold += f2 / t2 if t2 else 1.0
        g_chrf += chrf(post_edit(r["engine_output"]), r["fixed_fa"])
        g_lev_post += levenshtein(post_edit(r["engine_output"]), r["fixed_fa"])
        g_lev_raw += levenshtein(r["engine_output"], r["fixed_fa"])
    m = max(len(gold), 1)
    print("\n-- golden metrics (over corrected rows) --")
    print(f"corrected rows: {len(gold)}")
    print(f"term accuracy: post_edit {ta_post/m:.3f} | golden {ta_gold/m:.3f}")
    print(f"chrF(post_edit, golden): {g_chrf/m:.1f}")
    print(f"edit distance to golden: post_edit mean {g_lev_post/m:.1f} "
          f"| raw mean {g_lev_raw/m:.1f}")


if __name__ == "__main__":
    main()
