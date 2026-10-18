#!/usr/bin/env python3
"""
tools/fa_build/audit/rebuild_review_pack.py
===========================================
Rebuilds data/fa/review_pack_40.json with 40 English-source rows where
post_edit_output != engine_output:
  - 14 from Stratum B
  - 14 from Stratum A
  - 12 from Stratum C
Wraps changed words in ⟦ ⟧ in post_edit_output.
"""
import csv
import difflib
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from tools.fa_eval import is_english_source
from fa_postedit import post_edit

def highlight_diff(raw, post):
    # Word-level alignment
    r_toks = re.findall(r"\S+|\s+", raw)
    p_toks = re.findall(r"\S+|\s+", post)

    matcher = difflib.SequenceMatcher(None, r_toks, p_toks)
    out = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out.extend(p_toks[j1:j2])
        elif tag in ("replace", "insert"):
            chunk = "".join(p_toks[j1:j2])
            out.append(f"⟦{chunk}⟧")
    return "".join(out)

def main():
    tsv_path = REPO / "data" / "fa" / "golden_template.tsv"
    lines = tsv_path.read_text(encoding="utf-8-sig").splitlines()
    reader = csv.reader(lines, delimiter="\t")
    header = next(reader)

    strata_rows = {"A": [], "B": [], "C": []}
    for i, r in enumerate(reader):
        if len(r) < 4:
            continue
        art_id = r[0]
        en = r[1]
        raw = r[2]
        pe = post_edit(raw)  # current post_edit

        if not is_english_source(en) or "courtier en ligne" in en.lower():
            continue
        if pe == raw:
            continue  # only keep rows where post_edit changed something!

        st = "ABC"[min(i // 100, 2)]
        strata_rows[st].append({
            "id": art_id,
            "stratum": st,
            "template_line": i + 2,
            "en": en,
            "raw": raw,
            "post": pe,
            "post_highlighted": highlight_diff(raw, pe),
        })

    print(f"Available changed rows: A={len(strata_rows['A'])}, B={len(strata_rows['B'])}, C={len(strata_rows['C'])}")

    # We need: 14 from B, 14 from A, 12 from C
    picked_b = strata_rows["B"][:14]
    picked_a = strata_rows["A"][:14]
    picked_c = strata_rows["C"][:12]

    pack = picked_a + picked_b + picked_c
    print(f"Selected total: {len(pack)} (A={len(picked_a)}, B={len(picked_b)}, C={len(picked_c)})")

    out_json = REPO / "data" / "fa" / "review_pack_40.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(pack)} rows to {out_json}")

if __name__ == "__main__":
    main()
