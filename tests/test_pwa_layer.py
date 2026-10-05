"""Tests for the offline-first layer: service worker, manifest, icons, engine.

The browser is where this layer proves itself — and it did: with Flask stopped,
the page still boots from the worker's shell, the feed comes back from the
IndexedDB cache, a report drawer opens from its stored copy, the calendar
renders from the cached economic payload, and a query the live window cannot
answer is served from the full-text index.

A browser cannot be part of `pytest`, so what is pinned down here is the part
that would otherwise fail *silently*:

  * the engine's pure logic (tokenizing, weighting, ranking, filters) — a lost
    Persian fold or a wrong boost shows up as "search returns plausible junk",
    which no screenshot ever catches;
  * the manifest and the icons it promises, including their real pixel sizes;
  * the routes and the headers the browser needs to accept a worker at all;
  * the wiring in the page — one manifest link, one engine tag, the fetch
    interceptor installed before the app's first request.
"""
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "dashboard_html.py"
WEB = ROOT / "web"
ENGINE = WEB / "storage_engine.js"
SW = WEB / "sw.js"
MANIFEST = WEB / "manifest.webmanifest"
ICONS = WEB / "icons"


def _node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not on PATH")
    return node


# ── the storage engine's pure logic ─────────────────────────────────────────

HARNESS = r"""
const SE = require(process.argv[2]);
const assert = require('assert');
let n = 0;
const ok = (cond, msg) => { assert.ok(cond, msg); n++; };

/* ── tokenizer ─────────────────────────────────────────────────────────── */
const t = SE.seTok('Crude oil Rises! crude; THE Iran–Hormuz strait');
ok(t.join(' ') === 'crude oil rises iran hormuz strait', 'basic tokens, dedup, stopwords: ' + t.join(' '));
ok(SE.seTok('').length === 0 && SE.seTok(null).length === 0, 'empty input yields no tokens');
ok(SE.seTok('بانك مركزي').join(' ') === 'بانک مرکزی', 'Persian kaf/yeh folding: ' + SE.seTok('بانك مركزي').join(' '));
ok(SE.seTok('نفتِ خام').indexOf('نفت') >= 0, 'harakat are stripped');
ok(SE.seTok('Crudé').join(' ') === 'crude', 'latin diacritics folded');
ok(SE.seTok('a 1 22').join(' ') === '22', 'single characters are noise, two digits survive');

/* ── time + list coercion ──────────────────────────────────────────────── */
ok(SE.seTs(1790591715) === 1790591715000, 'epoch seconds → ms');
ok(SE.seTs(1790591715000) === 1790591715000, 'epoch ms stays ms');
ok(Math.abs(SE.seTs('2026-09-28T01:30:00Z') - Date.parse('2026-09-28T01:30:00Z')) === 0, 'ISO parses');
ok(Number.isFinite(SE.seTs(undefined)), 'missing time falls back to now, never NaN');
ok(SE.seArr('BTC, WTI/XAU').join('|') === 'BTC|WTI|XAU', 'string asset list splits');
ok(SE.seArr(['BTC', '', null]).join('|') === 'BTC', 'array asset list filters empties');
ok(SE.seArr(null).length === 0, 'null assets → []');

/* ── document terms ────────────────────────────────────────────────────── */
const d = SE.seDoc({id: 7, title: 'Hormuz tanker risk lifts oil', assets: ['WTI'], topic: 'macro',
                    source: 'Reuters', summary: 'Insurance costs rise', published_ts: 1790591715});
ok(d.rec.id === '7', 'id is stringified');
ok(d.rec.ts === 1790591715000, 'record carries ms timestamp');
ok(d.terms['hormuz'] >= SE.SE_FIELD_W.title, 'headline token weighted at the title boost');
ok(d.terms['wti'] >= SE.SE_FIELD_W.assets, 'asset tag weighted');
ok(d.terms['insurance'] === SE.SE_FIELD_W.summary, 'summary token weighted below the title');
ok(d.terms['oil'] === d.terms['hormuz'], 'a word in the headline is weighted once per field');
ok(d.terms['tanker'] > d.terms['insurance'], 'headline token outweighs a summary-only token');
const d2 = SE.seDoc({link: 'https://x/y', title: 'No id here'});
ok(d2.rec.id === 'https://x/y', 'a missing id falls back to the link');

/* ── search: AND, ranking, filters ─────────────────────────────────────── */
const post = (id, w, ts, topic, assets) => [id, w, ts, topic, assets];
const now = 1790591715000;
const parts = [
  {term: 'hormuz', exact: true, df: 2,
   postings: [post('a', 9, now - 3600e3, 'security', ['WTI']), post('b', 4, now - 90 * 3600e3, 'security', [])]},
  {term: 'oil', exact: true, df: 3,
   postings: [post('a', 5, now - 3600e3, 'security', ['WTI']), post('c', 5, now - 3600e3, 'macro', ['BTC'])]}
];
const all = SE.seSearch(parts, 'hormuz oil', {limit: 10, totalDocs: 1000, now: now});
ok(all.hits.length === 1 && all.hits[0].id === 'a', 'AND semantics: only the doc matching both terms');
ok(all.hits[0].coverage === 1, 'full coverage reported');
ok(all.relaxed === false, 'strict pass is not marked relaxed');

const loose = SE.seSearch(parts, 'hormuz oil', {limit: 10, totalDocs: 1000, now: now, any: true});
ok(loose.hits.length === 3, 'OR mode returns every candidate');
ok(loose.hits[0].id === 'a', 'the two-term hit still ranks first');
ok(loose.relaxed === true, 'relaxed flag set');

const fresh = SE.seSearch([
  {term: 'opec', exact: true, df: 2, postings: [post('new', 3, now - 600e3, 'macro', []),
                                                post('old', 30, now - 200 * 3600e3, 'macro', [])]}
], 'opec', {limit: 5, totalDocs: 1000, now: now});
ok(fresh.hits[0].id === 'new', 'recency beats a higher term frequency from three days ago');

/* two spellings of one token: the exact one must lead. OR mode on purpose — a
   strict AND over two identical terms can never match anything */
const exact = SE.seSearch([
  {term: 'cpi', exact: true, df: 5, postings: [post('x', 5, now, '', [])]},
  {term: 'cpi', exact: false, df: 5, postings: [post('y', 5, now, '', [])]}
], 'cpi', {limit: 5, totalDocs: 100, now: now, any: true});
ok(exact.hits.length === 2 && exact.hits[0].id === 'x',
   'an exact term outranks a prefix expansion of the same weight');

const filt = SE.seSearch(parts, 'hormuz oil', {limit: 5, totalDocs: 100, now: now, any: true,
                                               asset: 'BTC', topic: 'macro'});
ok(filt.hits.length === 1 && filt.hits[0].id === 'c' && filt.hits[0].assets[0] === 'BTC',
   'asset and topic filters apply to the ranked hits');
const since = SE.seSearch(parts, 'hormuz oil', {limit: 5, totalDocs: 100, now: now, any: true,
                                                since: now - 24 * 3600e3});
ok(since.hits.length === 2 && since.hits.every(h => h.ts >= now - 24 * 3600e3), 'time window filter');

const empty = SE.seSearch([], 'nothing', {});
ok(empty.hits.length === 0 && empty.terms === 0 && empty.took >= 0, 'no postings → empty result, still shaped');
const none = SE.seSearch([{term: 'x', postings: []}], 'x', {});
ok(none.hits.length === 0, 'a term with no postings is not a crash');

const cap = SE.seSearch([{term: 'q', exact: true, df: 1,
  postings: Array.from({length: 40}, (_, i) => post('d' + i, 1, now, '', []))}], 'q',
  {limit: 7, totalDocs: 40, now: now});
ok(cap.hits.length === 7 && cap.total === 40, 'limit caps the returned page, total keeps the real count');

/* ── schema ────────────────────────────────────────────────────────────── */
ok(SE.SE_DB_NAME === 'MohmdNewsDB', 'database name is the documented one');
ok(Object.keys(SE.SE_STORES).sort().join(',') === 'articles,bookmarks,calendar,meta,reports,terms',
   'the five object stores plus meta: ' + Object.keys(SE.SE_STORES).join(','));
const aIdx = SE.SE_STORES.articles.indexes.map(i => i[0]).sort().join(',');
ok(aIdx === 'assets,topic,ts', 'articles indexed by timestamp, topic and asset: ' + aIdx);
ok(SE.SE_STORES.articles.indexes.filter(i => i[0] === 'assets')[0][2].multiEntry === true,
   'the asset index is multiEntry (an article carries several assets)');
ok(SE.SE_STORES.bookmarks.keyPath === 'id' && SE.SE_STORES.reports.keyPath === 'sym',
   'bookmarks keyed by id, reports by symbol');
ok(SE.SE_STORES.terms.keyPath === 'term', 'inverted index keyed by term');

/* the class must not touch IndexedDB until open() — node has none */
const eng = new SE.StorageEngine();
ok(eng.name === 'MohmdNewsDB' && eng._db === null, 'constructing an engine does not open a database');
eng.open().then(() => { console.log('unexpected resolve'); }, err => {
  assert.ok(/IndexedDB/.test(String(err)), 'open() rejects with a clear message: ' + err);
});
console.log('ASSERTIONS ' + n);
"""


def test_storage_engine_logic(tmp_path):
    node = _node()
    script = tmp_path / "harness.js"
    script.write_text(HARNESS, encoding="utf-8")
    proc = subprocess.run([node, str(script), str(ENGINE)],
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, f"node harness failed:\n{proc.stdout}\n{proc.stderr}"
    m = re.search(r"ASSERTIONS (\d+)", proc.stdout or "")
    assert m, proc.stdout
    assert int(m.group(1)) >= 30, "expected the full assertion set to run"


def test_service_worker_contract():
    src = SW.read_text(encoding="utf-8")
    assert "'/'" in src and "/manifest.webmanifest" in src, "shell precache list"
    assert "skipWaiting" in src and "clients.claim" in src, "update + takeover"
    assert "/api/stream" in src and "return;" in src, "SSE must be left alone"
    # a synthetic 504 would resolve the page's fetch with an unusable body and
    # the page's own cache layer would never run
    assert "status: 504,\n      headers: { 'Content-Type': 'application/json'" not in src
    assert "throw new Error('offline" in src, "a cache miss must fail like a dead network"
    assert "SW_VERSION" in src, "cache names are versioned"
    assert "Service-Worker-Allowed" not in src  # the header belongs to the route


def test_manifest_matches_the_icons_on_disk():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert man["display"] == "standalone", "terminal mode"
    assert man["start_url"] == "/" and man["scope"] == "/", "the whole app is in scope"
    assert man["theme_color"].startswith("#") and man["background_color"].startswith("#")
    assert man["lang"] == "fa" and man["dir"] == "rtl", "Persian RTL terminal"
    assert any(i.get("purpose") == "maskable" for i in man["icons"]), "a maskable icon exists"

    for icon in man["icons"]:
        path = ICONS / Path(icon["src"]).name
        assert path.is_file(), f"{icon['src']} declared in the manifest but missing on disk"
        blob = path.read_bytes()
        assert blob[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
        w, h = struct.unpack(">II", blob[16:24])
        assert f"{w}x{h}" == icon["sizes"], f"{path.name} is {w}×{h}, manifest says {icon['sizes']}"


def test_icons_are_reproducible():
    """The icons are generated code, not binary blobs: `--check` must pass."""
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "make_icons.py"), "--check"],
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_routes_serve_the_offline_layer():
    sys.path.insert(0, str(ROOT))
    import app as flask_app                      # noqa: E402  (needs BASE_DIR set)

    client = flask_app.app.test_client()

    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["Content-Type"]
    assert r.headers.get("Service-Worker-Allowed") == "/", "scope must cover the app"
    assert "no-cache" in r.headers.get("Cache-Control", ""), "a cached worker never updates"

    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200 and r.headers["Content-Type"].startswith("application/manifest+json")
    json.loads(r.get_data(as_text=True))

    r = client.get("/storage-engine.js")
    assert r.status_code == 200 and "javascript" in r.headers["Content-Type"]

    r = client.get("/icons/icon-192.png")
    assert r.status_code == 200 and r.headers["Content-Type"] == "image/png"
    assert "max-age" in r.headers.get("Cache-Control", ""), "icons are immutable"

    for bad in ("app.py", "../app.py", "..%2fapp.py", "nope.png"):
        assert client.get(f"/icons/{bad}").status_code == 404, f"{bad} must not be servable"


def test_head_assets_are_actually_served():
    """Whatever the `<head>` points at has to resolve on this server.

    Written against the markup rather than against fixed paths on purpose: the
    head is shared ground (another thread branded it for its own manifest), and
    a link the browser cannot fetch fails *silently* — the icon is simply
    missing and the "install" prompt never appears.
    """
    page = SOURCE.read_text(encoding="utf-8")
    head = page[page.index("<head>"):page.index("</head>")]
    urls = re.findall(r'<link[^>]+href="(/[^"]+)"', head)
    assert urls, "no local <link> assets in the head at all"
    manifests = [u for u in urls if u.endswith(".json") or "manifest" in u]
    assert len(manifests) == 1, f"exactly one web app manifest, found {manifests}"

    sys.path.insert(0, str(ROOT))
    import app as flask_app                      # noqa: E402
    client = flask_app.app.test_client()
    for url in urls:
        r = client.get(url)
        assert r.status_code == 200, f"head links {url} but the server answers {r.status_code}"
    man = json.loads(client.get(manifests[0]).get_data(as_text=True))
    assert man["display"] == "standalone"
    for icon in man.get("icons", []):
        assert client.get(icon["src"]).status_code == 200, f"manifest icon {icon['src']} is not served"


def test_page_wires_the_layer_once():
    page = SOURCE.read_text(encoding="utf-8")
    for needle, count in [
        ('<script src="/storage-engine.js"></script>', 1),
        ('id="pwaItem"', 1),
        ('id="pwaTxt"', 1),
        ('window.MohmdCache=', 1),
        ("new StorageEngine()", 1),
        ("navigator.serviceWorker.register('/sw.js'", 1),
    ]:
        assert page.count(needle) == count, f"expected exactly {count}× {needle}"
    assert "if(window.__MAQUETTE__){" in page, "the offline demo file must stand down"
    # the interceptor is installed at parse time, the app hooks after the app's
    # own scripts have run — getting this order wrong is invisible until offline
    assert page.index("wireFetch();") < page.index("if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot);")
    assert page.index('<script src="/storage-engine.js"></script>') < page.index("wireFetch();")


def test_maquette_inlines_the_engine():
    """The demo file is one deliverable file: it must not be left pointing at a
    URL that only exists behind Flask (it is opened from a desktop sometimes).

    Built as a source check rather than a run, because a real build waits for a
    live scrape cycle — minutes, and it needs the network.
    """
    src = (ROOT / "tools" / "make_maquette.py").read_text(encoding="utf-8")
    assert '"/storage-engine.js"' in src and "storage_engine.js" in src
    assert "storage_engine.js is missing" in src, "a missing engine must fail the build"
    assert "engine_tag," in src and "html = html.replace(" in src, \
        "the tag has to be replaced by the file's contents"
    page = SOURCE.read_text(encoding="utf-8")
    assert page.count('<script src="/storage-engine.js"></script>') == 1
    # and the runtime stand-down that keeps the demo from writing a database
    assert "if(window.__MAQUETTE__){" in page
