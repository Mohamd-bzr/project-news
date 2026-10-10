"""Every inline handler in the dashboard must resolve to a defined function.

The SPA wires 100+ buttons through inline attributes (`onclick="saveSettings()"`).
Nothing in Python, nothing in `node --check` and nothing in the browser's
console-at-load will tell you when one of those names stops existing: the page
renders fine and the button just does nothing. A rename inside the 4.8k-line
core script block is a silent, 161-button-wide outage.

This test closes that hole. It pulls the handler attributes out of the assembled
`APP_HTML`, collects the top-level functions they call, and asserts every one of
them is defined somewhere in the page's own script blocks.
"""
from __future__ import annotations

import re

import pytest

from dashboard_html import APP_HTML

# Attributes that can carry a handler expression.
HANDLER_ATTR_RE = re.compile(
    r"""\bon(?:click|change|input|keydown|keyup|keypress|dblclick|submit)\s*=\s*"([^"]*)\"""")
# A call to a name that is NOT a property access (`a.b(`) and not a method.
TOP_LEVEL_CALL_RE = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(")
SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)

# JS syntax and globals that can legitimately appear before `(` in an
# attribute expression without needing a definition in this page.
JS_KEYWORDS = {
    "if", "else", "for", "while", "do", "switch", "case", "return", "typeof",
    "instanceof", "in", "of", "new", "delete", "void", "await", "yield",
    "function", "catch", "try", "throw", "class", "super", "this",
}
JS_BUILTINS = {
    "setTimeout", "setInterval", "clearTimeout", "clearInterval",
    "requestAnimationFrame", "parseInt", "parseFloat", "isNaN", "Number",
    "String", "Boolean", "JSON", "Object", "Array", "Math", "Date", "RegExp",
    "Map", "Set", "Promise", "Error", "encodeURIComponent", "decodeURIComponent",
    "console", "document", "window", "fetch", "alert", "confirm", "prompt",
    "URL", "Blob", "File", "TextEncoder", "Intl", "queueMicrotask",
}

# Handlers the shell cannot work without; losing one of these is a regression
# even if some other definition happens to satisfy the generic check.
CRITICAL_HANDLERS = {"showView", "toggleTheme", "doRefresh", "saveSettings", "toFa"}


def _markup_and_js(html: str) -> tuple[str, str]:
    """Split the page into (markup without script bodies, concatenated scripts)."""
    body_at = html.index("<body>")
    body = html[body_at:]
    js = "\n".join(SCRIPT_RE.findall(body))
    markup = SCRIPT_RE.sub("", body)
    return markup, js


def _handler_calls(markup: str) -> dict[str, set[str]]:
    """name -> the raw handler attributes that call it at the top level."""
    calls: dict[str, set[str]] = {}
    for expr in HANDLER_ATTR_RE.findall(markup):
        for name in TOP_LEVEL_CALL_RE.findall(expr):
            if name in JS_KEYWORDS or name in JS_BUILTINS:
                continue
            calls.setdefault(name, set()).add(expr.strip())
    return calls


def _defined_names(js: str) -> set[str]:
    """Names the page defines: declarations, assignments and window exports."""
    defined: set[str] = set()
    defined |= set(re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)", js))
    defined |= set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)", js))
    defined |= set(re.findall(r"\bwindow\.([A-Za-z_$][\w$]*)\s*=", js))
    # object-literal / class members: `name: function`, `name: (a) =>`, `name(a){`
    defined |= set(re.findall(r"([A-Za-z_$][\w$]*)\s*:\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>)", js))
    defined |= set(re.findall(r"^\s*([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{", js, re.M))
    # members of the page's namespace objects: UI.foo = ..., CAL.bar = ...
    defined |= set(re.findall(r"\b(?:UI|CAL|CHART|TVW|DATA|LIVE|State)\.([A-Za-z_$][\w$]*)\s*=", js))
    return defined


@pytest.fixture(scope="module")
def page() -> tuple[dict[str, set[str]], set[str]]:
    markup, js = _markup_and_js(APP_HTML)
    return _handler_calls(markup), _defined_names(js)


def test_the_extractor_still_sees_the_wiring(page):
    """Canary: if this fails the regexes stopped matching, not the page."""
    calls, _ = page
    assert len(calls) >= 35, (
        "the inline-handler extractor found suspiciously few names — "
        "the markup or the regex changed shape, fix the test, not the page")


def test_critical_handlers_are_wired_and_defined(page):
    calls, defined = page
    for name in sorted(CRITICAL_HANDLERS):
        assert name in calls, f"{name} is no longer wired to any inline handler"
        assert name in defined, f"{name} is wired but no longer defined"


def test_every_inline_handler_is_defined(page):
    calls, defined = page
    missing = {name: exprs for name, exprs in calls.items() if name not in defined}
    detail = "\n".join(
        f"  {name}() <- {sorted(exprs)[0][:120]}" for name, exprs in sorted(missing.items()))
    assert not missing, (
        f"{len(missing)} inline handler(s) call an undefined function — the "
        f"button renders and does nothing:\n{detail}")
