"""
Test suite verifying the three newly integrated institutional features in dashboard_html.py:
1. Modular Docking Workspace (Prompt 4)
2. Whale Liquidity Tracker (Prompt 6)
3. Financial Squawk Box (Prompt 9)
"""
import pytest
from pathlib import Path
import re
import subprocess
import shutil
import tempfile

def _page():
    """The page as served — assembled from web/fragments/.

    It used to be a raw string inside dashboard_html.py, which is a thin loader
    now, so the text has to come from the module rather than off the file.
    """
    from dashboard_html import APP_HTML
    return APP_HTML


def test_on_demand_audio_reader():
    content = _page()
    # Topbar squawk box must be removed per user specification
    assert 'id="squawkBox"' not in content
    assert 'id="squawkToggleBtn"' not in content
    assert 'id="squawkPopover"' not in content

    # Audio reader removed per user specification
    assert 'window.NewsAudio = NewsAudio' not in content
    assert 'id="btnAudioModal"' not in content
    assert 'id="btnAudioReport"' not in content


def test_whale_tracker_is_fully_removed():
    """Removed per operator request (2026-10-06): nav, view, controller,
    endpoint and icon must all be gone from the shipped page."""
    content = _page()
    for gone in ('id="nav-whales"', 'id="view-whales"', 'class WhaleTracker',
                 'whaleTracker', 'i-whale', '/api/whales/live'):
        assert gone not in content, f"{gone} should be removed"


def test_workspace_removed():
    content = _page()
    # Workspace markup and JS must be completely removed per user specification
    assert 'id="btnWorkspaceToggle"' not in content
    assert 'id="wsContainer"' not in content
    assert 'id="wsPresetSelect"' not in content
    assert 'id="wsGrid"' not in content
    assert 'class WorkspaceManager' not in content
    assert 'window.workspaceManager' not in content
    assert 'toggleWorkspaceMode' not in content


def test_top_news_slider_headline_only():
    content = _page()
    # Lead/slider cards must have title and rail, but no description/summary block
    assert 'function leadCardHTML' in content
    assert '<div class="lead-ttl">' in content
    # Ensure leadCardHTML does not render summary
    match = re.search(r'function leadCardHTML\(a\)\{.*?\n\}', content, re.DOTALL)
    assert match is not None
    lead_func = match.group(0)
    assert 'class="summ"' not in lead_func


def test_all_inline_js_blocks_syntax():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js not available on system")

    content = _page()
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", content, re.DOTALL)
    assert len(blocks) >= 6

    with tempfile.TemporaryDirectory() as tmp:
        for idx, block in enumerate(blocks, 1):
            if not block.strip():
                continue
            path = Path(tmp) / f"block{idx}.js"
            path.write_text(block, encoding="utf-8")
            proc = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
            assert proc.returncode == 0, f"Inline script block #{idx} failed syntax check:\n{proc.stderr}"


def test_no_test_leaves_the_shared_secret_behind():
    """test_core.py sets MOHMD_TOKEN for the admin-key checks; if it is not put
    back, every later test in the session silently runs behind the token gate
    (which is why test_stream_manager.py had to monkeypatch it away by hand).
    This file sorts after test_core.py, so it sees the aftermath.
    """
    import os
    assert not os.environ.get("MOHMD_TOKEN"), \
        "MOHMD_TOKEN leaked: later tests are running behind the shared-secret gate"
