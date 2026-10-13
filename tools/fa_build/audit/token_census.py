#!/usr/bin/env python3
"""
tools/fa_build/audit/token_census.py
====================================
Census of token-level changes (before -> after) produced by fa_postedit.post_edit
over all English-source articles with engine outputs in .mohmd_news.db.
"""
import difflib
import json
import random
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from fa_postedit import post_edit, lexicon, ZWNJ
from tools.fa_eval import is_english_source

DIGIT_TRANS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def classify_change(b, a, lex):
    """
    Returns (rule_name, is_approved_category, note)
    Approved categories:
      (a) U+200C or space insertion/removal around documented prefixes/suffixes
      (b) Arabic->Persian letters
      (c) digits
      (d) exact entity replacement
    """
    # (c) Digits
    if b.translate(DIGIT_TRANS) == a:
        return "digits", True, "(c) digits"

    # (b) Arabic -> Persian
    norm_ar = b.replace("\u064a", "\u06cc").replace("\u0649", "\u06cc").replace("\u0643", "\u06a9").replace("\u0640", "")
    if norm_ar == a:
        return "arabic_letters", True, "(b) Arabic->Persian letters"

    # (d) Exact entity replacement
    low_b = b.lower().strip()
    if lex.latin_fa_for(low_b) == a or lex.latin_fa_for(low_b.rstrip("'s")) == a:
        return "entity_replacement", True, "(d) exact entity replacement"

    # Punctuation-stripped entity / digit check
    b_core_punct = re.sub(r"^[^\w]+|[^\w]+$", "", b)
    a_core_punct = re.sub(r"^[^\w]+|[^\w]+$", "", a)
    if b_core_punct and a_core_punct:
        low_core = b_core_punct.lower()
        if lex.latin_fa_for(low_core) == a_core_punct or lex.latin_fa_for(low_core.rstrip("'s")) == a_core_punct:
            return "entity_replacement", True, "(d) exact entity replacement"
        if b_core_punct.translate(DIGIT_TRANS) == a_core_punct:
            return "digits", True, "(c) digits"

    # (a) ZWNJ / space around prefixes/suffixes
    b_core = b.replace(ZWNJ, "").replace(" ", "")
    a_core = a.replace(ZWNJ, "").replace(" ", "")
    if b_core == a_core:
        if b.startswith("می ") or b.startswith("نمی ") or " می " in b or " نمی " in b:
            return "zwnj_mi", True, "(a) prefix mi/nemi ZWNJ"
        if any(b.rstrip(".").endswith(" " + s) for s in ["ها", "های", "هایی", "هایمان", "هایشان", "هایش"]):
            return "zwnj_ha", True, "(a) suffix ha/hay ZWNJ"
        if any(b.rstrip(".").endswith(" " + s) for s in ["تر", "ترین"]):
            return "zwnj_tar", True, "(a) suffix tar/tarin ZWNJ"
        if b in ("بیش تر", "کم تر", "به تر", "به ترین"):
            return "zwnj_tar", True, "(a) lexicalized tar/tarin"
        return "zwnj_spacing", True, "(a) ZWNJ/spacing"

    # (a)/(b)/(c) combined orthography
    norm_combo = norm_ar.translate(DIGIT_TRANS).replace(ZWNJ, "").replace(" ", "")
    if norm_combo == a_core:
        return "arabic_plus_zwnj_or_digit", True, "(a)/(b)/(c) combined orthography"

    # (a) Spelling canonicalization from lexicon
    if lex.fa_windows and a in [v[0] for v in lex.fa_windows.values()]:
        return "fa_canon", True, "(a) spelling canonicalization"

    return "other", False, "[!UNAPPROVED / OUTSIDE RULES]"


def run_census():
    db_path = Path("E:/freebuff/.mohmd_news.db")
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    c = conn.cursor()

    rows = c.execute("SELECT id, title, title_fa, summary, summary_fa FROM articles WHERE title IS NOT NULL").fetchall()
    print(f"Total DB rows: {len(rows)}")

    lex = lexicon()
    pair_counts = Counter()
    pair_meta = {}

    for row_id, en_title, fa_title, en_summ, fa_summ in rows:
        targets = []
        if fa_title and is_english_source(en_title):
            targets.append(fa_title)
        if fa_summ and en_summ and is_english_source(en_summ):
            targets.append(fa_summ)

        for text in targets:
            pe = post_edit(text, lex)
            if pe == text:
                continue

            # Split by clauses/sentences for rock-solid local alignment
            # keeps sentence terminators attached to sentences
            sub_raws = re.split(r"(?<=[.!؟?\n])\s+", text)
            sub_posts = re.split(r"(?<=[.!؟?\n])\s+", pe)
            if len(sub_raws) == len(sub_posts):
                pairs = zip(sub_raws, sub_posts)
            else:
                pairs = [(text, pe)]

            for s_raw, s_post in pairs:
                if s_raw == s_post:
                    continue
                r_toks = re.findall(r"\S+|\s+", s_raw)
                p_toks = re.findall(r"\S+|\s+", s_post)
                matcher = difflib.SequenceMatcher(None, r_toks, p_toks)

                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag != "equal":
                        b_chunk = "".join(r_toks[i1:i2]).strip()
                        a_chunk = "".join(p_toks[j1:j2]).strip()
                        if b_chunk and a_chunk and b_chunk != a_chunk:
                            key = (b_chunk, a_chunk)
                            pair_counts[key] += 1
                            if key not in pair_meta:
                                rule, ok, note = classify_change(b_chunk, a_chunk, lex)
                                pair_meta[key] = (rule, ok, note)

    print(f"Total distinct token changes: {len(pair_counts)}")
    print(f"Total transformation instances: {sum(pair_counts.values())}")

    # Top 60 by frequency
    most_common_60 = pair_counts.most_common(60)

    # Tail selection: from ranks > 60
    tail_candidates = [item for item in pair_counts.most_common()[60:] if item[1] >= 1]
    random.seed(42)
    tail_20 = random.sample(tail_candidates, min(20, len(tail_candidates)))

    results = {
        "total_instances": sum(pair_counts.values()),
        "distinct_pairs": len(pair_counts),
        "top_60": [(k[0], k[1], cnt, pair_meta[k][0], pair_meta[k][1], pair_meta[k][2]) for k, cnt in most_common_60],
        "tail_20": [(k[0], k[1], cnt, pair_meta[k][0], pair_meta[k][1], pair_meta[k][2]) for k, cnt in tail_20],
    }

    out_json = REPO / "tools" / "fa_build" / "audit" / "token_census_results.json"
    out_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved results to {out_json}")

    return results


if __name__ == "__main__":
    run_census()
