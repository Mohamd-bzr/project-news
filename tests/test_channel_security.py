"""Security tests for web/channel.js link sinks and URL scheme sanitization."""

import json
import pathlib
import shutil
import subprocess

import pytest

CHANNEL_JS = pathlib.Path(__file__).resolve().parent.parent / "web" / "channel.js"


def _node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not on PATH")
    return node


MALICIOUS_VECTORS = [
    "javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    " javascript:alert(1)",
    "\tjavascript:alert(1)",
    "\njavascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    "vbscript:alert(1)",
    "vbscript:x",
    "file:///etc/passwd",
    "blob:https://example.com/uuid",
]

BENIGN_VECTORS = [
    "https://example.com/a?b=1&c=2",
    "http://example.com/news/123",
    "https://t.me/example_channel/42",
]


def test_channel_safe_href_schemes():
    """Verify Channel._safeHref disallows non-http(s) schemes and preserves valid URLs."""
    node = _node()
    harness = f"""
    global.window = global;
    require({json.dumps(str(CHANNEL_JS))});
    const mal = {json.dumps(MALICIOUS_VECTORS)};
    const ben = {json.dumps(BENIGN_VECTORS)};

    for (const v of mal) {{
        const res = window.Channel._safeHref(v);
        if (res !== '#') {{
            console.error(JSON.stringify({{ err: 'Malicious scheme not neutralized', input: v, got: res }}));
            process.exit(1);
        }}
    }}

    for (const v of ben) {{
        const res = window.Channel._safeHref(v);
        if (res !== v) {{
            console.error(JSON.stringify({{ err: 'Benign URL mutated or rejected', input: v, got: res }}));
            process.exit(1);
        }}
    }}

    // Empty or falsy input
    if (window.Channel._safeHref('') !== '#' || window.Channel._safeHref(null) !== '#' || window.Channel._safeHref(undefined) !== '#') {{
        console.error('Falsy input must return #');
        process.exit(1);
    }}

    console.log('OK');
    """

    res = subprocess.run([node, "-e", harness], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node security harness failed:\n{res.stdout}\n{res.stderr}"


def test_channel_link_sinks_and_noopener():
    """Verify that all link sinks in channel.js use safeHref, attr, and rel='noopener noreferrer'."""
    code = CHANNEL_JS.read_text(encoding="utf-8")

    # safeHref definition and export
    assert "function safeHref(" in code
    assert "_safeHref: safeHref" in code

    # itemCard linkAction
    assert 'attr(safeHref(it.link))' in code
    assert 'rel="noopener noreferrer"' in code

    # openDispatchModal link
    assert 'attr(safeHref(l.link))' in code

    # openSource fallback
    assert 'safeHref(it.link)' in code
    assert "noopener,noreferrer" in code
