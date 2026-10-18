#!/usr/bin/env python3
"""
tests/test_ingest_golden_reply.py — tests for golden reply parser and ingest.
=============================================================================
Tests:
  1. All three line forms:
     - "<n>: <Persian text>" -> fixed_fa = text, pref = "fixed"
     - "<n> ok" / "<n>: ok"  -> fixed_fa = post_edit, pref = "post_ok"
     - "<n> raw" / "<n>: raw"-> fixed_fa = engine, pref = "raw_better"
  2. Malformed lines ignored with warnings.
  3. UTF-8 BOM + CRLF round trip and 6-column structure.
"""
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools.fa_build.ingest_golden_reply import parse_line, parse_replies, apply_corrections


def test_parse_three_line_forms():
    # 1. Custom text
    p1 = parse_line("12: متن اصلاح‌شده توسط کاربر")
    assert p1 == (12, "fixed", "متن اصلاح‌شده توسط کاربر")

    p1_dash = parse_line("15 - ترجمه بهتر")
    assert p1_dash == (15, "fixed", "ترجمه بهتر")

    # 2. ok form (case-insensitive, with/without colon)
    assert parse_line("5 ok") == (5, "post_ok", "")
    assert parse_line("6 OK") == (6, "post_ok", "")
    assert parse_line("7: ok") == (7, "post_ok", "")
    assert parse_line("8 - Ok") == (8, "post_ok", "")

    # 3. raw form (case-insensitive, with/without colon)
    assert parse_line("10 raw") == (10, "raw_better", "")
    assert parse_line("11 RAW") == (11, "raw_better", "")
    assert parse_line("13: raw") == (13, "raw_better", "")
    assert parse_line("14 - Raw") == (14, "raw_better", "")


def test_parse_malformed_lines(capsys):
    input_text = """
    12: متن فارسی
    bad line without number
    5 ok
    999 random string
    10 raw
    just some text
    """
    res = parse_replies(input_text)
    captured = capsys.readouterr()

    # Valid parsed
    assert 12 in res and res[12] == ("fixed", "متن فارسی")
    assert 5 in res and res[5] == ("post_ok", "")
    assert 10 in res and res[10] == ("raw_better", "")

    # Malformed ignored
    assert "bad line without number" in captured.err
    assert "999 random string" in captured.err
    assert "just some text" in captured.err
    assert len(res) == 3


def test_bom_crlf_round_trip(tmp_path):
    # Dummy review pack
    dummy_pack = [
        {"id": "art-01", "en": "Title One", "raw": "خام یک", "post": "پس‌پردازش یک"},
        {"id": "art-02", "en": "Title Two", "raw": "خام دو", "post": "پس‌پردازش دو"},
        {"id": "art-03", "en": "Title Three", "raw": "خام سه", "post": "پس‌پردازش سه"},
    ]
    pack_file = tmp_path / "review_pack_40.json"
    import json
    pack_file.write_text(json.dumps(dummy_pack, ensure_ascii=False), encoding="utf-8")

    # Dummy initial golden template with 5 columns, BOM + CRLF
    tsv_file = tmp_path / "golden_template.tsv"
    init_content = "\ufeffid\tenglish\tengine_output\tpost_edit_output\tfixed_fa\r\n" \
                   "art-01\tTitle One\tخام یک\tپس‌پردازش یک\t\r\n" \
                   "art-02\tTitle Two\tخام دو\tپس‌پردازش دو\t\r\n" \
                   "art-03\tTitle Three\tخام سه\tپس‌پردازش سه\t\r\n"
    tsv_file.write_bytes(init_content.encode("utf-8"))

    # Apply all three forms: 1=fixed, 2=post_ok, 3=raw_better
    replies = {
        1: ("fixed", "اصلاح سفارشی یک"),
        2: ("post_ok", ""),
        3: ("raw_better", ""),
    }

    # Monkeypatch load_review_pack
    import tools.fa_build.ingest_golden_reply as mod
    orig_load = mod.load_review_pack
    mod.load_review_pack = lambda *args: dummy_pack
    try:
        updated = apply_corrections(replies, tsv_path=tsv_file)
        assert updated == 3

        raw_bytes = tsv_file.read_bytes()
        # 1. Assert UTF-8 BOM
        assert raw_bytes.startswith(b"\xef\xbb\xbf"), "Must start with UTF-8 BOM"

        # 2. Assert CRLF
        text = raw_bytes.decode("utf-8-sig")
        for line in text.splitlines(keepends=True):
            assert line.endswith("\r\n"), f"Line missing CRLF: {line!r}"

        # 3. Assert 6 columns
        rows = [l.split("\t") for l in text.splitlines()]
        assert rows[0] == ["id", "english", "engine_output", "post_edit_output", "fixed_fa", "pref"]
        assert rows[1] == ["art-01", "Title One", "خام یک", "پس‌پردازش یک", "اصلاح سفارشی یک", "fixed"]
        assert rows[2] == ["art-02", "Title Two", "خام دو", "پس‌پردازش دو", "پس‌پردازش دو", "post_ok"]
        assert rows[3] == ["art-03", "Title Three", "خام سه", "پس‌پردازش سه", "خام سه", "raw_better"]
    finally:
        mod.load_review_pack = orig_load
