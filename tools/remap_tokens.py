#!/usr/bin/env python3
"""One-shot: repoint var() references outside the <style> block at DL3 tokens.

The stylesheet was replaced wholesale in the redesign, so every var() that the
JS templates and inline styles still carried from the old palette has to follow
the new names. Only text after </style> is touched, so the stylesheet itself is
never rewritten. Prints a per-name count and is safe to re-run.
"""

import collections
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "dashboard_html.py")

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
    with io.open(TARGET, "r", encoding="utf-8", newline="") as fh:
        src = fh.read()
    cut = src.index("</style>")
    head, tail = src[:cut], src[cut:]

    counts = collections.Counter()
    for old, new in MAP.items():
        pat = r"var\(\s*" + re.escape(old) + r"(\s*[,)])"
        if not re.search(pat, tail):
            continue
        tail, n = re.subn(pat, "var(" + new + r"\1", tail)
        counts[f"{old} -> {new}"] += n

    if not counts:
        print("  nothing to remap")
        return 0
    for k, v in counts.most_common():
        print(f"  {k}: {v}")
    with io.open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(head + tail)
    print(f"  wrote {TARGET}")
    leftover = sorted(set(re.findall(r"var\(\s*(--[\w-]+)", tail)))
    print("  tokens still referenced after </style>:", leftover)
    return 0


if __name__ == "__main__":
    sys.exit(main())
