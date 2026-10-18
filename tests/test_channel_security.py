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
    assert 'attr(safeHref(esc(p.url)))' in code_tg
    assert 'rel="noopener noreferrer"' in code_tg


def test_server_safe_url_filter():
    """Verify app._safe_url and _ser_article neutralize dangerous schemes on server."""
    from app import _safe_url, _ser_article

    for v in MALICIOUS_VECTORS:
        assert _safe_url(v) == "", f"Malicious scheme not neutralized: {v}"

    for v in BENIGN_VECTORS:
        assert _safe_url(v) == v, f"Benign URL rejected or modified: {v}"

    assert _safe_url("") == ""
    assert _safe_url(None) == ""

    # Test serializer integration
    art = {"id": "1", "title": "t", "link": "javascript:alert(1)", "image": "vbscript:x"}
    ser = _ser_article(art)
    assert ser["link"] == ""
    assert ser["image"] == ""

    art_ok = {"id": "2", "title": "t", "link": "https://example.com/a", "image": "http://example.com/b.jpg"}
    ser_ok = _ser_article(art_ok)
    assert ser_ok["link"] == "https://example.com/a"
    assert ser_ok["image"] == "http://example.com/b.jpg"


def test_settings_messenger_escaping():
    """Verify that error, hint, and chat titles in settings fragment are HTML escaped against XSS."""
    node = _node()
    frag_path = pathlib.Path(__file__).resolve().parent.parent / "web" / "fragments" / "62_script_02.js"
    assert frag_path.exists()
    harness = f"""
    const fs = require('fs');
    const code = fs.readFileSync({json.dumps(str(frag_path))}, 'utf8');

    // Minimal DOM / runtime mock
    function esc(s) {{
        return String(s || '').replace(/&/g, '&amp;')
                              .replace(/</g, '&lt;')
                              .replace(/>/g, '&gt;')
                              .replace(/"/g, '&quot;')
                              .replace(/'/g, '&#39;');
    }}

    const xss = '<img src=x onerror=alert(1)>';
    const escaped = esc(xss);

    // Verify error and hint interpolations in Bale block are escaped
    const baleErrMatch = code.match(/box\\.innerHTML\\s*=\\s*`<div[^>]*>✗ \\${{([^}}]+)}}<\\/div>`/);
    if (!baleErrMatch || !baleErrMatch[1].includes('esc(')) {{
        console.error('Bale box.innerHTML error is not escaped with esc()');
        process.exit(1);
    }}

    const baleHintMatch = code.match(/⚠️ \\${{([^}}]+)}}/);
    if (!baleHintMatch || !baleHintMatch[1].includes('esc(')) {{
        console.error('Bale box.innerHTML hint is not escaped with esc()');
        process.exit(1);
    }}

    // Verify chat title interpolations in Bale and Telegram loops
    const chatTitleMatches = code.matchAll(/<span><b>\\${{([^}}]+)}}<\\/b>/g);
    let count = 0;
    for (const m of chatTitleMatches) {{
        count++;
        if (!m[1].includes('esc(')) {{
            console.error('Chat title interpolation not escaped: ' + m[1]);
            process.exit(1);
        }}
    }}
    if (count < 2) {{
        console.error('Expected at least 2 chat title loops (Bale & Telegram), found: ' + count);
        process.exit(1);
    }}

    console.log('OK');
    """

    res = subprocess.run([node, "-e", harness], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node security harness failed:\n{res.stdout}\n{res.stderr}"


def test_html_builders_xss_vectors():
    """Verify that HTML builders neutralize <img src=x onerror=alert(1)> and "><svg onload=alert(1)>."""
    node = _node()
    frag_62 = pathlib.Path(__file__).resolve().parent.parent / "web" / "fragments" / "62_script_02.js"
    frag_64 = pathlib.Path(__file__).resolve().parent.parent / "web" / "fragments" / "64_script_03.js"
    tg_js = pathlib.Path(__file__).resolve().parent.parent / "web" / "tgnews.js"

    harness = f"""
    const fs = require('fs');
    const vm = require('vm');

    const PAYLOADS = [
        '<img src=x onerror=alert(1)>',
        '"><svg onload=alert(1)>'
    ];

    const sandbox = {{
        window: {{}},
        document: {{
            getElementById: (id) => ({{
                value: '',
                textContent: '',
                innerHTML: '',
                style: {{}},
                classList: {{ add: () => {{}}, remove: () => {{}}, toggle: () => false }},
                querySelectorAll: () => [],
                querySelector: () => null,
            }}),
            createElement: (t) => ({{
                style: {{}},
                setAttribute: () => {{}},
                querySelector: () => null,
            }}),
            addEventListener: () => {{}},
            removeEventListener: () => {{}},
        }},
        location: {{ protocol: 'https:', host: 'localhost' }},
        localStorage: {{ getItem: () => null, setItem: () => {{}} }},
        DATA: {{ articles: [], sources: [], config: {{ assets: [] }}, rules: {{}}, market: {{}}, assets_meta: {{}}, kind_labels: {{}} }},
        UI: {{ view: 'feed', asset: 'all', topic: 'all' }},
        console: console,
        setTimeout: () => {{}},
        clearTimeout: () => {{}},
        requestAnimationFrame: (cb) => setTimeout(cb, 16),
        cancelAnimationFrame: () => {{}},
        fetch: () => new Promise(() => {{}}),
        addEventListener: () => {{}},
        removeEventListener: () => {{}},
    }};
    sandbox.window = sandbox;
    vm.createContext(sandbox);

    vm.runInContext(fs.readFileSync({json.dumps(str(frag_62))}, 'utf8'), sandbox);
    vm.runInContext(fs.readFileSync({json.dumps(str(frag_64))}, 'utf8'), sandbox);
    vm.runInContext(fs.readFileSync({json.dumps(str(tg_js))}, 'utf8'), sandbox);

    function assertSafe(html, payload, builderName) {{
        if (html.includes(payload)) {{
            console.error('XSS payload found unescaped in ' + builderName + ': ' + payload);
            process.exit(1);
        }}
        // Payload must appear safely escaped
        const escPayload = sandbox.esc(payload);
        if (!html.includes(escPayload)) {{
            console.error('Escaped payload not found in ' + builderName + ': ' + html);
            process.exit(1);
        }}
    }}

    for (const p of PAYLOADS) {{
        // 1. cardHTML (asset symbol and topic_fa)
        const c1 = sandbox.cardHTML({{ id: '1', title: 't', assets: [p], source: 's' }});
        assertSafe(c1, p, 'cardHTML (asset)');
        const c2 = sandbox.cardHTML({{ id: '2', title: 't', topic_fa: p, source: 's' }});
        assertSafe(c2, p, 'cardHTML (topic_fa)');

        // 2. leadCardHTML (asset symbol and topic)
        const l1 = sandbox.leadCardHTML({{ id: '3', title: 't', assets: [p], topic: 'tech', source: 's' }});
        assertSafe(l1, p, 'leadCardHTML (asset)');
        const l2 = sandbox.leadCardHTML({{ id: '4', title: 't', assets: [], topic_fa: p, source: 's' }});
        assertSafe(l2, p, 'leadCardHTML (topic)');

        // 3. ideaCardHTML (symbol_dir)
        const i1 = sandbox.ideaCardHTML({{ id: '5', title: 't', symbol_dir: p }});
        assertSafe(i1, p, 'ideaCardHTML (symbol_dir)');

        // 4. tbChipHTML
        const tb = sandbox.tbChipHTML(sandbox.esc(p), 'setTopicFilter(' + sandbox.jsArg(p) + ')');
        assertSafe(tb, p, 'tbChipHTML');

        // 5. etfCardHTML
        const etf = sandbox.etfCardHTML('BTC', {{ name: p, group: p, change_pct: 1.5 }});
        assertSafe(etf, p, 'etfCardHTML');
    }}

    // 6. verify TgNews.renderChips and detectBaleChat patterns
    const code62 = fs.readFileSync({json.dumps(str(frag_62))}, 'utf8');
    if (!code62.includes('data-bale-chatpick=')) {{
        console.error('detectBaleChat must use data-bale-chatpick instead of inline onclick');
        process.exit(1);
    }}

    const codetg = fs.readFileSync({json.dumps(str(tg_js))}, 'utf8');
    if (!codetg.includes('TgNews.pick(') || !codetg.includes('jsArg(s.handle)')) {{
        console.error('TgNews.renderChips must wrap s.handle in jsArg()');
        process.exit(1);
    }}

    console.log('OK');
    process.exit(0);
    """

    res = subprocess.run([node, "-e", harness], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0, f"Node XSS vectors harness failed:\n{res.stdout}\n{res.stderr}"


def test_security_headers():
    """Verify security headers on /, /api/health, an API route, web asset, and proxy-image."""
    import hashlib
    from app import app, IMAGE_CACHE_DIR
    client = app.test_client()

    # 1. Routes check
    routes = [
        "/",
        "/api/health",
        "/api/news",
        "/manifest.webmanifest",
    ]

    for route in routes:
        resp = client.get(route)
        assert resp.headers.get("X-Content-Type-Options") == "nosniff", f"Missing nosniff on {route}"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN", f"Missing SAMEORIGIN on {route}"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin", f"Missing Referrer-Policy on {route}"
        assert "Content-Security-Policy" not in resp.headers, f"CSP must not be set on {route}"

    # 2. Proxy image route (verifying existing headers stay and new ones are added)
    raw_url = "https://example.com/test_security_header_image.jpg"
    url_hash = hashlib.sha256(raw_url.encode("utf-8")).hexdigest()
    cached_file = IMAGE_CACHE_DIR / url_hash
    meta_file = IMAGE_CACHE_DIR / (url_hash + ".meta")
    cached_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"dummy")
    meta_file.write_text("image/jpeg", encoding="utf-8")
    try:
        resp = client.get(f"/api/proxy-image?url={raw_url}")
        assert resp.status_code == 200
        # Existing headers stay
        assert resp.headers.get("Cache-Control") == "public, max-age=86400"
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        # New headers added
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" not in resp.headers
    finally:
        cached_file.unlink(missing_ok=True)
        meta_file.unlink(missing_ok=True)





