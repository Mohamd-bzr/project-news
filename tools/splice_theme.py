#!/usr/bin/env python3
"""Replace the <style> block of dashboard_html.py with a stylesheet file.

The redesign authors the whole stylesheet from scratch as an ordinary .css
file; this applies it. The python source uses CRLF, so the CSS is normalised to
CRLF on the way in and the file is byte-identical apart from the replaced
region.

    python tools/splice_theme.py tools/theme_v3.css           # apply
    python tools/splice_theme.py tools/theme_v3.css --check    # dry run
"""

import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "dashboard_html.py")


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

    with io.open(TARGET, "r", encoding="utf-8", newline="") as fh:
        src = fh.read()

    m = re.search(r"<style>.*?</style>", src, re.S)
    if not m or "</style>" not in m.group(0):
        print("! could not find the <style> block")
        return 2

    old = m.group(0)
    new = "<style>\r\n" + css.lstrip("\r\n") + "\r\n</style>"
    print(f"  old style block: {old.count(chr(10))} lines, {len(old)} bytes")
    print(f"  new style block: {new.count(chr(10))} lines, {len(new)} bytes")
    if args.check:
        return 0

    src = src[: m.start()] + new + src[m.end():]
    with io.open(TARGET, "w", encoding="utf-8", newline="") as fh:
        fh.write(src)
    print(f"  wrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
