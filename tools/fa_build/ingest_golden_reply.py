#!/usr/bin/env python3
"""
ingest_golden_reply.py — ingest reviewer corrections into golden_template.tsv.
=============================================================================
Parses reviewer reply lines like:
  12: متن اصلاح شده
  25: ترجمه بهتر

Matches the review pack index (1..40) to the corresponding row in
data/fa/golden_template.tsv (or data/fa/review_pack_40.json) and fills
the fixed_fa column.

Preserves UTF-8 with BOM, CRLF, and all existing columns.
"""
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TSV_PATH = REPO / "data" / "fa" / "golden_template.tsv"
PACK_PATH = REPO / "data" / "fa" / "review_pack_40.json"


def load_review_pack():
    if PACK_PATH.exists():
        with open(PACK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback to computing the 40 rows deterministically
    sys.path.insert(0, str(REPO))
    from tools.fa_eval import is_english_source

    lines = TSV_PATH.read_text(encoding="utf-8-sig").splitlines()
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


def parse_replies(text):
    """Parses text containing lines like '12: <Persian>' into {12: '<Persian>'}."""
    results = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)\s*[:：\-]\s*(.*)$", line)
        if m:
            num = int(m.group(1))
            val = m.group(2).strip()
            if val:
                results[num] = val
    return results


def apply_corrections(corrections):
    pack = load_review_pack()
    pack_map = {idx + 1: item for idx, item in enumerate(pack)}

    # Map target article id -> corrected text
    id_to_fixed = {}
    for num, fixed_text in corrections.items():
        if num in pack_map:
            art_id = pack_map[num]["id"]
            id_to_fixed[art_id] = fixed_text
        else:
            print(f"[WARN] Item #{num} out of range (expected 1..{len(pack)})")

    lines = TSV_PATH.read_text(encoding="utf-8-sig").splitlines()
    out_lines = []
    header = lines[0]
    out_lines.append(header)

    updated_count = 0
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        while len(parts) < 5:
            parts.append("")
        art_id = parts[0]
        if art_id in id_to_fixed:
            parts[4] = id_to_fixed[art_id]
            updated_count += 1
        out_lines.append("\t".join(parts))

    with open(TSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        for l in out_lines:
            f.write(l + "\r\n")

    print(f"Applied {updated_count} corrections to {TSV_PATH}")
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
        print("No corrections found in input (expected format: '12: <Persian>').")
        sys.exit(1)

    print(f"Parsed {len(corrections)} corrections: {sorted(corrections.keys())}")
    apply_corrections(corrections)


if __name__ == "__main__":
    main()
