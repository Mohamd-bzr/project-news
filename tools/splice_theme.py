#!/usr/bin/env python3
"""Replace the dashboard's stylesheet with a stylesheet file.

The redesign authors the whole stylesheet from scratch as an ordinary .css file;
this applies it. Since the page is assembled from `web/fragments/`, the
stylesheet is a single file — `web/fragments/10_style.css` — so there is no
`<style>` block to search for any more: the `<style>` and `</style>` tags live in
the neighbouring HTML slices and are deliberately not touched here.

    python tools/splice_theme.py tools/theme_v3.css           # apply
    python tools/splice_theme.py tools/theme_v3.css --check    # dry run
"""

import argparse
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "web", "fragments", "10_style.css")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("css", nargs="+", help="stylesheet files, concatenated in the order given")
    ap.add_argument("--check", action="store_true", help="report sizes, write nothing")
    args = ap.parse_args()

    chunks = []
    for path in args.css:
        with io.open(path, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
        print(f"  + {os.path.relpath(path, ROOT)}: {text.count(chr(10))} lines")
        chunks.append(text.replace("\r\n", "\n").rstrip("\n"))
    css = "\n".join(chunks)
    css = css.replace("\r\n", "\n").replace("\n", "\r\n").rstrip("\r\n")

    if not os.path.isfile(TARGET):
        print(f"! {os.path.relpath(TARGET, ROOT)} is missing — the page's "
              "stylesheet slice (web/fragments/10_style.css) has to exist")
        return 2

    with io.open(TARGET, "r", encoding="utf-8", newline="") as fh:
        old = fh.read()

    print(f"  old sheet: {old.count(chr(10))} lines, {len(old)} bytes")
    print(f"  new sheet: {css.count(chr(10))} lines, {len(css)} bytes")
    if args.check:
        return 0

    with io.open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(css)
    print(f"  wrote {os.path.relpath(TARGET, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
