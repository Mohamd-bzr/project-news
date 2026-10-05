#!/usr/bin/env python3
"""Temporary one-shot: remove the DL2 DOM-retrofit blocks.

Each block is located by its opening comment and removed through its closing
`})();`, so no other line moves. Prints the ranges it removed and refuses to
touch anything it cannot find exactly once.
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "dashboard_html.py")

ANCHORS = [
    "/* ── DL2 step 3: one language policy for the chrome",
    "/* ── DL2 step 4: retire the repeated inline typography hack",
    "/* ── DL2 phase 5: group the nav rail into clusters + collapsible rail",
    "/* ══ STAGED ENTRANCE ══",
]

with io.open(TARGET, "r", encoding="utf-8", newline="") as fh:
    src = fh.read()
lines = src.split("\n")

for anchor in ANCHORS:
    hits = [i for i, l in enumerate(lines) if l is not None and l.startswith(anchor)]
    if len(hits) != 1:
        print(f"  ! {anchor[:48]}… found {len(hits)} times — skipped")
        continue
    start = hits[0]
    end = None
    for j in range(start, min(start + 200, len(lines))):
        if lines[j].startswith("})();"):
            end = j
            break
    if end is None:
        print("  ! " + anchor[:48] + "… has no closing marker — skipped")
        continue
    print(f"  - lines {start+1}-{end+1}: {lines[start].strip()[:64]}")
    for j in range(start, end + 1):
        lines[j] = None

out = "\n".join(l for l in lines if l is not None)
with io.open(TARGET, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)
print(f"  wrote {TARGET}: {src.count(chr(10))} -> {out.count(chr(10))} lines")
sys.exit(0)
