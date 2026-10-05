#!/usr/bin/env python3
"""
Syntax-check every inline <script> block inside dashboard_html.py.

The dashboard is one giant Python string: a stray brace in any of its script
blocks is invisible to `python -m py_compile` and only shows up as a blank page
in the browser. This pulls each block out and runs `node --check` on it, so a
broken edit fails here in a second instead of at runtime.

Usage:  python tools/check_dashboard_js.py [--list]
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "dashboard_html.py"
WEB = ROOT / "web"          # files the page loads by URL, not from the Python string


def script_blocks(text: str):
    """Every `<script>…</script>` body in the page (no src-only tags)."""
    out = []
    for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", text, re.S):
        body = m.group(1)
        if body.strip():
            out.append(body)
    return out


def main() -> int:
    node = shutil.which("node")
    if not node:
        print("node not found on PATH — cannot check JavaScript")
        return 2
    text = SOURCE.read_text(encoding="utf-8", errors="replace")
    blocks = script_blocks(text)
    print(f"{len(blocks)} inline script block(s), "
          f"{sum(b.count(chr(10)) for b in blocks)} lines total")
    if "--list" in sys.argv:
        for i, b in enumerate(blocks, 1):
            print(f"  block #{i}: {b.count(chr(10))} lines")
    bad = 0

    def check(label, path):
        """node --check one file, counting it against the exit status."""
        nonlocal bad
        proc = subprocess.run([node, "--check", str(path)],
                              capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"  [ok]   {label}: parses")
        else:
            bad += 1
            print(f"  [FAIL] {label}:")
            print("\n".join("         " + ln
                            for ln in (proc.stderr or "").splitlines()[:14]))

    with tempfile.TemporaryDirectory() as tmp:
        for i, body in enumerate(blocks, 1):
            path = Path(tmp) / f"block{i}.js"
            path.write_text(body, encoding="utf-8")
            check(f"block #{i}", path)

    # The offline layer is served from disk (the service worker must own the
    # root scope, so it cannot live inside the Python string). Those files are
    # just as invisible to `py_compile` as the inline blocks, so they are
    # checked here too — same gate, same failure mode.
    if WEB.is_dir():
        files = sorted(WEB.glob("*.js"))
        print(f"{len(files)} file(s) in web/")
        for path in files:
            if "--list" in sys.argv:
                print(f"  {path.name}: {path.read_text(encoding='utf-8').count(chr(10))} lines")
            check(path.name, path)
    else:
        print("web/ not found — skipping the service worker / storage engine")

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
