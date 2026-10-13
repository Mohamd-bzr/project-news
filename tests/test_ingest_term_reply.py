#!/usr/bin/env python3
"""
tests/test_ingest_term_reply.py
===============================
Tests for core term reply parsing and ingestion into data/fa/core_terms.tsv.
"""
import csv
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.fa_build.ingest_term_reply import (
    parse_line,
    parse_replies,
    apply_term_replies,
)

def test_parse_line_forms():
    # 1. Custom Persian override
    assert parse_line("1: بازده") == (1, "custom", "بازده")
    assert parse_line("2 - افزایش نرخ") == (2, "custom", "افزایش نرخ")
    assert parse_line("4: خدمات نگهداری") == (4, "custom", "خدمات نگهداری")

    # 2. Skip form
    assert parse_line("5 skip") == (5, "skip", "")
    assert parse_line("5: SKIP") == (5, "skip", "")
    assert parse_line("6 - skip") == (6, "skip", "")

    # 3. Default / OK form
    assert parse_line("7 ok") == (7, "default", "")
    assert parse_line("8: OK") == (8, "default", "")
    assert parse_line("9: default") == (9, "default", "")

    # 4. Comments and malformed lines
    assert parse_line("# this is a comment") is None
    assert parse_line("just text without id") is None
    assert parse_line("") is None

def test_parse_replies_multiline(capsys):
    input_text = """
    # Feedback on candidate terms
    1: بازده
    bad line without number
    4: نگهداری دارایی
    5 skip
    7 ok
    10: اختلاف قیمت
    another bad line
    """
    replies = parse_replies(input_text)
    captured = capsys.readouterr()

    assert len(replies) == 5
    assert replies[1] == ("custom", "بازده")
    assert replies[4] == ("custom", "نگهداری دارایی")
    assert replies[5] == ("skip", "")
    assert replies[7] == ("default", "")
    assert replies[10] == ("custom", "اختلاف قیمت")

    assert "bad line without number" in captured.err
    assert "another bad line" in captured.err

def test_apply_term_replies_roundtrip(tmp_path):
    dummy_candidates = [
        {
            "id": 1,
            "en": "yields",
            "domain": "macro",
            "recommended": "بازدهی",
            "variants": [{"term": "بازدهی"}, {"term": "بازده"}],
            "context_rule": "بازده اوراق",
        },
        {
            "id": 2,
            "en": "rate hike",
            "domain": "macro",
            "recommended": "افزایش نرخ بهره",
            "variants": [{"term": "افزایش نرخ بهره"}, {"term": "افزایش نرخ"}],
            "context_rule": "سیاست پولی",
        },
        {
            "id": 3,
            "en": "custody",
            "domain": "crypto",
            "recommended": "حضانت",
            "variants": [{"term": "نگهداری"}, {"term": "حضانت"}],
            "context_rule": "امانتداری",
        },
        {
            "id": 4,
            "en": "spread",
            "domain": "forex",
            "recommended": "اسپرد",
            "variants": [{"term": "اسپرد"}, {"term": "گسترش"}],
            "context_rule": "اختلاف قیمت",
        },
    ]

    cand_file = tmp_path / "candidates.json"
    cand_file.write_text(json.dumps(dummy_candidates, ensure_ascii=False), encoding="utf-8")

    tsv_file = tmp_path / "core_terms.tsv"

    # User input:
    # 1: override with بازده
    # 2: ok (default approved)
    # 3: skip
    # 4: not mentioned (default approved)
    replies = {
        1: ("custom", "بازده"),
        2: ("default", ""),
        3: ("skip", ""),
    }

    count = apply_term_replies(replies, candidates_path=cand_file, output_tsv_path=tsv_file)
    assert count == 4

    # Verify TSV
    rows = []
    with open(tsv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for r in reader:
            rows.append(r)

    assert len(rows) == 4

    # Check row 1 (override)
    assert rows[0]["en"] == "yields"
    assert rows[0]["fa_preferred"] == "بازده"
    assert rows[0]["status"] == "user_override"
    assert rows[0]["bad_variants"] == "بازدهی"

    # Check row 2 (ok)
    assert rows[1]["en"] == "rate hike"
    assert rows[1]["fa_preferred"] == "افزایش نرخ بهره"
    assert rows[1]["status"] == "approved"
    assert rows[1]["bad_variants"] == "افزایش نرخ"

    # Check row 3 (skip)
    assert rows[2]["en"] == "custody"
    assert rows[2]["fa_preferred"] == ""
    assert rows[2]["status"] == "skipped"

    # Check row 4 (unmentioned -> pending, not enforced)
    assert rows[3]["en"] == "spread"
    assert rows[3]["fa_preferred"] == ""
    assert rows[3]["status"] == "pending"
    assert rows[3]["bad_variants"] == ""
