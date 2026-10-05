"""Tests for the real-time layer: the client's StreamManager and the server's push.

What is pinned here is everything that fails *quietly* in a browser:

  * the reconnect ladder — a wrong step is invisible until a server restarts and
    every tab hammers it at once;
  * the routing table and the price diff — a mistyped event name drops a whole
    channel, and a diff that reports unchanged symbols turns every tick into a
    full DOM write;
  * the calendar release scan — announcing the same figure twice, or flushing a
    week of history on the first pass, is only visible as noise;
  * the "no parallel polling" invariant — the point of the whole exercise.

The browser side of these paths was exercised by hand as well (a killed server:
polling started, reconnect ladder walked, then `live` again with the poll timers
cleared; a forced WebSocket: one failed attempt, immediate step-down to SSE).
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard_logic import extract          # noqa: E402  (shared extractor)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "dashboard_html.py"

UNITS = ["SM_BACKOFF", "SM_CHANNELS", "SM_WIRE", "SM_POLL",
         "smBackoff", "smRouteEvent", "smPriceDiff", "smMergeNews",
         "smAnchorScroll", "smChangeText"]

STUBS = r"""
/* the page's own formatters, reduced to what these units touch */
function toFa(n){ return String(n==null?'':n).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]); }
function esc(s){ return String(s==null?'':s); }
const flash = () => {};
"""

ASSERTS = r"""
const ok = (cond, msg) => { if(!cond){ throw new Error('ASSERT FAILED: ' + msg); } n++; };
let n = 0;

/* ── the reconnect ladder ─────────────────────────────────────────────── */
const ladder = [1,2,3,4,5,6,7,8,9].map(a => smBackoff(a));
/* the base plus at most 25% jitter (capped at 500ms) */
const within = (v, base) => v >= base && v <= base + Math.min(500, base / 4) + 1;
ok(SM_BACKOFF.join(',') === '1000,2000,5000,10000,20000,30000', 'the documented ladder');
ok(within(ladder[0], 1000) && within(ladder[1], 2000) && within(ladder[2], 5000),
   'first steps in seconds: ' + ladder.slice(0,3).join(','));
ok(ladder[0] < ladder[1] && ladder[1] < ladder[2] && ladder[2] < ladder[3], 'the ladder grows');
ok(smBackoff(99) <= 30000 + 500, 'the last step is capped (never unbounded)');
ok(smBackoff(6) >= 30000 && smBackoff(6) <= 30500, 'past the end it stays at the cap');
ok(smBackoff(0) <= 1500 && smBackoff(0) >= 1000, 'attempt 0 behaves like attempt 1');
const spread = new Set([1,2,3,4,5,6,7,8,9,10].map(() => smBackoff(4)));
ok(spread.size > 1, 'jitter: ten clients do not reconnect on the same millisecond');

/* ── routing ──────────────────────────────────────────────────────────── */
ok(smRouteEvent('prices') === 'prices' && smRouteEvent('PRICES') === 'prices', 'case-insensitive');
ok(smRouteEvent('update') === 'news' && smRouteEvent('news') === 'news', 'the feed channel');
ok(smRouteEvent('init') === 'news', 'the initial payload is a news frame');
ok(smRouteEvent('calendar') === 'calendar', 'the release channel');
ok(smRouteEvent('heartbeat') === null && smRouteEvent('') === null && smRouteEvent(null) === null,
   'anything unknown is dropped, not guessed');
ok(SM_CHANNELS.length === 3 && SM_CHANNELS.indexOf('prices') >= 0 && SM_CHANNELS.indexOf('calendar') >= 0,
   'exactly the three promised channels');

/* ── the price diff ───────────────────────────────────────────────────── */
const t1 = {BTC:{price:100, change_24h:1}, XAU:{price:2000, change_24h:-0.5}};
const t2 = {BTC:{price:101, change_24h:1}, XAU:{price:2000, change_24h:-0.5}, WTI:{price:70, change_24h:2}};
const d = smPriceDiff(t1, t2);
ok(d.length === 2, 'only the moved symbols and the new one: ' + JSON.stringify(d.map(x => x.sym)));
ok(d.filter(x => x.sym === 'BTC')[0].moved.join() === 'price', 'the field that moved is named');
ok(d.filter(x => x.sym === 'BTC')[0].dirPrice === 1, 'up is +1');
ok(d.filter(x => x.sym === 'WTI')[0].dirPrice === 0, 'a first sighting is not a direction');
ok(smPriceDiff(t2, t2).length === 0, 'an identical frame costs zero DOM work');
const flip = smPriceDiff({BTC:{price:100, change_24h:1}}, {BTC:{price:100, change_24h:-1}});
ok(flip[0].dir === -1 && flip[0].dirPrice === 0, 'the 24h change turning negative is its own direction');
ok(smPriceDiff(null, t2).length === 3, 'no previous frame: everything is new');
ok(smPriceDiff(t2, {})[0] === undefined, 'an empty frame changes nothing');

/* ── news merge ───────────────────────────────────────────────────────── */
const a = {id:'a', published_ts:100}, b = {id:'b', published_ts:300}, c = {id:'c', published_ts:200};
const m = smMergeNews([a], [b, c, b]);
ok(m.list.map(x => x.id).join() === 'b,c,a', 'newest first, no duplicate from a repeated frame: ' + m.list.map(x => x.id).join());
ok(m.fresh.length === 2 && m.fresh[0].id === 'b', 'only genuinely new items are handed to the DOM');
const dupe = smMergeNews([a, b], [a, b]);
ok(dupe.list.length === 2, 'a replayed frame is idempotent for the list');
ok(dupe.fresh.map(x => x.id).join() === 'a,b',
   'fresh() means new *in this frame* — the DOM layer skips what is already rendered');
ok(smMergeNews([], [a, b], 1).list.length === 1, 'the limit is honoured');
ok(smMergeNews([{id:'x'}, {id:'y'}], []).list.length === 2, 'a news frame without items keeps the list');

/* ── scroll anchoring ─────────────────────────────────────────────────── */
ok(smAnchorScroll(1000, 0, 120) === 1120, 'the anchor moved down 120 → the scroll follows');
ok(smAnchorScroll(1000, 50, 50) === 1000, 'nothing moved → nothing changes');
ok(smAnchorScroll(1000, 120, 0) === 880, 'content that moved up scrolls back up');
ok(smAnchorScroll(10, 0, -400) === 0, 'never negative');
ok(smAnchorScroll(null, null, null) === 0, 'missing measurements are harmless');

/* ── formatting ───────────────────────────────────────────────────────── */
ok(smChangeText(1.234) === '▲1.23%', 'up arrow, two decimals: ' + smChangeText(1.234));
ok(smChangeText(-0.5) === '▼0.50%', 'down arrow');
ok(smChangeText(0) === '▲0.00%', 'flat reads as up, not as an error');

console.log('STREAM ASSERTIONS ' + n);
"""


def _node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not on PATH")
    return node


def test_stream_pure_logic(tmp_path):
    page = SOURCE.read_text(encoding="utf-8", errors="replace")
    harness = "\n".join([STUBS] + [extract(page, u) for u in UNITS] + [ASSERTS])
    path = tmp_path / "stream.js"
    path.write_text(harness, encoding="utf-8")
    proc = subprocess.run([_node(), str(path)], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"{proc.stdout}\n{proc.stderr}"
    m = re.search(r"STREAM ASSERTIONS (\d+)", proc.stdout or "")
    assert m and int(m.group(1)) >= 25, proc.stdout


def test_no_parallel_polling():
    """The whole point: while a stream is alive nothing polls on a timer.

    The old client had `setInterval(pollLive, 15000)` plus a 120s feed net, and
    the server's price cache was only refreshed *because* browsers asked. Those
    two intervals now have to be gated on the stream's state, or the terminal is
    back to double work with a socket open.
    """
    page = SOURCE.read_text(encoding="utf-8")
    assert "setInterval(pollLive, 15000)" not in page, "prices must not poll on their own timer"
    assert page.count("Stream.state!=='live'") >= 2, "the feed timers must stand down while live"
    assert "this.stopPolling();" in page and "startPolling()" in page
    # polling only starts from the failure path
    assert re.search(r"fail\(transport\)\{[\s\S]{0,700}?startPolling\(\)", page), \
        "polling is started by a failed transport, not at boot"


def test_dom_handles_for_micro_updates():
    page = SOURCE.read_text(encoding="utf-8")
    assert 'data-sym="${esc(sym)}"' in page, "ticker chips must expose their symbol"
    assert '<tr data-sym="${esc(sym)}">' in page, "asset rows must expose their symbol"
    assert 'data-key="${esc(e._key||' in page, "calendar rows must be addressable by key"
    for fn in ("smIndexPrices", "smPaintPrices", "smPrependNews", "smPickAnchor", "smScroller", "smFlashEvent"):
        assert f"function {fn}(" in page, f"{fn}() is part of the micro-update layer"
    assert "requestAnimationFrame(run)" in page, "the DOM batch is one frame, not one write per tick"


def test_stream_info_endpoint(monkeypatch):
    sys.path.insert(0, str(ROOT))
    import app as flask_app                      # noqa: E402

    # another suite sets MOHMD_TOKEN in the environment and never clears it;
    # this test reads the route as an ordinary local terminal would
    monkeypatch.setenv("MOHMD_TOKEN", "")
    data = flask_app.app.test_client().get("/api/stream/info").get_json()
    assert data, "the stream info route must answer JSON on a local terminal"
    assert data["ok"] is True
    assert data["sse"] == "/api/stream"
    assert data["channels"] == {"prices": "prices", "news": "update", "calendar": "calendar"}
    assert set(data["poll_seconds"]) == {"prices", "data", "calendar"}, "every fallback cadence is advertised"
    assert data["push_seconds"] >= 5
    # ws is advertised only when a proxy provides one — never a guess
    assert data["ws"] is None or data["ws"].startswith(("ws://", "wss://"))


def test_release_scan_announces_once(monkeypatch):
    sys.path.insert(0, str(ROOT))
    import app as flask_app                      # noqa: E402

    sent = []
    monkeypatch.setattr(flask_app, "_sse_broadcast", lambda ev, data: sent.append((ev, data)))
    now = 1_800_000_000.0
    fresh = {"ts": now - 60, "title": "US CPI (MoM)", "country": "USD", "actual": "0.4%",
             "actual_fmt": "0.4%", "impact": "High", "doc_sections": [{"big": "x"}]}
    old = {"ts": now - 86400, "title": "GDP", "country": "USD", "actual": "2.1%"}
    monkeypatch.setattr(flask_app, "market_context",
                        lambda *a, **k: {"calendar": {"events": [fresh, old]}})
    flask_app._CAL_SEEN.clear()

    first = flask_app.cal_scan_and_broadcast(now)
    assert [e["title"] for e in first] == ["US CPI (MoM)"], "only the release inside the window is announced"
    assert sent and sent[0][0] == "calendar"
    assert "doc_sections" not in sent[0][1], "the explanation payload is not pushed with the figure"
    assert sent[0][1]["key"].startswith(str(int(fresh["ts"]))), "the frame carries the row key"

    sent.clear()
    assert flask_app.cal_scan_and_broadcast(now) == [], "a release is announced once, not every scan"
    assert sent == []

    # a revision of the same release is news again
    fresh["actual"] = "0.5%"
    again = flask_app.cal_scan_and_broadcast(now)
    assert len(again) == 1 and again[0]["actual"] == "0.5%", "a revised figure is a new announcement"


def test_push_loop_costs_nothing_when_idle(monkeypatch):
    """No attached client must mean no upstream quote fetch: the APIs are free
    and rate-limited, and an idle terminal may not spend them."""
    sys.path.insert(0, str(ROOT))
    import app as flask_app                      # noqa: E402

    called = []
    monkeypatch.setattr(flask_app, "live_prices", lambda: called.append(1) or {})
    monkeypatch.setattr(flask_app, "_sse_subscribers", {})
    assert flask_app.stream_push_once(1_800_000_000.0) == 0
    assert not called, "live_prices() must not run with nobody attached"

    monkeypatch.setattr(flask_app, "_sse_subscribers", {"1": None})
    assert flask_app.stream_push_once(1_800_000_000.0) == 1
    assert called == [1], "with a client attached the tick refreshes once"
