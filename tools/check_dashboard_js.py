#!/usr/bin/env python3
"""
Syntax-check every inline <script> block of the dashboard, and every JS fragment.

The page is assembled from `web/fragments/` (see `dashboard_html.py`): a stray
brace in any of its script blocks is invisible to `python -m py_compile` and
only shows up as a blank page in the browser. This pulls each block out of the
assembled page and runs `node --check` on it, so a broken edit fails here in a
second instead of at runtime — and it checks the fragment files on disk as
well, so a slice corrupted outside the assembly step is caught too.

Usage:  python tools/check_dashboard_js.py [--list]
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRAGMENTS = ROOT / "web" / "fragments"   # the page's source slices
WEB = ROOT / "web"          # files the page loads by URL, not from the fragments


def page_text() -> str:
    """The page as the browser receives it — assembled by the real loader."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from dashboard_html import APP_HTML     # noqa: PLC0415 — own-path import
    return APP_HTML


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
    text = page_text()
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

    # The blocks above come from these files. Checking them on disk as well means
    # a fragment that no longer parses fails even if the assembly step is broken.
    if FRAGMENTS.is_dir():
        files = sorted(FRAGMENTS.glob("*.js"))
        print(f"{len(files)} script fragment(s) in web/fragments/")
        for path in files:
            if "--list" in sys.argv:
                print(f"  {path.name}: "
                      f"{path.read_text(encoding='utf-8').count(chr(10))} lines")
            check(path.name, path)
    else:
        print("web/fragments/ not found — skipping the page's script slices")

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
