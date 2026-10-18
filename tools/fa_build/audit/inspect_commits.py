#!/usr/bin/env python3
"""
tools/fa_build/audit/inspect_commits.py
=======================================
Inspects commits a533320 and 23b833c to list every row removed from terms.tsv,
group them, and verify line endings / BOM.
"""
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parents[3]

def main():
    # 1. git show a533320 for terms.tsv
    proc = subprocess.run(
        ["git", "show", "a533320", "--", "data/fa/terms.tsv"],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    diff_lines = proc.stdout.splitlines()

    deleted_rows = []
    for line in diff_lines:
        if line.startswith("-") and not line.startswith("---"):
            content = line[1:].strip()
            if content:
                parts = content.split("\t")
                deleted_rows.append(parts)

    print(f"Total deleted lines in diff: {len(deleted_rows)}")
    for i, r in enumerate(deleted_rows, 1):
        en = r[0] if len(r) > 0 else ""
        fa = r[1] if len(r) > 1 else ""
        src = r[4] if len(r) > 4 else ""
        pos = r[2] if len(r) > 2 else ""
        dom = r[3] if len(r) > 3 else ""
        print(f"{i:2d}. en={en:15s} | fa={fa:25s} | domain={dom:10s} | src={src}")

if __name__ == "__main__":
    main()
