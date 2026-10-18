#!/usr/bin/env python3
"""
Phase 0 audit — measure the current EN->FA pipeline quality.
==============================================================
Read-only by construction:
  * the SQLite DB opens with file:...?mode=ro,
  * .translate_cache.json is read from a TEMP COPY (never the real file),
  * translate.py is imported for its gate functions only
    (is_persian / persian_share / longest_latin_run / _looks_persian);
    translate_many() and save_cache() are never called, so no cache write
    and no network request can happen.

Writes: docs/fa_audit.md
Run:    .venv/Scripts/python.exe tools/fa_build/audit.py
"""
import hashlib
import json
import re
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

from translate import (  # noqa: E402  (pure gate helpers; no I/O on import)
    _FA_CHAR_RE, _looks_persian, is_persian, longest_latin_run, persian_share,
)

DB = BASE / ".mohmd_news.db"
CACHE = BASE / ".translate_cache.json"
VENDOR = BASE / "vendor" / "persian-crypto-words"
OUT_MD = BASE / "docs" / "fa_audit.md"

LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'&./#-]*[A-Za-z0-9]|[A-Za-z]")
EN_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'&.%/-]*")
FA_WORD_RE = re.compile(r"[\u0600-\u06FF\u200c]+")   # whole block: includes Persian ی (U+06CC) and ک (U+06A9)
FA_DIGITS_RE = re.compile(r"[\u06F0-\u06F9]")
ASCII_DIGITS_RE = re.compile(r"[0-9]")


# --------------------------------------------------------------------------- helpers

def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def fail_kind(text):
    """None when the text passes translate.is_persian, else echo|half|low."""
    if is_persian(text):
        return None
    if not _FA_CHAR_RE.search(text or ""):
        return "echo"                      # no Persian letters at all
    if longest_latin_run(text) >= 4:
        return "half"                      # Latin run >= 4
    return "low"                           # Persian letters, share < 0.45


def pct(a, b):
    return f"{100.0 * a / b:.1f}%" if b else "—"


def trunc(s, n):
    s = str(s).replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def norm_fa(s: str) -> str:
    """ي/ك -> ی/ک, strip tatweel (matches the Phase-1 normalization rule)."""
    return s.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9").replace("\u0640", "")


def fa_words(text: str):
    """Persian word tokens, ZWNJ kept inside the token."""
    return [w for w in FA_WORD_RE.findall(text) if w.strip("\u200c")]


def fa_key(token: str) -> str:
    """Canonical key for surface comparison: no ZWNJ, no space."""
    return token.replace("\u200c", "").replace(" ", "")


def md_escape(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


# crude but disclosed source-language screen (function words per language)
LANG_MARKERS = {
    "en": [" the ", " and ", " of ", " to ", " in ", " for ", " with ", " is ",
           " on ", " that "],
    "fr": [" le ", " la ", " les ", " des ", " est ", " une ", " dans ",
           " pour ", " avec ", " que ", " sur "],
    "de": [" der ", " die ", " das ", " und ", " ist ", " mit ", " für ",
           " eine ", " den ", " von ", " zu "],
    "es": [" el ", " los ", " las ", " que ", " una ", " por ", " con ",
           " para ", " del ", " est "],
    "nl": [" het ", " een ", " van ", " niet ", " met ", " voor ", " op ",
           " zijn ", " door "],
    "it": [" il ", " che ", " per ", " una ", " con ", " del ", " non ",
           " sono ", " più "],
    "pt": [" que ", " uma ", " por ", " com ", " para ", " não ", " dos "],
    "pl": [" się ", " nie ", " na ", " że ", " do ", " jest ", " jako ",
           " przez "],
    "tr": [" ve ", " bir ", " için ", " ile ", " olarak ", " çok ", " daha "],
    "id": [" yang ", " untuk ", " dengan ", " dari ", " ini ", " tidak ",
           " pada ", " akan "],
}


def detect_lang(text):
    t = " " + (text or "").lower() + " "
    scores = {lg: sum(t.count(m) for m in ms) for lg, ms in LANG_MARKERS.items()}
    if max(scores.values()) < 2:
        return "unknown"
    non_en = {lg: c for lg, c in scores.items() if lg != "en"}
    bn = max(non_en, key=lambda lg: non_en[lg])
    return bn if non_en[bn] > scores["en"] else "en"


# --------------------------------------------------------------------------- data

def load_data():
    with tempfile.TemporaryDirectory() as td:          # READ A COPY, never the real file
        tmp = Path(td) / "cache_copy.json"
        shutil.copyfile(CACHE, tmp)
        cache = json.loads(tmp.read_text(encoding="utf-8"))

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT title, title_fa, summary, summary_fa FROM articles"
    ).fetchall()
    con.close()
    return cache, rows


def build_pairs(rows):
    """(source, output) pairs of what the dashboard publishes."""
    pairs = []
    for title, title_fa, summary, summary_fa in rows:
        if title and title_fa:
            pairs.append((title, title_fa))
        if summary and len(summary) >= 40 and summary_fa:
            pairs.append((summary[:1000], summary_fa))
    return pairs


def build_source_index(rows):
    """md5(text) -> text for every candidate English source fed to translate."""
    idx = {}
    for title, _tf, summary, _sf in rows:
        if title:
            idx.setdefault(md5(title), title)
        if summary and len(summary) >= 40:
            idx.setdefault(md5(summary[:1000]), summary[:1000])
            idx.setdefault(md5(summary), summary)
    return idx


# --------------------------------------------------------------------------- sections

def sec_facts() -> str:
    return """\
### 1. Engine facts confirmed by reading `translate.py`

| # | Fact | Evidence (translate.py) |
|---|------|--------------------------|
| A1 | Every non-empty engine result is cached unconditionally, including English echoes; `to_persian()`'s "retry" goes through `translate_one()` → `translate_many()`, which re-reads the very same poisoned entry — no second network request ever happens for a failed text. | cache write: `translate_many` lines 289-298; retry path: `to_persian` 228-240, `translate_one` 304-307 |
| A2 | `_looks_persian()` (>25% Persian chars over *all* chars) identity-maps mixed texts; the `is_persian()` gate (≥45% Persian letters, Latin run < 4) then rejects them, and `to_persian()` cannot rescue them because `translate_one()` hits the same identity bypass. | `_looks_persian` 167-173, identity map 264-267; gate 216-225 |
| A3 | `_translate_batch()` sends up to 16 `q` params in one GET; non-200 (except 429/5xx retries) → `[]` (whole batch stays English); short responses are padded with `""` **at the end**, so a mid-drop misaligns translations with sources. | 131-156, pad at 143-144 |
| A4 | Cached values already have `fa_digits` applied, and the cache key is `md5(source)` only — the `persian_digits` flag is not part of the key. | store at 293-297; key at 60-61 |
"""


def sec_publish(rows) -> str:
    t_total = sum(1 for r in rows if r[0])
    t_out = sum(1 for r in rows if r[1])
    t_pass = sum(1 for r in rows if r[1] and is_persian(r[1]))
    t_fail_kinds = Counter(fail_kind(r[1]) for r in rows if r[1] and not is_persian(r[1]))

    s_total = sum(1 for r in rows if r[2] and len(r[2]) >= 40)
    s_out = sum(1 for r in rows if r[3])
    s_pass = sum(1 for r in rows if r[3] and is_persian(r[3]))
    s_fail_kinds = Counter(fail_kind(r[3]) for r in rows if r[3] and not is_persian(r[3]))

    t_src_fa = sum(1 for r in rows if r[0] and _FA_CHAR_RE.search(r[0]))
    s_src_fa = sum(1 for r in rows if r[2] and _FA_CHAR_RE.search(r[2] or ""))

    lang_t = Counter(detect_lang(r[0]) for r in rows
                     if r[0] and r[1] and not is_persian(r[1]))
    non_en_t = sum(c for lg, c in lang_t.items() if lg not in ("en", "unknown"))
    top_langs = ", ".join(f"{lg} {c}" for lg, c in
                          sorted(((lg, c) for lg, c in lang_t.items()
                                  if lg not in ("en", "unknown")),
                                 key=lambda x: -x[1])[:4]) or "—"

    lines = [
        "### 2. What the dashboard publishes (`title_fa` / `summary_fa`)",
        "",
        f"- Titles: **{t_out}/{t_total}** rows carry `title_fa`; "
        f"**{t_pass}/{t_out} pass is_persian = {pct(t_pass, t_out)}** "
        f"(**{t_out - t_pass} failing**).",
        f"- Summaries (source ≥ 40 chars): **{s_out}/{s_total}** carry `summary_fa`; "
        f"**{s_pass}/{s_out} pass = {pct(s_pass, s_out)}** "
        f"(**{s_out - s_pass} failing**).",
        f"- Failure reasons — titles: pure echo (no Persian letters) "
        f"**{t_fail_kinds['echo']}**, half-translated (Latin run ≥ 4) "
        f"**{t_fail_kinds['half']}**, low Persian share (< 45%) **{t_fail_kinds['low']}**.",
        f"- Failure reasons — summaries: echo **{s_fail_kinds['echo']}**, "
        f"half **{s_fail_kinds['half']}**, low share **{s_fail_kinds['low']}**.",
        f"- Failure reasons — source language (heuristic screen): "
        f"**{non_en_t}/{t_out - t_pass} = {pct(non_en_t, t_out - t_pass)}** of failing "
        f"titles have a non-English source (top: {top_langs}); with `sl=en` those "
        "texts cannot be translated by the endpoint at all (see §9).",
        f"- Source side: **{t_src_fa}/{t_total}** titles and **{s_src_fa}/{s_total}** "
        "summaries are natively Persian (the rest are English — or French/Spanish, see §5).",
        "",
    ]
    return "\n".join(lines)


def sec_cache(cache, src_idx) -> str:
    vals = {k: v for k, v in cache.items() if isinstance(v, str) and v.strip()}
    n = len(vals)
    kinds = Counter(fail_kind(v) for v in vals.values())
    fails = n - kinds[None]
    joined = 0
    joined_echo_same = 0
    fa_digit_vals = 0
    for k, v in vals.items():
        if FA_DIGITS_RE.search(v):
            fa_digit_vals += 1
        if k in src_idx:
            joined += 1
            if fail_kind(v) == "echo" and v == src_idx[k]:
                joined_echo_same += 1
    lines = [
        "### 3. Cache audit (read-only copy of `.translate_cache.json`)",
        "",
        f"- Entries: **{n}** (read from a temp copy; real file untouched).",
        f"- Pass is_persian: **{n - fails} = {pct(n - fails, n)}**; "
        f"**fail: {fails} = {pct(fails, n)}**.",
        f"- Failure kinds — pure echo (no Persian letters): **{kinds['echo']}**, "
        f"half-translated (Latin run ≥ 4): **{kinds['half']}**, "
        f"low Persian share (< 45%): **{kinds['low']}**.",
        f"- Entries whose md5 key joins back to an `articles` source: "
        f"**{joined}/{n} = {pct(joined, n)}** (the rest come from ideas/paragraphs/events).",
        f"- Of the joined *echo* failures, **{joined_echo_same} are byte-identical to "
        "their source** — the endpoint literally answered with the input again (A1).",
        f"- Values containing Persian digits: **{fa_digit_vals}/{n} = "
        f"{pct(fa_digit_vals, n)}** — `fa_digits` runs before the store (A4).",
        "",
    ]
    return "\n".join(lines)


def sec_identity(rows) -> str:
    """A2/B: items identity-mapped by _looks_persian but failing is_persian."""
    texts = []
    for title, title_fa, summary, summary_fa in rows:
        if title:
            texts.append(("title", title, title_fa or ""))
        if summary and len(summary) >= 40:
            texts.append(("summary", summary[:1000], summary_fa or ""))
    never = [t for t in texts if _looks_persian(t[1]) and not is_persian(t[1])]
    ident_pub = [t for t in never if t[2] and t[2].split() == t[1].split()]
    lines = [
        "### 4. Identity-mapped by `_looks_persian` but rejected by `is_persian` "
        "(never rescuable today, A2)",
        "",
        f"- Texts flowing into `translate_many` (titles + summaries ≥ 40 chars): "
        f"**{len(texts)}**.",
        f"- `_looks_persian(t) and not is_persian(t)`: **{len(never)}** "
        f"= {pct(len(never), len(texts))}.",
        f"- Of those, currently published unchanged (output == input): "
        f"**{len(ident_pub)}**.",
        "",
    ]
    if never:
        lines.append("Examples:")
        lines.append("")
        for kind_, src, out in never[:5]:
            lines.append(f"- ({kind_}) `{md_escape(trunc(src, 90))}` → "
                         f"`{md_escape(trunc(out or src, 90))}` "
                         f"(share={persian_share(src):.2f}, run={longest_latin_run(src)})")
        lines.append("")
    return "\n".join(lines)


def sec_latin_tokens(rows, pairs) -> str:
    """100 most frequent Latin tokens left in published Persian outputs."""
    total = Counter()
    in_fail = Counter()
    in_pass = Counter()
    example = {}
    for _src, out in pairs:
        for tok in LATIN_TOKEN_RE.findall(out):
            tl = tok.lower()
            total[tl] += 1
            if is_persian(out):
                in_pass[tl] += 1
            else:
                in_fail[tl] += 1
            if tl not in example:
                i = out.find(tok)
                example[tl] = trunc(out[max(0, i - 25): i + len(tok) + 25], 60)
    top = total.most_common(100)
    lines = [
        "### 5. 100 most frequent untranslated Latin tokens in published outputs",
        "",
        "Counted over every `title_fa` + `summary_fa`; `in failing` = occurrences "
        "inside outputs that fail `is_persian`.",
        "",
        "| # | token | count | in failing | in passing | example context |",
        "|---|-------|------:|-----------:|-----------:|-----------------|",
    ]
    for i, (tok, c) in enumerate(top, 1):
        lines.append(f"| {i} | `{md_escape(tok)}` | {c} | {in_fail[tok]} | "
                     f"{in_pass[tok]} | {md_escape(example.get(tok, ''))} |")
    lines.append("")
    return "\n".join(lines)


def sec_ngrams(rows) -> str:
    """200 most frequent source n-grams (1-4 words) in headlines + renderings."""
    titles = [(t, fa) for t, fa, _s, _sf in rows if t and fa]
    counts = Counter()
    for src, _out in titles:
        toks = [t for t in EN_TOKEN_RE.findall(src.lower()) if not t.isdigit()]
        for n in (1, 2, 3, 4):
            for i in range(len(toks) - n + 1):
                counts[" ".join(toks[i:i + n])] += 1
    top = sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:200]

    def examples(gram):
        gt = gram.split()
        hits = []
        for src, out in titles:
            toks = EN_TOKEN_RE.findall(src.lower())
            for i in range(len(toks) - len(gt) + 1):
                if toks[i:i + len(gt)] == gt:
                    hits.append((src, out))
                    break
        hits.sort(key=lambda x: len(x[0]))
        return hits[:2]

    def cells(gram):
        ex = examples(gram)
        return " ／ ".join(
            f"{md_escape(trunc(s, 45))} → {md_escape(trunc(o, 55))}" for s, o in ex
        ) or "—"

    lines = [
        "### 6. 200 most frequent source n-grams (1–4 words) in headlines, "
        "with current Persian renderings",
        "",
        "Pure-digit n-grams excluded (numbers are copied verbatim, not glossary "
        "targets). Examples are the shortest headlines containing the n-gram; "
        "the rendering shown is their current `title_fa`.",
        "",
        "| # | n-gram | n | headlines | example: source → output |",
        "|---|--------|---|----------:|--------------------------|",
    ]
    for i, (gram, c) in enumerate(top, 1):
        lines.append(f"| {i} | `{md_escape(gram)}` | {len(gram.split())} | {c} | "
                     f"{cells(gram)} |")
    for n in (3, 4):
        sub = [(g, c) for g, c in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
               if len(g.split()) == n][:20]
        lines += ["", f"Appendix — top {n}-grams:", "",
                  "| n-gram | headlines | example: source → output |",
                  "|--------|----------:|--------------------------|"]
        for gram, c in sub:
            lines.append(f"| `{md_escape(gram)}` | {c} | {cells(gram)} |")
    lines.append("")
    return "\n".join(lines)


def surface_pattern(fa_form: str):
    """Regex matching surface variants of a Persian rendering:
    ی/ك class tolerance, optional ZWNJ inside words, space/ZWNJ between words."""
    fa = norm_fa(fa_form)
    words = []
    for w in fa.split():
        chars = []
        for ch in w:
            if ch in "\u06cc\u064a":
                chars.append("[\u06cc\u064a]")
            elif ch in "\u0643\u06a9":
                chars.append("[\u0643\u06a9]")
            else:
                chars.append(re.escape(ch))
        words.append("\u200c*".join(chars))
    return re.compile(r"[\s\u200c]*".join(words))


def load_vendor():
    """crypto_names.txt: triples, in one of two orientations —
    (EN, FA, ticker) or (FA, ticker, EN); irregular triples are skipped."""
    lines = [ln.strip() for ln in
             (VENDOR / "crypto_names.txt").read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    trip = {}
    skipped = 0
    for i in range(0, len(lines) - 2, 3):
        a, b, c = lines[i], lines[i + 1], lines[i + 2]
        has_fa = lambda s: bool(re.search(r"[\u0600-\u06FF]", s))
        if not has_fa(a) and has_fa(b):
            en, fa = a, b                           # (EN, FA, ticker)
        elif has_fa(a) and not has_fa(b):
            en, fa = c, a                           # (FA, ticker, EN)
        else:
            skipped += 1
            continue
        trip.setdefault(en, {"fa": set(), "tickers": set()})
        trip[en]["fa"].add(fa)
    fa_list = [ln.strip() for ln in
               (VENDOR / "list.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    return trip, fa_list, skipped


def sec_term_inconsistency(pairs) -> str:
    """Inconsistent Persian renderings of the same English term.

    Method A (vendor terms): every surface variant of the known FA rendering
    inside outputs whose source contains the EN term.
    Method B (frequent EN terms): top Persian word/bigram candidates by
    conditional count+lift; two strong candidates that *rarely co-occur* are
    alternates; candidates that co-occur are components of one phrase.
    """
    trip, _fa_list, vendor_skipped = load_vendor()

    out_words, out_wset, out_bset = [], [], []
    for _src, out in pairs:
        ws = fa_words(out)
        out_words.append(ws)
        out_wset.append(set(ws))
        out_bset.append({ws[i] + " " + ws[i + 1] for i in range(len(ws) - 1)})

    bg_word = Counter(w for ws in out_words for w in ws)
    bg_big = Counter(b for bs in out_bset for b in bs)
    n_out = len(pairs) or 1
    total_words = sum(bg_word.values()) or 1
    total_big = sum(bg_big.values()) or 1

    en_freq = Counter()
    for src, _o in pairs:
        en_freq.update({t for t in EN_TOKEN_RE.findall(src.lower()) if not t.isdigit()})
    terms = [t for t, c in en_freq.most_common(200) if len(t) >= 3 and c >= 40][:80]
    for en in trip:
        el = en.lower()
        if el in en_freq and en_freq[el] >= 40 and el not in terms:
            terms.append(el)

    def src_has(src, term):
        if " " in term:
            return re.search(r"\b" + re.escape(term) + r"\b", src.lower()) is not None
        return term in EN_TOKEN_RE.findall(src.lower())

    lines = [
        "### 7. Inconsistent renderings of the same finance term",
        "",
        "**Method A — known renderings (vendor `crypto_names.txt`):** all surface "
        "variants found in outputs of sources containing the term "
        f"(≥ 15 outputs; variant counted if seen ≥ 5×; {vendor_skipped} vendor "
        "triples skipped as irregular):",
        "",
        "| EN term | FA rendering | surface variants (count) | verdict |",
        "|---------|--------------|--------------------------:|---------|",
    ]
    a_flagged = 0
    for en in sorted(trip):
        for form in sorted(trip[en]["fa"]):
            hits = [(src, out) for src, out in pairs if src_has(src, en.lower())]
            if len(hits) < 15:
                continue
            pat = surface_pattern(form)
            surf = Counter()
            for _src, out in hits:
                for m in pat.finditer(out):
                    surf[m.group(0)] += 1
            if sum(surf.values()) < 10:
                continue
            multi = {s: c for s, c in surf.items() if c >= 5}
            verdict = ("inconsistent ✗" if len(multi) >= 2 else "ok ✓")
            if len(multi) >= 2:
                a_flagged += 1
            variants = ", ".join(
                f"«{md_escape(s)}»×{c}" for s, c in
                sorted(surf.items(), key=lambda x: -x[1])[:4])
            lines.append(f"| `{md_escape(en)}` | {md_escape(form)} | {variants} | "
                         f"{verdict} |")
    if a_flagged == 0:
        lines.append("| — | — | — | no Method-A inconsistency found |")

    lines += [
        "",
        "**Method B — data-driven candidates** (frequent EN terms; word/bigram "
        "candidates with count ≥ max(6, 12% of matching outputs) and lift ≥ 5 "
        "vs background; flagged when two strong candidates rarely co-occur "
        "(obs < 0.5·expected) and neither key contains the other). Flags "
        "include polysemy (one English word with several legitimate Persian "
        "words); only stylistic alternates of the same meaning are glossary "
        "targets — sorted by matched-set size, smallest first:",
        "",
        "| EN term | outputs | candidate renderings (count) | obs/exp co-occur | verdict |",
        "|---------|--------:|-----------------------------|-----------------:|---------|",
    ]
    b_flagged = []
    for term in terms:
        M = [i for i, (src, _o) in enumerate(pairs) if src_has(src, term)]
        m = len(M)
        if m < 15:
            continue
        cw, cb = Counter(), Counter()
        for i in M:
            cw.update(out_wset[i])
            cb.update(out_bset[i])
        cands = {}
        for kind_, cnt, bg, tot in (("w", cw, bg_word, total_words),
                                    ("b", cb, bg_big, total_big)):
            for tok, c in cnt.most_common(40):
                if c < max(6, 0.12 * m):
                    break
                if len(fa_key(tok)) < 3 or c / m > 0.8:
                    continue        # fragment or stopword, not a rendering
                p_bg = bg[tok] / tot
                if p_bg <= 0:
                    continue
                lift = (c / m) / p_bg
                if lift >= 5:
                    prev = cands.get(tok)
                    if prev is None or prev[0] < c:
                        cands[tok] = (c, kind_, lift)
        by_key = {}
        for tok, (c, kind_, lift) in cands.items():
            k = fa_key(tok)
            if k and (k not in by_key or by_key[k][1] < c):
                by_key[k] = (tok, c, kind_, lift)
        cand_list = sorted(by_key.values(), key=lambda x: -x[1])[:10]
        pairs_flag = []
        for i1 in range(len(cand_list)):
            for i2 in range(i1 + 1, len(cand_list)):
                t1, c1, k1, _l1 = cand_list[i1]
                t2, c2, k2, _l2 = cand_list[i2]
                key1, key2 = fa_key(t1), fa_key(t2)
                if key1 in key2 or key2 in key1:
                    continue                      # components of one phrase
                if k1 == "w" and k2 == "w":
                    both = sum(1 for i in M if t1 in out_wset[i] and t2 in out_wset[i])
                elif k1 == "b" and k2 == "b":
                    both = sum(1 for i in M if t1 in out_bset[i] and t2 in out_bset[i])
                else:
                    wt, bt = (t1, t2) if k1 == "w" else (t2, t1)
                    both = sum(1 for i in M
                               if wt in out_wset[i] and bt in out_bset[i])
                obs, exp = both / m, (c1 / m) * (c2 / m)
                if obs < 0.5 * exp:
                    pairs_flag.append((t1, c1, t2, c2, obs, exp))
        if pairs_flag:
            pairs_flag.sort(key=lambda x: -min(x[1], x[3]))
            b_flagged.append((term, m, cand_list, pairs_flag[0]))
    b_flagged.sort(key=lambda x: x[1])          # smallest matched sets first
    for term, m, cand_list, (t1, c1, t2, c2, obs, exp) in b_flagged:
        shown = ", ".join(f"«{t}»×{c}" for t, c, _k, _l in cand_list[:5])
        lines.append(
            f"| `{md_escape(term)}` | {m} | {shown} | "
            f"{obs:.3f}/{exp:.3f} | inconsistent ✗ |")
    if not b_flagged:
        lines.append("| — | — | — | — | no Method-B inconsistency found |")

    if b_flagged:
        lines += ["", "Worked examples (real source → current output):", ""]
        for term, m, _cands, (t1, c1, t2, c2, _o, _e) in b_flagged[:3]:
            ex1 = ex2 = None
            for src, out in pairs:
                if not src_has(src, term):
                    continue
                if ex1 is None and t1 in out:
                    ex1 = (src, out)
                if ex2 is None and t2 in out:
                    ex2 = (src, out)
                if ex1 and ex2:
                    break
            lines.append(f"- **`{term}`** — «{t1}»×{c1} vs «{t2}»×{c2}:")
            if ex1:
                lines.append(f"  - `{md_escape(trunc(ex1[0], 70))}` → "
                             f"`{md_escape(trunc(ex1[1], 80))}`")
            if ex2 and ex2 != ex1:
                lines.append(f"  - `{md_escape(trunc(ex2[0], 70))}` → "
                             f"`{md_escape(trunc(ex2[1], 80))}`")
    lines.append("")
    return "\n".join(lines)


def sec_format(rows) -> str:
    """Character / punctuation / digit problems in published outputs."""
    outs = []
    for title, title_fa, summary, summary_fa in rows:
        if title_fa:
            outs.append((title, title_fa, "title"))
        if summary_fa:
            outs.append((summary, summary_fa, "summary"))

    miss_mey = (r"(?:^|[\s(\[«\"'\u201c])\u0645\u06cc [\u0600-\u06ff]|"
                r"(?:^|[\s(\[«\"'\u201c])\u0646\u0645\u06cc [\u0600-\u06ff]")
    plural = r"[\u0600-\u06ff] ها(?:ی)? "
    compar = r"[\u0600-\u06ff]{2,} تر(?:ین)? "
    space_before = r" [\u060c\u061b\u061f]"
    quote_sp = r"«\s|\s»"

    checks = [
        ("Arabic yeh/kaf (ي ك) instead of Persian ی ک",
         lambda s: re.search(r"[\u064a\u0643]", s) is not None,
         lambda s: next((m.group(0) for m in re.finditer(r"[\u064a\u0643]+", s)), "")),
        ("tatweel ـ",
         lambda s: "\u0640" in s, lambda s: "ـ"),
        ("missing ZWNJ after می/نمی («می رود»)",
         lambda s: re.search(miss_mey, s) is not None,
         lambda s: next((m.group(0).strip() for m in re.finditer(miss_mey, s)), "")),
        ("missing ZWNJ in plural ها/های («سقوط ها»)",
         lambda s: re.search(plural, s) is not None,
         lambda s: next((m.group(0) for m in re.finditer(plural, s)), "")),
        ("missing ZWNJ in comparative تر/ترین («بزرگ تر»)",
         lambda s: re.search(compar, s) is not None,
         lambda s: next((m.group(0) for m in re.finditer(compar, s)), "")),
        ("space before ، ؛ ؟ («متن ،»)",
         lambda s: re.search(space_before, s) is not None,
         lambda s: next((m.group(0) for m in re.finditer(space_before, s)), "")),
        ("« » broken spacing («« متن» or «متن »»)",
         lambda s: re.search(quote_sp, s) is not None,
         lambda s: next((m.group(0) for m in re.finditer(quote_sp, s)), "")),
        ("double space",
         lambda s: "  " in s, lambda s: "  "),
        ("mixed digit styles (ASCII + Persian digits in one output)",
         lambda s: bool(ASCII_DIGITS_RE.search(s)) and bool(FA_DIGITS_RE.search(s)),
         lambda s: "123+۱۲۳"),
        ("Persian digits inside URLs (fa_digits corrupted the link)",
         lambda s: re.search(r"https?://\S*[\u06F0-\u06F9]", s) is not None,
         lambda s: next((m.group(0) for m in
                         re.finditer(r"https?://\S*[\u06F0-\u06F9]\S*", s)), "")),
    ]

    lines = [
        "### 8. Character / punctuation / digit problems in published outputs",
        "",
        f"Measured over **{len(outs)}** published outputs "
        "(title_fa + summary_fa). Counts are outputs affected; each suspect "
        "pattern is a candidate defect, judged by its regex.",
        "",
        "| problem | outputs affected | share | example fragment |",
        "|---------|-----------------:|------:|-----------------|",
    ]
    for label, test, extract in checks:
        hits = [(src, out) for src, out, _k in outs if test(out)]
        ex = md_escape(trunc(extract(hits[0][1]), 50)) if hits else ""
        lines.append(f"| {label} | {len(hits)} | {pct(len(hits), len(outs))} | "
                     f"`{ex}` |")
    lines.append("")
    return "\n".join(lines)


def sec_worst(rows) -> str:
    """30 worst published outputs (source + output)."""
    items = []
    for title, title_fa, summary, summary_fa in rows:
        if title_fa and not is_persian(title_fa):
            items.append((persian_share(title_fa), longest_latin_run(title_fa),
                          "title", title, title_fa))
        if summary_fa and not is_persian(summary_fa):
            items.append((persian_share(summary_fa), longest_latin_run(summary_fa),
                          "summary", summary[:1000], summary_fa))
    items.sort(key=lambda x: (x[0], -x[1], x[3]))
    lines = [
        "### 9. 30 worst examples (source → current output)",
        "",
        "Sorted by lowest Persian letter share, then longest Latin run.",
        "",
        "| # | kind | share | run | source | output |",
        "|---|------|------:|----:|--------|--------|",
    ]
    for i, (share, run, kind_, src, out) in enumerate(items[:30], 1):
        lines.append(f"| {i} | {kind_} | {share:.2f} | {run} | "
                     f"{md_escape(trunc(src, 60))} | {md_escape(trunc(out, 80))} |")
    lines.append("")
    return "\n".join(lines)


def sec_probe_placeholder() -> str:
    return """\
### 10. Live endpoint probe (network; `tools/fa_build/probe_endpoint.py`)

Run 2026-10-12 10:52 local, ~15 GETs, 1 req/s, raw endpoint requests (no cache
writes, no translate.translate_many):

- **(a) Re-asking echoed headlines:** both fixed English headlines (cache value
  byte-identical to the source) were asked again through a fresh request —
  **still verbatim echoes** (Persian share 0.00, pass=0). A second ask does not
  fix an echo; a third-party retry would just re-cache the same text.
- **(b) Sentence-by-sentence:** a 374-char half-translated summary (4 sentences):
  whole ask → share 0.42, Latin run 27, fail; per-sentence asks → only 1/4
  sentences passes `is_persian`; joined result still fails (0.42/27).
  Sentence splitting alone does not rescue texts with embedded
  non-translatable content — the D.2 retry must accept-and-join-or-«""».
- **(c) Query length:** URL length 4,078 → 200; 8,081 → 200; 12,084 → 200;
  **20,090 → HTTP 400**. The cliff sits between ≈12 KB and ≈20 KB of URL; the
  conservative Phase-3b batch budget is **≈8.4 KB (70% × 12,084, the largest
  confirmed-OK URL)**.
- **(d) Batch of 16 alignment:** complete batch → 16/16 aligned. With slot 8
  replaced by an **empty string** the endpoint still returned 16 items with the
  empty kept in place → 15/16 markers at their expected positions, **no mid-drop
  shift**; a very short member ("ok") → 16/16 aligned. The end-padding
  misalignment (A3) did not reproduce for empty/short members in this probe.
"""


def sec_method() -> str:
    return f"""\
### 11. Method & caveats

- DB read with `file:.mohmd_news.db?mode=ro`; cache read from a temp copy;
  `translate.translate_many` / `save_cache` never called — this audit performs
  **zero writes and zero network requests**.
- Gate semantics are `translate.py`'s own (`is_persian`, `persian_share`,
  `longest_latin_run`, `_looks_persian`) — measured, not re-implemented.
- N-grams: `title` sources, lowercased, tokens `[a-z0-9'&.%/-]*`, pure-digit
  tokens dropped, orders 1–4.
- Term inconsistency is a *screen*, not ground truth: Method A is exact for
  vendor-known renderings; Method B is a lift + co-occurrence heuristic and
  may miss alternates that share words (or flag rare combinations) — every
  flagged item above ships with real source/output examples for manual review.
- `summary_fa` is stored from `summary[:1000]` (app.py
  `_translate_articles_inplace`), so long summaries are only audited on their
  first 1000 chars.
- Generated by `tools/fa_build/audit.py` on {date.today().isoformat()}.
"""


def main():
    cache, rows = load_data()
    pairs = build_pairs(rows)
    src_idx = build_source_index(rows)

    parts = [
        "# FA translation audit — Phase 0",
        "",
        f"Measured on {date.today().isoformat()} against `.mohmd_news.db` "
        f"({len(rows)} articles) and a read-only copy of `.translate_cache.json` "
        f"({len(cache)} entries).",
        "",
        sec_facts(),
        sec_publish(rows),
        sec_cache(cache, src_idx),
        sec_identity(rows),
        sec_latin_tokens(rows, pairs),
        sec_ngrams(rows),
        sec_term_inconsistency(pairs),
        sec_format(rows),
        sec_worst(rows),
        sec_probe_placeholder(),
        sec_method(),
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    print(f"wrote {OUT_MD} ({OUT_MD.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
