"""The dashboard SPA, assembled from the slices in ``web/fragments/``.

This module used to *be* the page: one 9,286-line raw Python string holding the
markup, the 2,039-line stylesheet and 6,000 lines of inline JavaScript. Nobody —
human or model — could see it in one view, so edits were either blind or a
full-file rewrite, and a stray ``\"\"\"`` or one bad backslash took the whole UI
down without ``py_compile`` noticing.

The page now lives in ``web/fragments/`` as orderable slices cut at its own
structural boundaries (``<style>`` … ``</style>``, each ``<script>`` block, each
VIEW section) — never mid-function. ``APP_HTML`` is their concatenation and is
byte-for-byte the string this module used to hold; the split was verified with a
sha256 of the assembled text before and after.

Notes for whoever edits this next:

* Assembly order is the sorted fragment file names, and the numeric prefixes are
  chosen so that the sorted order is the reading order. ``_EXPECTED_ORDER``
  pins the list: a fragment that is added, renamed or deleted fails loudly here
  instead of silently shipping a page with a missing view or a dead button.
* Fragments are read in text mode on purpose. The repo stores LF but checks out
  CRLF on Windows, and universal-newline reading yields the same ``\\n``-only
  text on both, so ``APP_HTML`` cannot drift with the platform.
* CSS and JS slices hold code only; the ``<style>``/``<script>`` tags live in the
  neighbouring HTML slices. That is what lets ``node --check`` run on a JS
  fragment directly — see ``tools/check_dashboard_js.py``.
"""
from __future__ import annotations

from pathlib import Path

FRAGMENTS_DIR = Path(__file__).resolve().parent / "web" / "fragments"

#: Fragment file names in assembly order. The directory listing is validated
#: against this tuple, so neither an unlisted file nor a missing one can pass.
_EXPECTED_ORDER: tuple[str, ...] = (
    "00_head.html",
    "10_style.css",
    "20_head_tail.html",
    "30_body_head.html",
    "40_nav.html",
    "50_views.html",
    "60_script_01.js",
    "61_gap_01.html",
    "62_script_02.js",
    "63_gap_02.html",
    "64_script_03.js",
    "65_gap_03.html",
    "66_script_04.js",
    "67_gap_04.html",
    "68_script_05.js",
    "69_gap_05.html",
    "70_script_06.js",
    "71_gap_06.html",
    "72_script_07.js",
    "99_tail.html",
)


def fragment_path(name: str) -> Path:
    """Absolute path of one fragment, resolved from this file's location."""
    return FRAGMENTS_DIR / name


def load_fragments() -> list[tuple[str, str]]:
    """Read every fragment in assembly order: ``[(name, text), …]``."""
    if not FRAGMENTS_DIR.is_dir():
        raise RuntimeError(
            f"dashboard fragments are missing: {FRAGMENTS_DIR} does not exist. "
            "The page is assembled from web/fragments/ — restore the directory "
            "instead of inlining the page back into this module.")

    missing = [n for n in _EXPECTED_ORDER if not fragment_path(n).is_file()]
    if missing:
        raise RuntimeError(f"missing dashboard fragment(s): {', '.join(missing)}")

    present = {p.name for p in FRAGMENTS_DIR.iterdir() if p.is_file()}
    unlisted = sorted(present - set(_EXPECTED_ORDER))
    if unlisted:
        raise RuntimeError(
            f"unlisted file(s) in {FRAGMENTS_DIR.name}/: {', '.join(unlisted)}. "
            "Add them to _EXPECTED_ORDER (in reading order) or move them out — "
            "an unlisted fragment is never served.")

    # newline=None (the default) is deliberate: it normalises CRLF to LF, so a
    # Windows checkout and a Linux checkout assemble the identical page.
    return [(name, fragment_path(name).read_text(encoding="utf-8"))
            for name in _EXPECTED_ORDER]


def assemble() -> str:
    """The whole page: every fragment, concatenated in order."""
    return "".join(text for _, text in load_fragments())


APP_HTML = assemble()
