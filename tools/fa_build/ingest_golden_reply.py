#!/usr/bin/env python3
"""
ingest_golden_reply.py — ingest reviewer corrections into golden_template.tsv.
=============================================================================
Accepts three line forms in reviewer reply:
  "<n>: <Persian text>"  -> fixed_fa = that text, pref = "fixed"
  "<n> ok"               -> post_edit output acceptable -> fixed_fa = post_edit_output, pref = "post_ok"
  "<n> raw"              -> raw engine output was better -> fixed_fa = engine_output, pref = "raw_better"

Rows not mentioned stay blank (= no opinion, excluded from tallies).
Maintains a 6-column header: id, english, engine_output, post_edit_output, fixed_fa, pref.
Preserves UTF-8 BOM, CRLF line endings, and existing data.
Malformed lines are ignored with a warning.
"""
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TSV_PATH = REPO / "data" / "fa" / "golden_template.tsv"
PACK_PATH = REPO / "data" / "fa" / "review_pack_40.json"


def load_review_pack(repo_path=None):
    pack_file = (repo_path / "data" / "fa" / "review_pack_40.json") if repo_path else PACK_PATH
    if pack_file.exists():
        with open(pack_file, "r", encoding="utf-8") as f:
            return json.load(f)

    tsv_file = (repo_path / "data" / "fa" / "golden_template.tsv") if repo_path else TSV_PATH
    sys.path.insert(0, str(repo_path or REPO))
    from tools.fa_eval import is_english_source

    lines = tsv_file.read_text(encoding="utf-8-sig").splitlines()
    reader = csv.reader(lines, delimiter="\t")
    next(reader, None)

    rows_a, rows_b, rows_c = [], [], []
    for i, r in enumerate(reader):
        if len(r) < 4:
            continue
        row_data = {"template_line": i + 2, "idx": i, "id": r[0], "en": r[1], "raw": r[2], "post": r[3]}
        if not is_english_source(r[1]):
            continue
        if i < 100:
            rows_a.append(row_data)
        elif i < 200:
            rows_b.append(row_data)
        else:
            rows_c.append(row_data)

    return rows_a[:10] + rows_b[:20] + rows_c[:10]


def parse_line(line):
    """
    Parses a single line into (idx, pref, fixed_text) or None if empty,
    or ('bad', line) if malformed.
    """
    s = line.strip()
    if not s:
        return None

    # Form 1: "<n> ok" or "<n> raw" (with optional :, -, or whitespace)
    m_kw = re.match(r"^(\d+)\s*(?:[:：\-]\s*)?(ok|raw)\s*$", s, re.IGNORECASE)
    if m_kw:
        idx = int(m_kw.group(1))
        kw = m_kw.group(2).lower()
        pref = "post_ok" if kw == "ok" else "raw_better"
        return (idx, pref, "")

    # Form 2: "<n>: <Persian text>"
    m_fixed = re.match(r"^(\d+)\s*[:：\-]\s*(.+)$", s)
    if m_fixed:
        idx = int(m_fixed.group(1))
        text = m_fixed.group(2).strip()
        if text.lower() == "ok":
            return (idx, "post_ok", "")
        if text.lower() == "raw":
            return (idx, "raw_better", "")
        if text:
            return (idx, "fixed", text)

    return ("bad", s)


def parse_replies(text):
    """
    Parses full reply text.
    Returns dict: {item_idx: (pref, fixed_text)}
    Warns on malformed lines.
    """
    results = {}
    for line in text.splitlines():
        parsed = parse_line(line)
        if parsed is None:
            continue
        if parsed[0] == "bad":
            print(f"[WARN] Ignored bad line: {parsed[1]!r}", file=sys.stderr)
            continue
        idx, pref, val = parsed
        results[idx] = (pref, val)
    return results


def apply_corrections(corrections, tsv_path=None, pack_path=None):
    """
    Applies parsed corrections {num: (pref, val)} to golden_template.tsv.
    Maintains 6 columns: id, english, engine_output, post_edit_output, fixed_fa, pref.
    Preserves UTF-8 BOM and CRLF.
    """
    tsv_file = Path(tsv_path) if tsv_path else TSV_PATH
    pack = load_review_pack(tsv_file.parents[2]) if tsv_path else load_review_pack()
    pack_map = {idx + 1: item for idx, item in enumerate(pack)}

    # Map article id -> (fixed_fa, pref)
    id_to_data = {}
    for num, (pref, custom_text) in corrections.items():
        if num in pack_map:
            item = pack_map[num]
            art_id = item["id"]
            if pref == "fixed":
                id_to_data[art_id] = (custom_text, "fixed")
            elif pref == "post_ok":
                id_to_data[art_id] = (item["post"], "post_ok")
            elif pref == "raw_better":
                id_to_data[art_id] = (item["raw"], "raw_better")
        else:
            print(f"[WARN] Item #{num} out of range (expected 1..{len(pack)})", file=sys.stderr)

    lines = tsv_file.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        return 0

    header_cols = lines[0].split("\t")
    if len(header_cols) < 6:
        header_cols = ["id", "english", "engine_output", "post_edit_output", "fixed_fa", "pref"]
    out_lines = ["\t".join(header_cols)]

    updated_count = 0
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        while len(parts) < 6:
            parts.append("")
        art_id = parts[0]
        if art_id in id_to_data:
            fixed_val, pref_val = id_to_data[art_id]
            parts[4] = fixed_val
            parts[5] = pref_val
            updated_count += 1
        out_lines.append("\t".join(parts))

    with open(tsv_file, "w", encoding="utf-8-sig", newline="") as f:
        for l in out_lines:
            f.write(l + "\r\n")

    print(f"Applied {updated_count} opinion(s) to {tsv_file}")
    return updated_count


def main():
    if len(sys.argv) > 1:
        arg_path = Path(sys.argv[1])
        if arg_path.exists():
            text = arg_path.read_text(encoding="utf-8")
        else:
            text = sys.argv[1]
    else:
        text = sys.stdin.read()

    corrections = parse_replies(text)
    if not corrections:
        print("No valid corrections found in input.", file=sys.stderr)
        sys.exit(1)

    print(f"Parsed {len(corrections)} items: {sorted(corrections.keys())}")
    apply_corrections(corrections)


if __name__ == "__main__":
    main()
