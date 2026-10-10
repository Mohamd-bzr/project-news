#!/usr/bin/env python3
"""One-shot: repoint var() references outside the stylesheet at DL3 tokens.

The stylesheet was replaced wholesale in the redesign, so every var() that the
JS templates and inline styles still carried from the old palette has to follow
the new names. Only the non-stylesheet fragments are touched — the stylesheet
slice (`10_style.css`) is a finished sheet and is never rewritten. Prints a
per-name count and is safe to re-run.

    python tools/remap_tokens.py
"""

import collections
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAGMENTS = os.path.join(ROOT, "web", "fragments")
STYLESHEET = "10_style.css"

MAP = {
    "--muted": "--ink-3",
    "--faint": "--ink-4",
    "--body": "--ink-2",
    "--text": "--ink-1",
    "--red": "--dn",
    "--green": "--up",
    "--cyan": "--info",
    "--purple": "--info",
    "--slate": "--ink-3",
    "--amber": "--warn",
    "--gold": "--cu-hi",
    "--copper-hi": "--cu-hi",
    "--copper-txt": "--cu-txt",
    "--copper-deep": "--cu-2",
    "--copper-line": "--cu-line",
    "--copper-bg": "--cu-wash",
    "--copper": "--cu",
    "--border": "--rule",
    "--line": "--rule-2",
    "--surface-2": "--panel-2",
    "--surface-3": "--panel-3",
    "--surface": "--panel",
    "--card": "--panel",
    "--radius-sm": "--r1",
    "--radius-lg": "--r3",
    "--radius-xl": "--r3",
    "--radius": "--r2",
    "--topbar-height": "--topbar-h",
}


def main() -> int:
    if not os.path.isdir(FRAGMENTS):
        print(f"! {os.path.relpath(FRAGMENTS, ROOT)} is missing")
        return 2

    counts = collections.Counter()
    targets = sorted(name for name in os.listdir(FRAGMENTS)
                     if name != STYLESHEET and os.path.isfile(os.path.join(FRAGMENTS, name)))
    for name in targets:
        path = os.path.join(FRAGMENTS, name)
        with io.open(path, "r", encoding="utf-8", newline="") as fh:
            src = fh.read()

        out, per_file = src, 0
        for old, new in MAP.items():
            pat = r"var\(\s*" + re.escape(old) + r"(\s*[,)])"
            if not re.search(pat, out):
                continue
            out, n = re.subn(pat, "var(" + new + r"\1", out)
            counts[f"{old} -> {new}"] += n
            per_file += n
        if per_file:
            with io.open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(out)

    if not counts:
        print("  nothing to remap")
        return 0
    for k, v in counts.most_common():
        print(f"  {k}: {v}")
    print(f"  files touched: {len(targets)}")

    leftover = set()
    for name in targets:
        with io.open(os.path.join(FRAGMENTS, name), "r", encoding="utf-8", newline="") as fh:
            leftover |= set(re.findall(r"var\(\s*(--[\w-]+)", fh.read()))
    print(f"  tokens still referenced outside {STYLESHEET}: {sorted(leftover)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
