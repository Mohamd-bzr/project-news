"""Regression tests for the bugs in BUG_REPORT_DEEP_2026-09-29.md.

One test per finding that was actually fixed, so the behaviour cannot drift back
silently. Findings that were deliberately left alone (see the report's notes)
are not tested here.
"""
import json
import pathlib
import time
from datetime import datetime, timedelta, timezone

import pytest

import app as A
from billing import _is_expired
from calendar_data import LOWER_IS_BETTER, _entry
from news_intelligence import CorrelationTracker, Deduplicator


# ── C1 · an article is never a duplicate of itself ─────────────────────────

def test_deduplicator_does_not_match_an_article_with_itself():
    d = Deduplicator()
    art = {'id': '1', 'title': 'Gold slumps as real yields rise',
           'summary': 'Real yields rose and the dollar strengthened.'}
    assert d.is_duplicate(art) == (False, None)
    # the second pass is the one that used to be "duplicate of itself"
    assert d.is_duplicate(art) == (False, None)
    assert d.is_duplicate(art) == (False, None)


def test_deduplicator_still_catches_a_real_duplicate():
    d = Deduplicator()
    text = {'title': 'Gold slumps as real yields rise',
            'summary': 'Real yields rose and the dollar strengthened.'}
    d.is_duplicate({'id': 'a', **text})
    is_dup, of = d.is_duplicate({'id': 'b', **text})
    assert is_dup is True and of == 'a'
    assert d.is_duplicate({'id': 'c', 'title': 'Bitcoin ETF inflows hit a record',
                           'summary': 'Funds saw record creations.'}) == (False, None)


def test_deduplicator_fallback_id_is_stable_across_processes():
    d = Deduplicator()
    d.is_duplicate({'title': 'A headline with no id'})
    stored = d._articles[0][2]
    assert stored and stored.isalnum() and not stored.startswith('-')
    assert stored != str(hash('a headline with no id'))


# ── H1 · one correlation event per (article, asset) ────────────────────────

def _blank_tracker(tmp_path):
    """A tracker with no history: the live store must not leak into the test."""
    tracker = CorrelationTracker()
    tracker.DB_PATH = tmp_path / "corr.json"          # never touch the live store
    tracker._events = []
    tracker._seen = {}
    return tracker


def test_correlation_records_each_article_once_per_asset(tmp_path):
    tracker = _blank_tracker(tmp_path)
    for _ in range(25):                               # 25 price pushes, one article
        tracker.record_event('BTC', 0.4, 80000.0, article_id='a1')
        tracker.record_event('ETH', 0.4, 2600.0, article_id='a1')
    assert len(tracker._events) == 2
    assert {e['symbol'] for e in tracker._events} == {'BTC', 'ETH'}
    assert all(e['article_id'] == 'a1' for e in tracker._events)


def test_correlation_has_no_lockstep_requirement_without_an_id(tmp_path):
    """A caller with no article id keeps the old behaviour (recorded as asked)."""
    tracker = _blank_tracker(tmp_path)
    tracker.record_event('BTC', 0.1, 80000.0)
    tracker.record_event('BTC', 0.1, 80000.0)
    assert len(tracker._events) == 2


# ── H2 · the configured news window drives /api/data and /api/fng ──────────

@pytest.fixture()
def client():
    A.app.config['TESTING'] = True
    return A.app.test_client()


def test_api_data_honours_the_configured_window(client):
    now = time.time()
    saved_arts, saved_win = A.STATE['articles'], A.CONFIG.get('report_max_age_hours')
    A.STATE['articles'] = [
        {'id': 'fresh', 'title': 'f', 'link': 'http://f', 'assets': ['BTC'],
         'published_ts': now - 3600, 'credibility': 0.8},
        {'id': 'day3', 'title': 'd', 'link': 'http://d', 'assets': ['BTC'],
         'published_ts': now - 60 * 3600, 'credibility': 0.8},
    ]
    try:
        A.CONFIG['report_max_age_hours'] = 72
        wide = client.get('/api/data').get_json()
        A.CONFIG['report_max_age_hours'] = 24
        narrow = client.get('/api/data').get_json()
    finally:
        A.STATE['articles'] = saved_arts
        A.CONFIG['report_max_age_hours'] = saved_win

    assert sorted(a['id'] for a in wide['articles']) == ['day3', 'fresh']
    assert wide['archive'] == []
    assert [a['id'] for a in narrow['articles']] == ['fresh']
    assert [a['id'] for a in narrow['archive']] == ['day3']


def test_fng_uses_the_same_window(client):
    now = time.time()
    saved_arts, saved_win = A.STATE['articles'], A.CONFIG.get('report_max_age_hours')
    A.STATE['articles'] = [
        {'id': 'fresh', 'title': 'f', 'link': 'http://f', 'assets': ['XAU'],
         'published_ts': now - 3600, 'credibility': 0.8, 'sentiment_score': 0.5},
        {'id': 'old', 'title': 'o', 'link': 'http://o', 'assets': ['XAU'],
         'published_ts': now - 60 * 3600, 'credibility': 0.8, 'sentiment_score': 0.5},
    ]
    A.FNG_SYM_CACHE.pop('XAU', None)
    try:
        A.CONFIG['report_max_age_hours'] = 24
        narrow = client.get('/api/fng/XAU').get_json()
        A.FNG_SYM_CACHE.pop('XAU', None)
        A.CONFIG['report_max_age_hours'] = 72
        wide = client.get('/api/fng/XAU').get_json()
    finally:
        A.STATE['articles'] = saved_arts
        A.CONFIG['report_max_age_hours'] = saved_win
        A.FNG_SYM_CACHE.pop('XAU', None)

    assert narrow['count'] == 1
    assert wide['count'] == 2


# ── H3 · one honest "news cited" number ───────────────────────────────────

def test_report_news_used_counts_articles_not_blocks():
    from report_generator import build_report, count_cited_news
    now = datetime.now(timezone.utc)
    ts = time.time()
    arts = [{'id': f'n{i}', 'title': f'Gold headline {i}', 'title_fa': f'طلا {i}',
             'summary': 'Real yields rose and the dollar firmed.',
             'summary_fa': 'بازده بالا رفت.', 'source_name': 'Reuters',
             'link': f'https://e.com/{i}', 'assets': ['XAU'],
             'credibility': 0.9 - i * 0.05, 'published_ts': ts - i * 600,
             'age_hours': i * 0.17, 'topic': 'macro'} for i in range(6)]
    md = {'price': 4174.0, 'change_24h': 0.14, 'closes': [4000 + i for i in range(260)],
          'volumes': [1000 + i for i in range(260)]}
    rep = build_report('XAU', md, arts, now, name='Gold', fa_name='طلا', max_age=24)
    meta = [v for k, v in rep['sections'] if k == 'meta'][0]
    blocks = sum(1 for k, _ in rep['sections'] if k == 'cites')
    assert rep['news_used'] == count_cited_news(rep['sections']) == meta['news_used']
    assert rep['news_used'] != blocks            # the old, block-counting answer


# ── C3 · the free Pro key is a loopback privilege ──────────────────────────

def test_upgrade_is_self_service_on_loopback_only(client):
    local = client.post('/api/billing/upgrade', json={'email': 'local@example.com'})
    assert local.status_code == 200 and local.get_json()['tier'] == 'pro'

    remote = client.post('/api/billing/upgrade', json={'email': 'remote@example.com'},
                         environ_base={'REMOTE_ADDR': '203.0.113.9'})
    assert remote.status_code == 403
    assert remote.get_json()['error'] == 'payment required'
    assert 'api_key' not in remote.get_json()


# ── M3 · the settings window survives the restart ──────────────────────────

def test_settings_clamps_the_window_to_what_load_config_keeps(client, tmp_path, monkeypatch):
    # /api/settings persists through save_config(). Point it at a scratch file:
    # a test must never rewrite the live settings.json.
    monkeypatch.setattr(A, 'CONFIG_FILE', tmp_path / "settings.json")
    saved = A.CONFIG.get('report_max_age_hours')
    try:
        client.post('/api/settings', json={'report_max_age_hours': 720})
        assert A.CONFIG['report_max_age_hours'] == A.NEWS_WINDOW_MAX_HOURS
        client.post('/api/settings', json={'report_max_age_hours': 1})
        assert A.CONFIG['report_max_age_hours'] == A.NEWS_WINDOW_MIN_HOURS
    finally:
        A.CONFIG['report_max_age_hours'] = saved


# ── M4 · no invented indicator for an unknown symbol ───────────────────────

def test_indicators_do_not_answer_with_a_letter(client):
    key = A._default_key
    r = client.get('/api/v1/indicators/ZZZZ-USD', headers={'X-API-Key': key})
    assert r.status_code == 404
    assert r.get_json()['error'] == 'no data'


# ── M5 · the calendar endpoint returns events, and honours ?days ───────────

def test_calendar_endpoint_returns_the_event_list(client):
    r = client.get('/api/v1/calendar?days=7', headers={'X-API-Key': A._default_key})
    body = r.get_json()
    assert r.status_code == 200 and body['ok'] is True
    assert isinstance(body['calendar'], list)
    assert body['days'] == 7 and body['count'] == len(body['calendar'])
    for ev in body['calendar']:
        assert 'events' not in ev                 # not the week bundle again


# ── M6 · symbols and assets are a union ────────────────────────────────────

def test_article_asset_filter_unions_symbols_and_assets(client):
    """A record carrying BOTH keys must answer to either of them."""
    saved = A.STATE['articles']
    A.STATE['articles'] = [{'id': 'both', 'title': 't', 'link': 'http://x',
                            'symbols': ['BTC'], 'assets': ['ETH'],
                            'published_ts': time.time(), 'credibility': 0.8}]
    try:
        hdr = {'X-API-Key': A._default_key}
        for sym in ('BTC', 'ETH'):
            body = client.get(f'/api/v1/articles?symbol={sym}', headers=hdr).get_json()
            assert body['total'] == 1, f'{sym} was dropped by `symbols or assets`'
            assert set(body['articles'][0]['symbols']) == {'BTC', 'ETH'}
    finally:
        A.STATE['articles'] = saved


# ── M7 · an expiry stored as TEXT does not raise ───────────────────────────

def test_is_expired_handles_every_shape_we_store():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    assert _is_expired(past.strftime('%Y-%m-%d %H:%M:%S')) is True
    assert _is_expired(future.strftime('%Y-%m-%d %H:%M:%S')) is False
    assert _is_expired(future.isoformat()) is False
    assert _is_expired(time.time() - 60) is True
    assert _is_expired(str(time.time() + 60)) is False
    assert _is_expired(None) is False and _is_expired('') is False
    assert _is_expired('not-a-date') is False      # never downgrade a payer


# ── M8 / M9 · the calendar's own honesty ───────────────────────────────────

def _ev(title, ts, forecast='1', previous='1', actual=''):
    return _entry(title, 'USD', 'US', 'High', ts, forecast, previous, actual, '',
                  'High impact', 'https://example.com/calendar')


def test_a_past_event_without_a_number_is_not_released():
    past = time.time() - 3600
    ev = _ev('Fed Chair Speech', past)
    assert ev['past'] is True
    assert ev['released'] is False                 # nothing was published
    numbered = _ev('US CPI YoY', past, forecast='0.3', previous='0.3', actual='0.5')
    assert numbered['released'] is True


def test_a_hot_cpi_is_not_tinted_like_a_falling_unemployment_print():
    assert not LOWER_IS_BETTER.search('us cpi yoy')
    cpi = _ev('US CPI YoY', time.time(), forecast='0.3', previous='0.2', actual='0.5')
    assert cpi['surprise'] > 0 and cpi['better'] == 1     # hot print = green
    claims = _ev('US Initial Jobless Claims', time.time(), forecast='220',
                 previous='215', actual='205')
    assert LOWER_IS_BETTER.search('us initial jobless claims') is not None
    assert claims['surprise'] < 0 and claims['better'] == 1


# ── M10 · settings.json is written atomically ──────────────────────────────

def test_save_config_replaces_the_file_in_one_step(tmp_path, monkeypatch):
    target = tmp_path / "settings.json"
    monkeypatch.setattr(A, "CONFIG_FILE", target)
    A.save_config()
    assert json.loads(target.read_text(encoding='utf-8')) == A.CONFIG
    assert not list(pathlib.Path(tmp_path).glob("*.tmp"))


# ── M12 · candle cache: the declared TTL is actually applied ───────────────

def test_candle_cache_expires_and_stays_bounded():
    A.CANDLES_CACHE.clear()
    A._candles_store('X_1D', [{'time': 1, 'close': 2}])
    assert A._candles_cached('X_1D') == [{'time': 1, 'close': 2}]

    A.CANDLES_CACHE['X_1D']['ts'] = time.time() - (A.CANDLE_TTL + 5)
    assert A._candles_cached('X_1D') is None       # stale series never served
    assert 'X_1D' not in A.CANDLES_CACHE

    for i in range(A._CANDLES_MAX + 25):
        A._candles_store(f'S{i}_1D', [{'time': i}])
    assert len(A.CANDLES_CACHE) <= A._CANDLES_MAX
    A.CANDLES_CACHE.clear()

    # an entry written without a timestamp (tests, older code) counts as fresh
    A.CANDLES_CACHE['BTC_1D'] = {'data': [{'time': 1}]}
    assert A._candles_cached('BTC_1D') == [{'time': 1}]
    A.CANDLES_CACHE.clear()


# ── H5 · one manifest, one icon set, one truth ────────────────────────────

def test_there_is_exactly_one_manifest(client):
    root = pathlib.Path(__file__).resolve().parent.parent
    assert (root / "web" / "manifest.webmanifest").is_file()
    assert not (root / "manifest.json").exists()
    assert not (root / "static" / "icons").exists()

    man = client.get('/manifest.webmanifest')
    assert man.status_code == 200
    body = man.get_json()
    assert body['name'].startswith('MOHMD NEWS') and body['lang'] == 'fa'
    for icon in body['icons']:
        assert client.get(icon['src']).status_code == 200, icon['src']

    legacy = client.get('/manifest.json')          # old bookmark/installed app
    assert legacy.status_code == 301
    assert legacy.headers['Location'].endswith('/manifest.webmanifest')


def test_the_page_registers_one_worker_and_links_the_real_manifest():
    from dashboard_html import APP_HTML      # the page lives in web/fragments/ now
    page = APP_HTML
    assert page.count("serviceWorker.register('/sw.js'") == 1
    assert "serviceWorker.register('/static/sw.js')" not in page
    assert '<link rel="manifest" href="/manifest.webmanifest">' in page
    assert '/static/icons/' not in page


# ── M2 · the open token-gate paths are said out loud ──────────────────────

def test_health_reports_the_token_gate_state(client, monkeypatch):
    monkeypatch.delenv('MOHMD_TOKEN', raising=False)
    monkeypatch.setattr(A, '_MOHMD_TOKEN', '')
    off = client.get('/api/health').get_json()['token_gate']
    assert off['armed'] is False and off['open_without_token'] == []

    monkeypatch.setattr(A, '_MOHMD_TOKEN', 'a-shared-secret')
    on = client.get('/api/health', headers={'X-Auth-Token': 'a-shared-secret'})
    gate = on.get_json()['token_gate']
    assert gate['armed'] is True
    assert '/api/candles/' in gate['open_without_token']
    assert '/api/v1/' in gate['self_authenticating']
    assert not set(gate['open_without_token']) & set(gate['self_authenticating'])

    # token-guard rejects wrong token of the exact same length
    wrong = client.get('/', headers={'X-Auth-Token': 'b-shared-secret'})
    assert wrong.status_code == 401
    correct = client.get('/', headers={'X-Auth-Token': 'a-shared-secret'})
    assert correct.status_code == 200


# ── low 1/2/7/9 · the small ones ───────────────────────────────────────────

def test_source_history_is_a_list_in_both_producers():
    hist = A.STATE['src_hist'].setdefault('__probe__', [])
    hist.append(1)
    del hist[:-30]                                  # a deque raised TypeError here
    A.STATE['src_hist'].pop('__probe__', None)


def test_ser_article_survives_a_malformed_record():
    out = A._ser_article({'summary': 'only a summary'})
    assert out['id'] == '' and out['title'] == '' and out['link'] == ''


def test_text_hash_is_stable_across_processes():
    import hashlib
    from sentiment import _text_hash
    a = _text_hash('Gold slumps as real yields rise')
    assert a == _text_hash('  GOLD SLUMPS AS REAL YIELDS RISE ')
    assert a == hashlib.sha1(b'gold slumps as real yields rise').hexdigest()[:16]
    assert a != str(hash('gold slumps as real yields rise')), 'still the salted hash()'


def test_telegram_preview_reports_a_bad_template_instead_of_a_500(client):
    saved = A.CONFIG.get('telegram')
    A.CONFIG['telegram'] = dict(saved or {})
    A.CONFIG['telegram']['template'] = '{not_a_field} {title}'
    saved_arts = A.STATE['articles']
    A.STATE['articles'] = [{'id': 'x', 'title': 't', 'link': 'http://x',
                            'assets': ['BTC'], 'published_ts': time.time() - 60,
                            'credibility': 0.9, 'age_hours': 0.1,
                            'source_name': 'S', 'summary_fa': 's'}]
    try:
        r = client.post('/api/telegram/preview')
        assert r.status_code == 400
        assert r.get_json()['error'] == 'template_error'

        A.CONFIG['telegram']['template'] = '{index}. {title}'
        assert client.post('/api/telegram/preview').status_code == 200
    finally:
        A.STATE['articles'] = saved_arts
        if saved is None:
            A.CONFIG.pop('telegram', None)
        else:
            A.CONFIG['telegram'] = saved


# ── C2 · the retired worker cannot wipe the current one's caches ───────────

def test_the_stale_worker_is_a_tombstone():
    import re
    sw = (pathlib.Path(__file__).resolve().parent.parent / "static" / "sw.js").read_text(
        encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", sw, flags=re.S)   # the prose explains the old bug
    assert 'caches.open' not in code        # it precaches and serves nothing
    assert 'addAll' not in code
    assert "'fetch'" not in code            # and has no fetch handler
    assert 'freebuff-v4' in code and 'unregister' in code


# ── api_proxy_image hardening ──────────────────────────────────────────────

def test_api_proxy_image_rejects_svg(client, monkeypatch):
    class FakeResp:
        status_code = 200
        headers = {'Content-Type': 'image/svg+xml'}
        def close(self): pass
    monkeypatch.setattr('requests.get', lambda *a, **kw: FakeResp())
    r = client.get('/api/proxy-image?url=https://example.com/logo.svg')
    assert r.status_code == 415


def test_api_proxy_image_enforces_size_cap_while_streaming(client, monkeypatch):
    class FakeLargeResp:
        status_code = 200
        headers = {'Content-Type': 'image/png'}
        def iter_content(self, chunk_size=65536):
            # Yield 7MB in 1MB chunks (limit is 6MB)
            for _ in range(7):
                yield b'X' * 1024 * 1024
        def close(self): pass
    monkeypatch.setattr('requests.get', lambda *a, **kw: FakeLargeResp())
    r = client.get('/api/proxy-image?url=https://example.com/large.png')
    assert r.status_code == 413


def test_api_proxy_image_success_adds_nosniff(client, monkeypatch, tmp_path):
    fake_png = b'\x89PNG\r\n\x1a\n' + b'0' * 200
    class FakeOkResp:
        status_code = 200
        headers = {'Content-Type': 'image/png'}
        def iter_content(self, chunk_size=65536):
            yield fake_png
        def close(self): pass
    monkeypatch.setattr('requests.get', lambda *a, **kw: FakeOkResp())
    monkeypatch.setattr(A, 'IMAGE_CACHE_DIR', tmp_path)
    r = client.get('/api/proxy-image?url=https://example.com/valid.png')
    assert r.status_code == 200
    assert r.headers.get('X-Content-Type-Options') == 'nosniff'

    # Cached hit must also return nosniff
    r_cached = client.get('/api/proxy-image?url=https://example.com/valid.png')
    assert r_cached.status_code == 200
    assert r_cached.headers.get('X-Content-Type-Options') == 'nosniff'

