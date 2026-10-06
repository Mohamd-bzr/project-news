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

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "dashboard_html.py"


def test_on_demand_audio_reader():
    content = SOURCE.read_text(encoding="utf-8")
    # Topbar squawk box must be removed per user specification
    assert 'id="squawkBox"' not in content
    assert 'id="squawkToggleBtn"' not in content
    assert 'id="squawkPopover"' not in content

    # Audio reader removed per user specification
    assert 'window.NewsAudio = NewsAudio' not in content
    assert 'id="btnAudioModal"' not in content
    assert 'id="btnAudioReport"' not in content


def test_whale_liquidity_tracker_components():
    content = SOURCE.read_text(encoding="utf-8")
    # Sidebar nav and view panel
    assert 'id="nav-whales"' in content
    assert 'id="view-whales"' in content
    assert 'id="whaleHero"' in content
    assert 'id="wkpiBtc"' in content
    assert 'id="wkpiEth"' in content
    assert 'id="wkpiStable"' in content
    assert 'id="whaleTB"' in content
    assert 'id="whaleTableBody"' in content
    assert 'id="whaleCount"' in content
    # JS controller
    assert 'class WhaleTracker' in content
    assert 'window.whaleTracker = new WhaleTracker()' in content
    assert 'setFilter' in content
    # the fabricated-data machinery must stay gone: no seeds, no random ticks
    assert 'generateTick' not in content
    assert 'initSeedData' not in content
    assert 'whale-tick-35s' not in content


def test_workspace_removed():
    content = SOURCE.read_text(encoding="utf-8")
    # Workspace markup and JS must be completely removed per user specification
    assert 'id="btnWorkspaceToggle"' not in content
    assert 'id="wsContainer"' not in content
    assert 'id="wsPresetSelect"' not in content
    assert 'id="wsGrid"' not in content
    assert 'class WorkspaceManager' not in content
    assert 'window.workspaceManager' not in content
    assert 'toggleWorkspaceMode' not in content


def test_top_news_slider_headline_only():
    content = SOURCE.read_text(encoding="utf-8")
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

    content = SOURCE.read_text(encoding="utf-8")
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
