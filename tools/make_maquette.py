#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build a single-file, offline *maquette* of the dashboard.

The maquette is the real page — the same stylesheet, the same markup, the same
renderers — with every `/api/…` call answered from a JSON snapshot taken off a
running server. So the file a reviewer opens is not a redrawn approximation of
the product: it *is* the product, with frozen data and no backend. Every tab,
the new one-line filter toolbars and their sheets, the article modal, the report
with its sources button, the ideas cards and the price marquee all work.

    python tools/make_maquette.py                    # http://127.0.0.1:5055
    MOHMD_MAQUETTE_BASE=http://host:port python tools/make_maquette.py

Writes `mockup/mohmd-dashboard-maquette.html` and prints its size. Snapshots are
trimmed (the newest slice of each list) so the file stays shareable by mail or
messenger instead of shipping the whole database.
"""

import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dashboard_html import APP_HTML                       # noqa: E402

BASE = os.environ.get("MOHMD_MAQUETTE_BASE", "http://127.0.0.1:5055").rstrip("/")
OUT = os.path.join(ROOT, "mockup", "mohmd-dashboard-maquette.html")

# how much of each endless list the maquette carries. The point is a file that
# can be mailed or sent on a messenger, so every endless list is cut to the part
# a reviewer will actually scroll through.
N_ARTICLES = 36
N_ARCHIVE = 10
N_SOURCES = 20
N_CAL_EVENTS = 18
N_CAL_NEXT = 28
N_FNG_HISTORY = 12
IDEAS_LIMIT = 6
IDEAS_LIMIT_MAIN = 16
REPORT_SYMS = ("BTC", "XAU")
REPORT_FA = ("BTC",)
ARTICLE_IDS = 10              # the modal «متن کامل» must work down the visible list


def fetch_json(path, timeout=90):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as exc:                                # noqa: BLE001
        print(f"  ! {path}: {type(exc).__name__} {exc}")
        return None


# The dashboard's write paths. A file with no backend should not toast
# «حذف نشد — دوباره تلاش کن» at a reviewer who clicks anything, so these
# answer like the server would. Nothing is persisted — the page carries the
# «ماکت نمایشی» badge and every list re-reads the frozen snapshot.
DEMO_ROUTES = {
    "/api/refresh":           {"ok": True, "started": True},
    "/api/article/hide":      {"ok": True, "hidden": 1},
    "/api/article/restore":   {"ok": True, "restored": 0},
    "/api/settings":          {"ok": True, "demo": True,
                                "note": "ماکت نمایشی — چیزی ذخیره نشد"},
    "/api/recover":           {"ok": True},
    "/api/recover/status":    {"running": False, "done": 0, "total": 0,
                                "attempts": 0, "fixed": 0},
    "/api/telegram/test":     {"ok": True, "demo": True},
    "/api/telegram/send-now": {"ok": True, "sent": 3, "demo": True},
    # the smart-alert builder posts free text here; offline there is no bot, so
    # it answers the way the real endpoint does when Telegram is unconfigured
    "/api/telegram/send":     {"ok": False, "error": "demo_no_bot"},
    "/api/telegram/preview": {
        "ok": True,
        "text": ("<b>MOHMD NEWS</b> · خلاصهٔ بازار\n\n"
                 "• بیت‌کوین: به‌روزرسانی بازار\n"
                 "• طلا: تحلیل فلزات گرانبها\n"
                 "• تقویم اقتصادی: رویدادهای پیش رو\n\n"
                 "(نمونهٔ پیام در ماکت نمایشی — ارسال واقعی نمی‌شود)"),
    },
}


def wait_for_prices(timeout=150):
    """A freshly booted server serves articles long before its first market
    cycle, so a snapshot taken in the first minute has no prices at all — an
    empty price marquee and no live quote on any card, which is exactly the
    thing that makes a maquette look broken. Wait for the market block."""
    waited = 0
    while waited <= timeout:
        probe = fetch_json("/api/live")
        prices = (probe or {}).get("prices") or {}
        if prices:
            print(f"  market ready after {waited}s ({len(prices)} assets)")
            return True
        print(f"  waiting for the market cycle… ({waited}s)")
        time.sleep(10)
        waited += 10
    print("  ! no prices after waiting; the maquette will have an empty ticker")
    return False


def trim_data(d):
    if not d:
        return d
    for key, n in (("articles", N_ARTICLES), ("archive", N_ARCHIVE), ("sources", N_SOURCES)):
        if isinstance(d.get(key), list):
            d[key] = d[key][:n]
    return d


def trim_report(d):
    """The report's chart column embeds the TradingView widget — the huge
    OHLC / indicator series in `chart` are never drawn (only `chart.price`,
    read by updateChartLive for the quote line). Keeping the scalars and
    dropping the series takes a report from ~82 KB to ~38 KB, which is what
    makes shipping a report for *every* asset affordable."""
    if not isinstance(d, dict):
        return d
    ch = d.get("chart")
    if isinstance(ch, dict):
        for k, v in list(ch.items()):
            if isinstance(v, list):
                ch.pop(k)
    return d


def trim_econ(d):
    if not d:
        return d
    for key, n in (("calendar", N_CAL_EVENTS), ("calendar_next", N_CAL_NEXT)):
        block = d.get(key)
        if isinstance(block, dict) and isinstance(block.get("events"), list):
            block["events"] = block["events"][:n]
    fng = d.get("fng")
    if isinstance(fng, dict) and isinstance(fng.get("history"), list):
        fng["history"] = fng["history"][:N_FNG_HISTORY]
    return d


STUB = r"""
<script>
/* ── maquette runtime ────────────────────────────────────────────────────────
   Every /api/… call is answered from the JSON snapshot in #mohmd-mock, so this
   page is the real dashboard (same CSS, markup and renderers) with the server
   taken away. Anything not in the snapshot answers with a clear 404 instead of
   hanging, and non-/api requests (the TradingView widget, news thumbnails) go
   to the network exactly as they do in the live app. */
(function () {
  var el = document.getElementById('mohmd-mock');
  var MOCK = {};
  try { MOCK = JSON.parse((el && el.textContent) || '{}'); } catch (e) { MOCK = {}; }
  var KEYS = Object.keys(MOCK);

  function find(url) {
    if (!url) return null;
    var i = url.indexOf('/api/');
    if (i < 0) return null;
    var p = url.slice(i);
    if (Object.prototype.hasOwnProperty.call(MOCK, p)) return MOCK[p];
    var cut = p.indexOf('?');
    var base = cut < 0 ? p : p.slice(0, cut);
    var qp = new URLSearchParams(cut < 0 ? '' : p.slice(cut + 1));
    var cands = KEYS.filter(function (k) { return k.split('?')[0] === base; });
    if (!cands.length) return null;
    var best = null;
    cands.forEach(function (k) {
      if (best) return;
      var kq = new URLSearchParams(k.split('?').slice(1).join('?'));
      ['sym', 'tf', 'id', 'lang', 'window'].forEach(function (kk) {
        if (!best && kq.get(kk) && kq.get(kk) === qp.get(kk)) best = k;
      });
    });
    return MOCK[best || cands[0]];
  }

  function resp(data, ok) {
    var body = JSON.stringify(data === undefined ? null : data);
    return {
      ok: ok !== false, status: ok === false ? 404 : 200,
      statusText: ok === false ? 'Not Found' : 'OK',
      headers: { get: function () { return 'application/json'; } },
      url: '', redirected: false, type: 'basic',
      clone: function () { return resp(data, ok); },
      json: function () { return Promise.resolve(data === undefined ? null : data); },
      text: function () { return Promise.resolve(body); }
    };
  }

  /* A macrotask, never a microtask: the app kicks off its first loadData()
     from the middle of the document, and a promise that settles before the
     parser reaches the later script blocks makes renderAll() throw
     ("faTopic is not defined") — the feed then stayed empty for good. Tying
     the resolution to DOMContentLoaded is the deterministic version of the
     same idea: every script block has run by then, exactly as with a real
     network round trip. */
  function later(value) {
    return new Promise(function (res) {
      function go() { setTimeout(function () { res(value); }, 0); }
      if (document.readyState === 'loading')
        document.addEventListener('DOMContentLoaded', go, { once: true });
      else go();
    });
  }

  var native = window.fetch ? window.fetch.bind(window) : null;
  window.fetch = function (input, init) {
    var url = (typeof input === 'string') ? input : ((input && input.url) || '');
    var d = find(url);
    if (d !== null && d !== undefined) return later(resp(d, true));
    if (url.indexOf('/api/') >= 0) {
      return later(resp({
        ok: false, error: 'maquette',
        note: 'نسخهٔ نمایشی است؛ داده‌ها ثابت‌اند و سروری در کار نیست.'
      }, false));
    }
    return native ? native(input, init) : Promise.resolve(resp({}, false));
  };

  /* belt and braces: if the feed still rendered empty for any reason, load it
     again once the document is complete — a demo must never open on a blank
     news stream. */
  document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
      try {
        var g = document.getElementById('newsGrid');
        if (window.loadData && g && !g.children.length) loadData();
      } catch (e) {}
      mqFill();
    }, 150);
  });

  /* Two tabs are legitimately empty in a fresh browser but look *broken* in a
     file that exists to be reviewed:
       · نشان‌شده‌ها — no bookmarks yet → seed three from the snapshot, once
         per browser (the reviewer may clear them; they must stay cleared)
       · تقویم اقتصادی — opens on today, and today often has no release → load
         the calendar and jump to the first day that actually has events.
     Both run through the app's own functions, so what the reviewer sees is
     the real renderer, not hand-written markup. */
  function mqFill() {
    var tries = 0;
    var timer = setInterval(function () {
      tries++;
      var ready = false;
      try {
        if (typeof DATA !== 'undefined' && DATA && DATA.articles &&
            DATA.articles.length && window.getBookmarks) {
          ready = true;
          var seen = null;
          try { seen = localStorage.getItem('mohmd_mq_seeded'); } catch (e) {}
          if (seen !== '1' && !getBookmarks().length) {
            DATA.articles.slice(0, 3).forEach(function (a) {
              if (a && a.id) toggleBookmark(a.id);
            });
            try { localStorage.setItem('mohmd_mq_seeded', '1'); } catch (e) {}
          }
          if (window.loadCalendar && window.jumpToNextEventDay) {
            var jump = function () {
              try { setTimeout(function () { jumpToNextEventDay(); }, 60); }
              catch (e) {}
            };
            if (typeof ECON === 'undefined' || !ECON) loadCalendar().then(jump, function(){});
            else jump();
          }
        }
      } catch (e) {}
      if (ready || tries > 40) clearInterval(timer);
    }, 250);
  }
})();
</script>
<style>
/* the badge that says what this file is — dismissable, never in the way.
   Same tokens as the DL3 shell: warm graphite plate, copper flag, hairline. */
.mq-badge{
  position:fixed; inset-block-end:14px; inset-inline-start:14px; z-index:9999;
  display:flex; align-items:center; gap:9px; padding:9px 12px;
  background:rgba(19,17,15,.96); border:1px solid rgba(200,150,93,.34);
  border-radius:6px; box-shadow:0 18px 44px -10px rgba(0,0,0,.7);
  color:#CFC6B8; font:12px/1.5 'Vazirmatn', system-ui, sans-serif; direction:rtl;
}
.mq-badge b{ color:#EFE8DD; }
.mq-badge .d{ width:7px; height:7px; border-radius:50%; background:#E6BE8B; box-shadow:0 0 8px rgba(230,190,139,.7); }
.mq-badge button{
  margin-inline-start:4px; width:22px; height:22px; border-radius:4px;
  border:1px solid rgba(236,224,206,.14); background:transparent; color:#9A9083;
  cursor:pointer; font:11px/1 inherit;
}
.mq-badge button:hover{ color:#EBD2AC; border-color:rgba(200,150,93,.58); }
@media print{ .mq-badge{ display:none; } }
</style>
"""

BADGE = """
<div class="mq-badge" id="mqBadge">
  <span class="d"></span>
  <span><b>ماکت نمایشی</b> — دادهٔ نمونهٔ ثابت، بدون سرور</span>
  <button onclick="document.getElementById('mqBadge').remove()" aria-label="بستن">✕</button>
</div>
"""


def build():
    print(f"snapshot source: {BASE}")
    mock = {}
    wait_for_prices()

    data = trim_data(fetch_json("/api/data"))
    if data:
        mock["/api/data"] = data
    assets = ((data or {}).get("config") or {}).get("assets") or ["BTC", "ETH", "XAU"]
    articles = (data or {}).get("articles") or []

    # the three routes the shell polls on its own (prices, ETF table, monitor)
    for path in ("/api/live", "/api/etf", "/api/monitor"):
        got = fetch_json(path)
        if got is not None:
            mock[path] = got

    econ = trim_econ(fetch_json("/api/econ"))
    if econ is not None:
        mock["/api/econ"] = econ


    for sym in assets:
        got = fetch_json(f"/api/fng/{sym}")
        if got is not None:
            mock[f"/api/fng/{sym}"] = got

    # /api/candles is no longer fetched by the dashboard (the TradingView
    # widget streams its own series), so the snapshot skips it — 28 routes and
    # 140 KB of data no renderer ever reads.

    for sym in assets:
        lim = IDEAS_LIMIT_MAIN if sym == "BTC" else IDEAS_LIMIT
        got = fetch_json(f"/api/ideas?sym={sym}&limit={lim}")
        if got is not None:
            mock[f"/api/ideas?sym={sym}&limit={lim}"] = got

    # one translated idea so the «ترجمه» button has something to show
    btc_ideas = ((mock.get(f"/api/ideas?sym=BTC&limit={IDEAS_LIMIT_MAIN}") or {}).get("items") or [])[:2]
    for idea in btc_ideas:
        iid = idea.get("id")
        if not iid:
            continue
        path = f"/api/ideas/translate?sym=BTC&id={iid}"
        got = fetch_json(path)
        if got is not None:
            mock[path] = got

    for sym in REPORT_SYMS:
        got = fetch_json(f"/api/report/{sym}")
        if got is not None:
            mock[f"/api/report/{sym}"] = got
        if sym in REPORT_FA:
            got = fetch_json(f"/api/report/{sym}?lang=fa")
            if got is not None:
                mock[f"/api/report/{sym}?lang=fa"] = got

    # every asset chip in «تحلیل و گزارش‌ها» must open a finished report —
    # before, only BTC and XAU existed and the other twelve showed a 404 note
    for sym in assets:
        if sym in REPORT_SYMS:
            continue
        got = trim_report(fetch_json(f"/api/report/{sym}"))
        if got is not None:
            mock[f"/api/report/{sym}"] = got
    for sym in REPORT_SYMS:
        key = f"/api/report/{sym}"
        if key in mock:
            mock[key] = trim_report(mock[key])
    for sym in REPORT_FA:
        key = f"/api/report/{sym}?lang=fa"
        if key in mock:
            mock[key] = trim_report(mock[key])

    for art in articles[:ARTICLE_IDS]:
        aid = art.get("id")
        if not aid:
            continue
        got = fetch_json(f"/api/article/{aid}")
        if got is not None:
            mock[f"/api/article/{aid}"] = got
        if art is articles[0]:
            got = fetch_json(f"/api/article/{aid}?fa=1")
            if got is not None:
                mock[f"/api/article/{aid}?fa=1"] = got

    # A snapshot that lost its core routes (server down, wrong port) would still
    # produce a file — an empty one that looks broken to whoever receives it.
    # Fail loudly instead, and keep the previous maquette untouched.
    for must in ("/api/data", "/api/econ"):
        if must not in mock:
            print(f"refusing to write: snapshot has no {must} — is the server running at {BASE}?")
            return 1

    mock.update(DEMO_ROUTES)

    blob = json.dumps(mock, ensure_ascii=False).replace("<", "\\u003c")
    html = APP_HTML
    if "<head>" not in html:
        raise SystemExit("APP_HTML has no <head> — refusing to guess where to inject")

    inject = (
        f'\n<script id="mohmd-mock" type="application/json">{blob}</script>\n'
        f"{STUB}"
        f'<script>window.__MAQUETTE__=true;window.__MOCK_ROUTES__={len(mock)};</script>\n'
    )
    html = html.replace("<head>", "<head>" + inject, 1)
    html = html.replace("<body>", "<body>" + BADGE, 1)

    # The storage layer is a real file on disk (that is how the server and the
    # service worker address it), but the maquette is one deliverable file that
    # must open from a desktop with no server: inline the engine and drop the
    # URLs that only exist behind Flask. The PWA bridge itself stands down on
    # `window.__MAQUETTE__`, so no worker is registered and no database is
    # written while somebody is reviewing the design.
    engine = os.path.join(ROOT, "web", "storage_engine.js")
    engine_tag = '<script src="/storage-engine.js"></script>'
    if engine_tag in html:
        if not os.path.isfile(engine):
            print("refusing to write: page loads /storage-engine.js "
                  "but web/storage_engine.js is missing")
            return 1
        with open(engine, encoding="utf-8") as fh:
            body = fh.read()
        html = html.replace(
            engine_tag,
            "<!-- inlined from web/storage_engine.js by tools/make_maquette.py -->\n"
            "<script>\n" + body + "\n</script>",
            1,
        )
    else:
        print("warning: no /storage-engine.js tag in APP_HTML — engine not inlined")
    for tag in ('<link rel="manifest" href="/manifest.webmanifest">',
                '<link rel="icon" type="image/png" href="/icons/icon-192.png">',
                '<link rel="apple-touch-icon" href="/icons/icon-192.png">'):
        html = html.replace(tag, "", 1)
    html = html.replace(
        "<title>MOHMD NEWS — Market Intelligence</title>",
        "<title>ماکت داشبورد MOHMD NEWS — نمایش طراحی</title>",
        1,
    )
    if "fonts.googleapis.com" in html:
        pass                       # the webfont stays; the stack falls back offline

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)

    size = os.path.getsize(OUT)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print(f"  routes in snapshot : {len(mock)}")
    print(f"  size               : {size/1024:.0f} KB")
    weights = sorted(
        ((len(json.dumps(v, ensure_ascii=False)), k) for k, v in mock.items()),
        reverse=True,
    )[:8]
    print("  heaviest routes    : " + ", ".join(f"{k} {n/1024:.0f}KB" for n, k in weights))
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
