#!/usr/bin/env python3
"""
golden_template.py — build data/fa/golden_template.tsv (Phase-3 evaluation set)
================================================================================
300 real headlines from .mohmd_news.db (opened READ-ONLY), fixed seed,
stratified so the review set covers the failure modes that matter:

  A. 100 where translate.is_persian FAILS on the raw engine output — the
     publish-gate rejects / repairs these today
  B. 100 whose EN title contains a terms.tsv / entities.tsv key — measures
     lexicon coverage on real text
  C. 100 random from the remainder

Columns: id, english, engine_output, post_edit_output, fixed_fa (blank).
  engine_output   = stored title_fa (the translate pipeline's output)
  post_edit_output= post_edit(engine_output) — what the Phase-3 hook emits
  fixed_fa        = YOU fill it only where the output is wrong/awkward;
                    blank means "acceptable as-is".

Excel-safe: UTF-8 with BOM, CRLF rows, one line per row, tabs/newlines/
bidi-control marks stripped from every field. Offline, stdlib only,
never writes the database.
"""
import csv
import random
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from translate import is_persian       # noqa: E402 (path bootstrap)
from fa_postedit import post_edit      # noqa: E402

SEED = 20261012
PER_STRATUM = 100
OUT = REPO / "data" / "fa" / "golden_template.tsv"
_BIDI = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def _clean(s):
    """One line, no tabs, no bidi marks — safe for a TSV cell."""
    return " ".join(_BIDI.sub("", s or "").replace("\t", " ").split())


def load_term_keys():
    """EN keys (len>=4) from terms.tsv + entities.tsv."""
    keys = set()
    for name in ("terms.tsv", "entities.tsv"):
        with open(REPO / "data" / "fa" / name, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                k = (row.get("en") or "").strip().lower()
                if len(k) >= 4:
                    keys.add(k)
    return keys


def has_term(title, single, multi):
    """True when a token matches a single-word key or opens a multi-word key."""
    tl = re.sub(r"[^a-z0-9]+", " ", (title or "").lower())
    for tok in tl.split():
        if tok in single:
            return True
        for mk in multi.get(tok, ()):
            if mk in tl:
                return True
    return False


def main():
    keys = load_term_keys()
    single = {k for k in keys if " " not in k}
    multi = {}
    for k in keys:
        if " " in k:
            multi.setdefault(k.split(" ")[0], []).append(k)

    con = sqlite3.connect(f"file:{REPO / '.mohmd_news.db'}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT id, title, title_fa FROM articles"
        " WHERE title_fa IS NOT NULL AND title_fa <> ''"
        "   AND title IS NOT NULL AND title <> ''").fetchall()
    con.close()

    pool_a = [r for r in rows if not is_persian(r[2])]
    pool_b = [r for r in rows if has_term(r[1], single, multi)]

    rng = random.Random(SEED)
    taken = set()

    def take(pool):
        avail = [r for r in pool if r[0] not in taken]
        rng.shuffle(avail)
        picked = avail[:PER_STRATUM]
        taken.update(r[0] for r in picked)
        return picked

    picked = [("A:is_persian-fails", r) for r in take(pool_a)] \
        + [("B:has-term-key", r) for r in take(pool_b)] \
        + [("C:random", r) for r in take(rows)]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        f.write("id\tenglish\tengine_output\tpost_edit_output\tfixed_fa\r\n")
        for _stratum, (_id, en, eng) in picked:
            pe = post_edit(eng)
            f.write("\t".join((_clean(str(_id)), _clean(en),
                               _clean(eng), _clean(pe), "")) + "\r\n")

    n_changed = sum(1 for _s, (_i, _e, g) in picked if post_edit(g) != g)
    print(f"pool: total={len(rows)} A(is_persian fails)={len(pool_a)} "
          f"B(has term)={len(pool_b)}")
    print(f"wrote {len(picked)} rows -> {OUT} "
          f"({OUT.stat().st_size / 1024:.0f} KB, BOM+CRLF)")
    print(f"post_edit changes {n_changed}/{len(picked)} engine outputs")


if __name__ == "__main__":
    main()
