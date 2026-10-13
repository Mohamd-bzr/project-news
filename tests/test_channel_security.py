"""Security tests for web/channel.js link sinks and URL scheme sanitization."""

import json
import pathlib
import shutil
import subprocess

import pytest

CHANNEL_JS = pathlib.Path(__file__).resolve().parent.parent / "web" / "channel.js"
TGNEWS_JS = pathlib.Path(__file__).resolve().parent.parent / "web" / "tgnews.js"


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
    """Verify Channel._safeHref and TgNews._safeHref disallow non-http(s) schemes and preserve valid URLs."""
    node = _node()
    harness = f"""
    global.window = global;
    require({json.dumps(str(CHANNEL_JS))});
    require({json.dumps(str(TGNEWS_JS))});
    const mal = {json.dumps(MALICIOUS_VECTORS)};
    const ben = {json.dumps(BENIGN_VECTORS)};

    for (const mod of [window.Channel, window.TgNews]) {{
        for (const v of mal) {{
            const res = mod._safeHref(v);
            if (res !== '#') {{
                console.error(JSON.stringify({{ err: 'Malicious scheme not neutralized', input: v, got: res }}));
                process.exit(1);
            }}
        }}

        for (const v of ben) {{
            const res = mod._safeHref(v);
            if (res !== v) {{
                console.error(JSON.stringify({{ err: 'Benign URL mutated or rejected', input: v, got: res }}));
                process.exit(1);
            }}
        }}

        // Empty or falsy input
        if (mod._safeHref('') !== '#' || mod._safeHref(null) !== '#' || mod._safeHref(undefined) !== '#') {{
            console.error('Falsy input must return #');
            process.exit(1);
        }}
    }}

    console.log('OK');
    """

    res = subprocess.run([node, "-e", harness], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node security harness failed:\n{res.stdout}\n{res.stderr}"


def test_channel_link_sinks_and_noopener():
    """Verify that all link sinks in channel.js and tgnews.js use safeHref, attr, and rel='noopener noreferrer'."""
    code_channel = CHANNEL_JS.read_text(encoding="utf-8")
    assert "function safeHref(" in code_channel
    assert "_safeHref: safeHref" in code_channel
    assert 'attr(safeHref(it.link))' in code_channel
    assert 'rel="noopener noreferrer"' in code_channel
    assert 'attr(safeHref(l.link))' in code_channel
    assert 'safeHref(it.link)' in code_channel
    assert "noopener,noreferrer" in code_channel

    code_tg = TGNEWS_JS.read_text(encoding="utf-8")
    assert "function safeHref(" in code_tg
    assert "_safeHref: safeHref" in code_tg
    assert 'attr(safeHref(p.url))' in code_tg
    assert 'rel="noopener noreferrer"' in code_tg

