# MOHMD NEWS — Persian Crypto & Macro News Dashboard
**Project overview for external code review** · Generated 2026-09-19 · ~7,400 lines of Python, no build step

---

## 1. What this project is

A self-hosted, single-process **Flask** web app that:

1. Scrapes **107 free news sources** (RSS + Google-News search + Reddit social) every **15 minutes**
2. Validates each article locally (no AI API): credibility score 0–1, hard rejects for sponsored/spam/stale content
3. Translates titles & summaries to **Persian** (Google Translate free endpoint, with persistent cache)
4. Tags every article to tracked assets, computes technical indicators from **Yahoo Finance** candles
5. Generates a **bilingual institutional-grade analysis report per asset** (Market Overview → Macro → News Impact → Flows → Derivatives → Risk), every section citing the exact news items used (source + Persian date/time)
6. Serves a dark-copper **RTL Persian SPA** with 7 tabs, live prices, TradingView chart, economic calendar, per-asset sentiment, live ETF quotes, Telegram digest, and a source-health monitor with auto-recovery

Everything runs free: **no API keys, no paid services**. Windows-first (`start.bat`), but pure Python.

---

## 2. How to run

```
E:\freebuff
├── start.bat                  # creates .venv if missing, installs deps, opens http://localhost:5055
└── .venv\Scripts\python app.py
```

- Port **5055**; first cycle at boot (~3.5 min for 100+ feeds), then every 15 min (`interval: 900` in `settings.json`)
- Deps: `flask feedparser beautifulsoup4 requests` (+ optional `cloudscraper` for paywall fallback)
- `smoke_test.py` = one-shot pipeline test without the server

**Persistence:** `settings.json` (user config) · `reports/*.json` (last report per asset) · `market_cache.json` (Yahoo disk cache) · `translate_cache.json` (translation cache). News state itself is **in-memory only** (lost on restart — see §9).

---

## 3. File map (all Python, no framework)

| File | Lines | Role |
|---|---:|---|
| `app.py` | 1,664 | Flask server: 18 endpoints, `run_cycle` pipeline, config, Telegram, monitor, archive, per-asset sentiment, ETF quotes |
| `dashboard_html.py` | 1,927 | The entire SPA as one Python string: CSS + HTML + vanilla JS (~72k chars of JS). Rendered at `/` |
| `sources.py` | 517 | **107 source registry** (name, RSS URL, trust 0–1, tier, kind) · **asset registry** (13 builtin + user custom) · keyword→asset patterns · credibility scoring constants |
| `scraper.py` | 547 | Parallel feed fetcher (ThreadPool, 97 parallel + 10 serialized), UA fallback ladder, RSS image extraction + `og:image` fallback, failure classification, article validation & scoring |
| `report_generator.py` | 685 | Bilingual report builder per asset: section writers, news selection (credibility-ranked), citation formatting, markdown export |
| `news_bypass.py` | 700 | Paywall bypass reader (ported from user's tool): site configs for 14 paywalled domains, ladder = direct → AMP → Googlebot UA → Google Cache → cloudscraper(if installed) |
| `indicators.py` | 292 | Pure-python TA: SMA/EMA/RSI/MACD/ATR/Bollinger/pivots/trend terms. Feeds reports & candlestick chart |
| `market_data.py` | 242 | Yahoo v8 chart API wrapper (with `-USDT`→`-USD` retry), CoinGecko/Binance live prices, 1y daily history, disk cache |
| `translate.py` | 241 | Persian translation (Google free endpoint), batch + persistent disk cache, digit conversion |
| `calendar_data.py` | 777 | **TradingView Economic Calendar** (exact UTC epochs, actual/forecast/previous + revisions, 1/0/−1 importance, 13 majors) with the faireconomy JSON mirror as fallback, the English explainer engine (`event_doc`), Fear&Greed (alternative.me), macro quotes (DXY/SPX/VIX/WTI via Yahoo), market sessions — all cached, independent failure |
| `tv_ideas.py` | 344 | Public **TradingView ideas** per asset tag: parses the embedded JSON on `/ideas/<tag>/`, returns chart image + text + a **resolvable permalink** (`chart_url`, never `/idea/<id>/` which 404s), the card badges (`is_picked` / `is_hot` / `is_video` / `is_education`) and the **author's follower count** (read once per author from the profile page, cached 24 h). Also owns TradingView's sort modes (`popular` / `recent` / `followers`) and badge filters. 30-min item cache, fails to `[]` |
| `fa_format.py` | 133 | Jalali dates, Tehran tz, Persian digits, "ago" strings |
| `smoke_test.py` | 81 | Offline pipeline smoke test |
| `probe8.py`, `probe9.py` | 92+70 | **Leftover scratch probe scripts from source-hunting — safe to delete** |

**Data flow (one cycle):**
```
107 feeds ──parallel──▶ raw entries ─▶ dedupe/validate/score ─▶ translate titles ─▶ tag assets
                                                                              ├─▶ STATE["articles"] (24h window)
                                                                              ├─▶ STATE["archive"]  (older, cap 1200)
market: Yahoo+CoinGecko+Binanche ─▶ 14 assets snapshot ──────────────────────┼─▶ STATE["market"]
                                                                              ├─▶ 14 reports (reports/*.json)
calendar/ETF-F&G/macro (cached) ─────────────────────────────────────────────┴─▶ /api/econ
after cycle: Telegram digest (if enabled+configured) · health history per feed
```

---

## 4. API endpoints (all under `app.py`)

| Endpoint | Purpose |
|---|---|
| `GET /` | the SPA |
| `GET /api/data` | **main payload**: articles (24h window) + `archive` + market snapshot + sources view + config + counts. UI polls every 60s |
| `GET /api/stats` | cycle stats |
| `GET /api/chart/<sym>` | indicator chart payload (RSI/MACD/BB/levels). **Unused since 2026-09-28** — the feed's candle panel that fetched it was removed on request; the endpoint stays for any external client until one asks for something else |
| `GET /api/live` | live prices (CoinGecko→Binance→Yahoo ladder) + global Fear&Greed, 15s poll |
| `GET /api/etf` | live spot-ETF quotes (8 symbols: BITO/IBIT/FBTC/GBTC/ARKB/ETHA/ETH/ETHE) via Yahoo v8, 60s cache |
| `GET /api/fng/<sym>` | **per-asset Fear & Greed** 0–100 from that asset's last-24h headlines — local keyword polarity weighted by source credibility and freshness, returned with the bullish/bearish item counts (`pos`/`neg`), 15min cache |
| `GET /api/candles/<sym>` | live candles (60m/240m/1d). **Unused since 2026-09-28** — it fed the in-app candlestick chart, which is gone (see §36); no page in the SPA calls it any more |
| `GET /api/article/<id>` | full article content; paywalled domains go through `news_bypass` ladder, others direct with bypass as fallback; Persian option; cached |
| `GET /api/report/<sym>` | full bilingual report (sections list) |
| `GET /api/report/<sym>/markdown` | markdown export |
| `POST /api/refresh` | manual cycle trigger |
| `GET /api/econ` | calendar — this week + next week (Monday→Sunday UTC), each row carrying the epoch, the printed actual/forecast/previous, the parsed numbers, the surprise and a 4-section English explainer — plus F&G, macro quotes and sessions |
| `GET /api/ideas?sym=BTC&sort=&kind=` | TradingView ideas for **one asset**: items carry chart image, snippet/body text, the real permalink, badges, timeframe and author followers. `sort` = `popular`/`recent`/`followers`, `kind` = `all`/`picked`/`video`/`education` |
| `GET /api/ideas/translate?sym=BTC&id=` | Persian version of one idea for the modal (background thread; answers `pending:true` first, then `title_fa` + paragraphs) |
| `POST /api/telegram/*` | test / preview / send-now |
| `GET /api/monitor` | per-source health: ok, latency, last count, failure **cause** (English), 30-cycle sparkline history |
| `POST /api/recover` | one-button recovery: retries broken feeds (mirrors → AMP → alternate UA) |
| `POST /api/settings` | persists assets/window/interval/auto-reports/sources |

---

## 5. UI tabs (Persian RTL, dark copper theme, WCAG-minded)

1. **📰 News Feed** — 4-wide card grid, thumbnails (RSS media → og:image fallback → 📰 placeholder), credibility badge on image, Persian headlines (bold 800), Persian dates (Jalali) + EDT times, filter stack: search box / source-kind / source / sort / credibility slider (0–100%) / asset+topic tag bar. Default sort **Newest first**, 400 rendered cards.
2. **📊 Analysis & Reports** — per-asset report document + copy (text only) + markdown + Persian version toggle + **TradingView Advanced Chart widget** (free official embed) + **the asset's own Fear & Greed panel under the chart** (gauge, label, bullish/bearish news counts, global index reference).
3. **🩺 Source Health** — all 107 sources with ✓/✗, latency, news count, failure cause (English), 30-cycle health sparkline, single **Recover** button.
4. **📅 Economic Calendar** — ForexFactory week grouped **per-day boxes**, impact badges (🔴🟡⚪), FCST/PREV chips, per-event live segmented countdown (days/hours/min/sec boxed timer), released events ticked **✔ منتشر شد** with distinct style, sort by time/impact, filters (impact/country/hide-past), header countdown to next High event. Sidebar: Market Sessions.
4b. **💡 ایده‌های تریدینگ‌ویو** — its own analysis tab (rail group **تحلیل**): an asset chip row filters ideas per asset, plus **TradingView-style filters** — sort (محبوب‌ترین = TV's default Popular feed, جدیدترین, بیشترین دنبال‌کننده), type (منتخب سردبیر / آموزشی / ویدیو — the badges TV puts on its cards) and a timeframe lane built from the loaded ideas. Each card shows the **chart image, title, snippet, direction, timeframe, likes/comments, the author with their follower count and the permalink button**; «📖 متن کامل ایده + ترجمه فارسی» opens an in-app modal (chart, full text, author, stats) with a **🇮🇷 ترجمهٔ فارسی button** that streams the translated title + body in, exactly like the news reader.
5. **🗄 Archive** — articles that fell out of the 24h window (server keeps ≤1200, serves ≤250 newest).
6. ~~**😱 Fear & Greed tab**~~ — **removed on request.** The gauge now lives **inside each asset report, under the chart** (`#repFng`): the asset's own 0–100 reading with its bullish/bearish/news breakdown, plus the global alternative.me index as a reference line. No standalone tab, no rail entry.
6b. **🏛 ETF** — a pure **live rate board**: **56 funds** (every US spot BTC and ETH ETF, Solana and XRP ETFs, futures, leveraged/inverse, crypto-equity, blended and macro funds) boxed per family with **group chips + a search box**, refreshed every ~2 min. Names come from Yahoo's own meta (`longName`) so a renamed fund can never show a stale label. The old spot-BTC ETF **net-flow table (Farside) and the whole flow plumbing were removed**, together with the “Yahoo” source label in the panel heading.
7. **📨 Telegram** — token/chat, **message template** with variables (`{title} {summary_fa} {cred} {stars} {tags}` + hyperlinks + #hashtags), live preview, silent/pin/quiet-hours/min-cred/max-items/max-age/language/asset-filter, send-now button.

Top bar: cycle status + next-cycle countdown + window pill + refresh; icon buttons → **⚙ Settings** (interval 15/30/60, window 24/48/72/168h, asset toggles, auto-reports) / **📡 Sources** / **💹 Assets** (add custom ticker → auto Yahoo resolution + full report).

**Asset strip:** 14 cards (BTC ETH BNB SOL XRP ADA DOGE LINK XAU XAG + **WTI DXY SPX VIX**) — live price, 24h change (green/red), sparkline, news count, click → report. Macro assets are full registry members.

---

## 6. Credibility model (pure-local, explainable)

- **Hard reject** (scored out): sponsored/press-release patterns, spam topics, SEO pages, titles <20 chars, older than window (24h default)
- **Base** = source trust (tier-1 wires 0.95–0.97 … unknown 0.64 default)
- **Penalties**: clickbait −0.15 · thin body −0.20 · risky claims −0.10 · affiliate links −0.35
- **Freshness multiplier**: ≤6h ×1.00 · ≤24h ×0.96 · ≤48h ×0.90 · older ×0.84
- Reports cite only items ≥ `REPORT_MIN_CREDIBILITY`; the UI slider filters the same score

---

## 7. Notable design decisions

- **Single process, in-memory STATE + two locks** (`STATE_LOCK`, `CYCLE_LOCK`); API handlers never do blocking network work except the explicitly-cached ones (etf/fng/econ with 60s–30min caches)
- **All free data paths** with graceful degradation: every external fetch fails independently to `None`/cache
- **Translation cache on disk** — repeat boots translate almost nothing
- **Bypass reader integrated** rather than external: paywalled domains get the ladder first, normal sites get it as fallback only when content looks partial
- **Persian-first UX**: Jalali dates, Persian digits with `dir=ltr` isolation for numbers, RTL-safe CSS (logical properties), tabular numerals in timers

---

## 8. Recent history (Sept 2026, in order)

Archive tab + server-side archive merge · 24h default window (user-selectable) · per-asset sentiment (`/api/fng/<sym>`) · live ETF quotes (`/api/etf`) · removed alert price/keyword system (Telegram kept & expanded) · calendar redesigned (per-day boxes, boxed timers, released-tick) · Fear&Greed own tab · bypass tool ported into project · og:image thumbnail backfill · full-width layout + card grid redesign · **WTI/DXY/SPX/VIX promoted to full assets with reports** · fixed: `STATE_LOCK` deadlock in monitor, undefined-`now` NameError breaking cycle save, JS stray-brace breaking whole script, Yahoo v7→v8 for ETF quotes.

---

## 9. Known limitations & tech debt (for the reviewer)

1. **In-memory news state** — restart wipes feed/archive until the first cycle refills (~3.5 min). Archive is not persisted.
2. **Thread-safety is coarse**: one big `STATE_LOCK` around snapshot copies; fine at this scale, not audited for heavy concurrency.
3. **`MAX_AGE_HOURS = 72` constant in `sources.py`** is only a fallback default; effective window is `CONFIG["report_max_age_hours"]` (24). Naming is confusing; `smoke_test.py` docstring still says 72h.
4. **Paywalls**: investing.com & Bloomberg remain unreadable even via bypass ladder (anti-bot) — article modal shows a graceful "full text unavailable + link" message. MarketWatch/CNBC/WSJ etc. work.
5. **Hotlink-protected images** (some domains 403 the browser) fall back to the 📰 placeholder — server-side image proxy would fix it (not built).
6. **Per-asset F&G is a heuristic** over dashboard headlines, **not** the crypto Fear&Greed index per coin (that only exists globally from alternative.me).
7. **Yahoo v7 quote endpoint** is deprecated (crumb-gated) — ETF quotes already use v8; `_etf_quotes` fetches 8 symbols in parallel each 60s only when requested.
8. **`probe8.py`/`probe9.py` are leftover scratch files** — deletable.
9. **No tests** beyond `smoke_test.py` (no unit tests for scoring/indicators/translation).
10. **No auth** — bind to localhost assumed; do not expose directly to the internet.
11. `README.md` (7k) predates several features; this file is the accurate snapshot.

---

## 10. Suggested review focus (what Claude should look at)

- `app.py::run_cycle` — cycle transaction, archive merge logic, lock usage
- `scraper.py::validate_article` + `sources.py` patterns — scoring quality/false positives
- `dashboard_html.py` JS — it's one big inline script; check the polling layer (60s `/api/data`), countdown timers (memory: `setInterval` cleared per render), and XSS escaping (`esc()` coverage on all interpolations)
- `news_bypass.py` — legality/ethics note: it's a paywall reader; keep for personal use
- `report_generator.py::select_news` — citation ranking and section assembly
- Failure surfaces: every external call should degrade independently (spot-check)

---

## Update — 2026-09-20 · DL2 (design language 2.0 + hardening)

UI (dashboard_html.py, additive labelled blocks `DL2 — DESIGN LANGUAGE 2.0 · phase 1..5`):
WCAG-AA ink ramp (`--faint` 3.97:1 → 5.0:1), 9-step type scale with a 12px readability floor,
Persian leading 1.8, 68ch report measure, unified interaction states, focus rings,
reduced-transparency/reduced-motion support, price ticker, lead-story row, sticky filter
console, feed density rules, sticky chart column, sources disclosure, KPI grids, two-column
settings, grouped nav rail with a persisted 64px collapsed mode, print styles.
Fixed on the way: the UI claimed a 72h window while the engine used 24h (repeated `selected`),
`role=tablist` added, dead shadowed `redrawChart()` removed, duplicate 60s `/api/data` poll removed.

Backend / quality:
- `/api/proxy-image` hardened against SSRF (private/loopback/link-local/CGNAT hosts blocked) and capped at 6 MB
- `market_cache.json` + `translate_cache.json` written atomically (temp file + `os.replace`)
- localhost bind by default (`--public` / `MOHMD_HOST` to expose, `MOHMD_TOKEN` for a shared secret)
- Telegram token/chat may come from `MOHMD_TG_TOKEN` / `MOHMD_TG_CHAT` instead of settings.json
- per-source circuit breaker in `scraper.py` (4 failed cycles → exponential cooldown, auto-recovery)
- reports now use the real Yahoo high/low arrays for ATR instead of the close-bucket proxy
- `/api/health` endpoint, `requirements.txt`, `tests/test_core.py` (13 tests, pytest)
- legacy scratch files moved to `backups/legacy_removed/` (probe8/9, freebuff.rar, old HTML backups)

**Limitations that no longer apply:** news state is hydrated from SQLite at boot (`database.py`),
so the dashboard is no longer empty after a restart; and the Fear & Greed feed is served in its own
tab (spot-BTC ETF flows were removed entirely — see the 2026-09-23 update below).
- Feed fetches are now conditional (`If-None-Match` / `If-Modified-Since`); publishers answering 304
  cost a few hundred bytes instead of a full feed re-download, which shortens every cycle.
- The report now cites live derivatives data (Binance futures funding / open interest / long-short
  account ratio, free and key-less) in section 6, plus the alternative.me Fear & Greed reading in
  section 4 — each degrades to an explicit "data gap" line when an endpoint does not answer.
- Images reserve their box (`aspect-ratio`) so lazily-loaded thumbnails cannot shift the layout.

---

## Update — 2026-09-23 · ideas tab + ETF board

**TradingView ideas got their own tab** (`💡 ایدههای تریدینگویو`, rail group **تحلیل**, between
reports and ETF). The links never opened because the cards were built from the payload's numeric
`id` (`https://www.tradingview.com/idea/<id>/` → **404**); the parser now returns the payload's
`chart_url` permalink, so every card opens. The chart thumbnail was wrong too — it guessed
`s3.tradingview.com/s/<slug>.png` (403) instead of the payload's `image.big` (200). Cards now show
**chart image + title + text (snippet, with an expandable full text) + likes/views/comments + a
permalink button**, and an **asset chip row filters ideas per asset** (`/api/ideas?sym=…`, 12 ideas
per asset, 30-min server / 15-min client cache). `TAG_BY_ASSET` now covers LINK and uses
`dollarindex` for DXY.

**The ETF tab is a live rate board** (`نرخ زندهٔ ETF`): the spot-BTC ETF flow table and its whole
plumbing are gone — `_etf_flows()`/`_etf_num()` in `calendar_data.py`, the `etf` key of `/api/econ`,
`renderEtfFlows`/`flowBar`/`#etfBox2` in the UI, the Farside sentence in `sec_flows`
(`report_generator.py`) and the PHP mirror. Quotes are now boxed per fund family
(Bitcoin / BTC futures / Ethereum / Crypto equity / Commodities / Markets) with a 60-s refresh, and
the “Yahoo · ۶۰s” source label was dropped. (`--border-strong` was referenced in CSS but never
defined; it now exists.)

`wp-plugin/mohmd-news/assets/` was regenerated with `tools/extract_assets.py`; its `/ideas` route
stays an intentional stub, and the tab says so instead of spinning forever.

**Second pass (same day):** the ideas tab now carries **TradingView's own filters** — the site's
default **Popular** ranking, Latest, the **Editors'-pick** badge filter, video/education badges and a
timeframe lane — and every idea exposes its **author's follower count**, so analysts with a real
following rank above one-off posters (`sort_items` weights likes/comments/followers/picked/hot).
Clicking **متن کامل** opens an in-app modal exactly like a news item (chart image, full text,
author, engagement) with a **🇮🇷 ترجمهٔ فارسی** button backed by the new `/api/ideas/translate`
route, which translates the title + body off-thread and is polled until ready — the same
background-then-poll contract as `/api/article`.

**Fear & Greed moved into the reports.** The tab, its nav entry, its view and the 10-card sentiment
grid are gone; every asset report now renders its own gauge **under the chart** (`#repFng`, fed by
`/api/fng/<sym>`) — score, Persian label, a bullish/bearish/news breakdown and the global
alternative.me index as a reference line.

That move exposed a real bug worth recording: the per-asset score multiplied every headline by
`a["sentiment"]`, **a field nothing in the pipeline ever wrote**, so every asset collapsed to
`50 + freshness` and the whole board printed the identical number (56 for all of BTC/ETH/XAU/WTI…).
`app.py` now scores headlines directly with a local, explainable keyword lexicon
(`headline_polarity` / `asset_sentiment`): bullish vs bearish term counts over the title + summary,
weighted by source credibility and freshness, 50 + 42 × polarity. The ten tracked assets now read
independently (e.g. BTC 62 Greed with 72 positive / 19 negative, WTI 42 **Fear** with 12 / 29). The
same lexicon is mirrored in the plugin's `class-mn-rest.php`.

The **ETF board was completed**: 56 funds across 10 families (spot BTC 12, BTC futures 2,
leveraged/inverse 6, spot ETH 10, Solana 4, XRP 2, blended 4, crypto equity 5, commodities 6,
markets 5), each verified to resolve on Yahoo. Fund names are taken from Yahoo's `longName`
(which also fixed “ETH”, previously mislabelled as a ProShares fund — it is the Grayscale Ethereum
Mini Trust), the cache is 120 s, and the board gained group chips + a search box so a 56-card grid
stays navigable.

## WordPress twin is now feature-complete (v1.1.0)

The plugin in `wp-plugin/mohmd-news/` is the PHP/WP-Cron twin of this Flask app (no Python server,
no API key) and now covers everything the Python dashboard shows. `tools/deploy_wp_plugin.py`
lints every PHP file with the bundled PHP CLI and then copies the plugin into a site's
`wp-content/plugins/` — one-way, so the Python project is never touched:

```
.venv\Scripts\python tools/deploy_wp_plugin.py                       # the mohmd-news.local site
.venv\Scripts\python tools/deploy_wp_plugin.py --site "C:/path/to/wp" --dry-run
```

Ported in this round:

* **TradingView ideas** — a new `includes/class-mn-ideas.php` is a line-by-line port of `tv_ideas.py`:
  the embedded page JSON is pulled out with a string-aware bracket scan, items are parsed into the
  same 24-field shape, permalinks come from `chart_url` (the numeric id 404s) and thumbnails from
  `image.big`. Author follower counts are read from the public profile pages once a day
  (`mn_tv_followers` transient, fetched in one curl_multi batch) — that is what powers
  “بیشترین دنبالکننده”. `/ideas` and `/ideas/translate` are registered in `class-mn-rest.php`;
  the translation runs off-request via the `mn_idea_translate` single event + `spawn_cron()`, so the
  modal gets `pending:true` and polls, exactly like `/api/article`. Live check on the deployed site:
  **10/10 images 200, 10/10 permalinks 200**, ETH `kind=picked` returning `ok:false` matches the
  Python result for the same feed (that page currently has no editors' picks).
* **ETF parity** — `etf_yahoo_map()` now carries the full 56-fund / 10-family registry and
  `etf_quotes()` prefers Yahoo's `longName`/`shortName` over the static fallback label.
* **Fear & Greed under the chart** — `/fng/<sym>` already returned the same payload as Flask
  (`now`, `label`, `count`, `pos`, `neg`, `sent`); the shared JS builds `#repFng` under the chart, so
  the WordPress report tab shows each asset's own gauge (verified live: BTC 64/100 “طمع”,
  103 positive / 23 negative headlines).
* **Assets resynced** — `tools/extract_assets.py` regenerated `mn.css` / `mn.js` / `shell.html` from
  the current `dashboard_html.py` (this also re-removed the retired F&G nav item).
* **Front page** — `MN_Admin::action_make_landing()` + the “🏠 ساخت لندینگ و تنظیم صفحهٔ اول” button
  create a page holding `[mohmd_landing]`, publish it and set it as the static front page. The
  `template_redirect` bypass renders it theme-free, so the landing is pixel-identical to
  `landing-preview.html`.

The only deliberate gap left is the Telegram digest (the `alerts` nav button is stripped by
extract_assets); everything else — feed, reports + chart, assets, sources monitor, calendar,
settings, archive, bookmarks — is live in WordPress.

### Why the WordPress feed could come up empty (and the fix)

The owner loaded `/mohmd-dashboard/` during a cycle and got a blank board: no cards, empty chip
rows and “تعداد خبر: —”. The cause was not the data: `/api/data` (1.4 MB, ~600 articles) rebuilds
from the DB on every request, and while a cycle is inserting hundreds of rows MySQL holds the table
lock — a stats call measured **19.5 s** during one cycle, and a browser that gives up on `/api/data`
leaves `DATA` null, so every renderer returns early (that is exactly the “—” + empty grid state).

The endpoint is now cache-first and cycle-aware (`MN_Rest::data()` → `build_data()`):

* a fresh payload is served for **60 s** from `mn_cache/data-payload.json` (0.1–0.6 s instead of
  seconds-long rebuilds), and `MN_Cycle::run()` deletes it in its `finally` block so the next poll
  rebuilds with the rows that cycle just wrote;
* if the cache is cold **and** `mn_cycle_lock` is set, the *stale* payload (up to 6 h) is returned
  instead of blocking on a locked table — a running cycle can no longer blank the dashboard;
* a `Throwable` anywhere in the build falls back to the stale payload too.

Measured after the change: 18 consecutive `/api/data` calls during and around a cycle — worst
0.35 s, zero empty payloads (was: unbounded wait → empty board).

### Full end-to-end test of the twin — `tools/wp_e2e_test.py`

```
.venv\Scripts\python tools/wp_e2e_test.py                 # 85 checks against the live site
.venv\Scripts\python tools/wp_e2e_test.py --quick         # skip network + translation checks
.venv\Scripts\python tools/wp_e2e_test.py --json e2e.json # machine-readable report
```

It walks the whole contract the Flask app serves and fails loudly on any drift: the `/api/data`
article shape (24 fields), newest-first ordering, Persian titles, counts/meta, the five polled
endpoints, both pages (landing + dashboard shell), the 56-fund/10-family ETF board, per-asset
Fear & Greed (including a guard that the assets are **not** all printing one shared number), the
ideas contract + real 200s on chart images and permalinks + the pending→cached translation flow,
columnar candles for all four timeframes, the 8-heading/8-paragraph report, full-text extraction
plus Persian body translation, the sources monitor, the economic calendar, the image proxy (and its
non-image guard) and `/api/health`. Current state: **85/85 passing**.

### Landing rebuilt from scratch (full page, live data, own palette)

`templates/landing.php` was rewritten. It is a real full page (hero sized to the viewport, sticky
bar, live board, features, how-it-works, a data-transparency band, final CTA, footer) and **every
number is read from the plugin’s own store at render time** — sources 107, feeds healthy 90/107,
assets 13, articles in window 648, ETF funds 56, families 10, cycles run, interval 30 min, the live
ticker from `/api/live`/stored market, the newest Persian headlines, the ETF up/down split and each
asset’s own Fear & Greed. The old version advertised fixed numbers (“۱۰۶ منبع / ۱۵ دقیقه”) and a
Telegram tile for a section this twin deliberately does not ship — both gone.

Palette: **deep jade + warm sand on near-black** (`--jade:#5ED6B8`, `--sand:#E3C48D`) instead of the
dashboard’s obsidian + copper (`--copper`), so the landing reads as a sibling of the dashboard, not
a clone. The E2E test asserts that difference (`--jade` present, `--copper` absent) and that no
Telegram copy leaks back in.

---

## 14. Economic Calendar rebuilt + the price ticker (Flask app — 2026-09-23)

This round touched **only the main Python project**; the WordPress twin was left untouched on
purpose (the ask was “add this to our own project, not to WordPress for now”).

### The data source was the real bug

The calendar used to be scraped off the ForexFactory HTML table: the wall clock shown on that page
was read in the *page’s* timezone (`America/Los_Angeles`), stamped as UTC, and the year was guessed
from `datetime.now()`. Every next-week row therefore landed at the wrong hour — usually on the
wrong day — and the JSON mirror it fell back to for the current week has no revisions at all.

It now reads **TradingView’s own economic-calendar endpoint** for both weeks:

```
https://economic-calendar.tradingview.com/events?from=<Mon 00:00Z>&to=<Sun 24:00Z>&countries=US,EU,GB,JP,CN,CA,AU,NZ,CH,DE,FR,IT,ES
```

* one exact UTC epoch per event (`date`), so the client formats the time and re-buckets the day
  itself — the timezone selector moves every clock and every day together;
* real `actualRaw` / `forecastRaw` / `previousRaw` values with their `unit`, turned into a parsed
  number, a table-ready string (`1.62M`, `4.5%`, `−2.60B`), a **surprise** (`actual − forecast`) and
  a direction flag (lower-is-better for unemployment/claims/inventories, so a falling print shows
  green);
* `importance` 1/0/−1 → High/Medium/Low, holidays lifted out into their own bucket from
  `indicator: "Holidays"`;
* the faireconomy weekly JSON is kept as a last-resort fallback for the current week.

Fix found while porting: `_fmt_num()` formatted from `abs(n)` in its integer branch, so every
negative reading printed as a positive one (`Richmond Fed −2` → `2`) and its surprise read backwards.
Signs are now carried through every branch, and the surprise uses the same formatter (no more
`-2.6e+09`).

### English explainer per row — `event_doc()`

Every event now carries `doc` (one line) plus `doc_sections`: **four English paragraphs — What it is,
How it is measured, Why it matters, How the market trades it** — reachable from an **ℹ Explain**
button on each row (and from the side rail). 60+ curated glossary entries cover the releases desks
actually watch; everything else is generated from the title itself by classifying it into twelve
categories (speech, auction, inventory, rate decision, document, survey, jobs, inflation, housing,
growth, trade, holiday), inferring the cadence (daily/weekly/monthly/quarterly) and the reporting
period (`m/m`↔`MoM`, `y/y`↔`YoY`, `q/q`↔`QoQ` are one glossary), and stripping reporting qualifiers
(`Flash`, `Prel`, `Final`, `SA`). Deterministic and offline — no model, no API key.

### The tab was rebuilt, and it is English-only

`#view-calendar` is `direction: ltr` (the rest of the dashboard stays RTL): a trading calendar reads
Time → Ccy → Impact → Event → Actual → Forecast → Previous → Explain, and mirroring it made every
row feel scrambled.

* **Hero** — the next high-impact release with a live countdown and five week counters (events,
  high, released, beat forecast, missed forecast).
* **Control panel** — week stepper with the range (`Sep 21 – Sep 27`), a **7-day strip** (each day
  shows its event count, high-impact count and dots), then Impact / Currency / Order / **Timezone**
  (UTC, New York, London, Frankfurt, Tokyo, Shanghai, Tehran, Sydney) / free-text search / *Hide
  released*.
* **Board** — a real table for one day at a time, one grid per row so the header and the rows stay
  aligned; released rows print the actual against the forecast with a coloured surprise, upcoming
  rows carry a live countdown, holidays get their own rail, and every row has the Explain button.
* **Side rail** — Market Sessions, **Week at a glance** (per-day load bars, click to open that day)
  and **Upcoming high impact** (the next six with countdowns).
* Responsive at 1600 / 900 / 390 px with no horizontal overflow: the *previous* column folds away
  below 980 px and *forecast* below 780 px.

The sidebar item itself (تقویم اقتصادی) stays Persian like the rest of the menu — the *content* of
the tab is 100 % English, which is what was asked for.

### Price ticker: compact, always rotating

The ticker under the topbar was a scrolling box you had to drag. It is now a **28–30 px marquee**:
the full series is rendered twice inside `.tk-track` and slides exactly `-50%`, so the loop is
seamless; the duration is computed per render (≈3.4 s per symbol, clamped 30–110 s), it pauses on
hover, `prefers-reduced-motion` users get a plain scrollable strip with no animation, and a fade
mask caps the trailing edge. Stale quotes are a 5 px dot with a tooltip instead of a word.

---

## 15. TradingView chart, report surface and ticker rebuilt (2026-09-26)

A UI-only round in `dashboard_html.py` (no backend, no pipeline change), shipped as one appended
layer — a CSS block at the end of the stylesheet plus one extra `<script>` — because the sheet
duplicates selectors and the last block wins.

### The chart is the official TradingView widget again

The report panel used to draw its own SVG candles. It now mounts TradingView's free, key-less
**Advanced Chart** embed (`s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js`)
with a symbol map for the tracked assets: `BTC → BINANCE:BTCUSDT`, `XAU → OANDA:XAUUSD`,
`WTI → TVC:USOIL`, `DXY → TVC:DXY`, `SPX → FOREXCOM:SPXUSD`, `VIX → TVC:VIX`; a custom asset
resolves from its Yahoo symbol (crypto → `BINANCE:XXXUSDT`). Timeframes are a segmented control
(5m / 1h / 4h / 1d). **⛶ بزرگ‌نمایی** lifts the panel out of the grid to the whole viewport — Esc or
the same button returns — and rebuilds the widget at the new size. If the embed cannot load
(offline, blocked) the old in-app candle chart takes over automatically from `/api/candles`, so the
panel is never empty, and `📊 تحلیلی` stays one click away for the series the report text was
written from.

Two traps worth recording. A finished view animation leaves an identity `transform` on
`.view.active`, and **any** transform makes that ancestor the containing block for
`position:fixed` — the first fullscreen attempt measured 420 px inside a 1600 px viewport; the mode
now neutralises the chain (`body.tv-full .view, .view-container, .app-body { transform:none }`).
And `tvTimeframe()` used to replace the *whole* chart column, which silently deleted the per-asset
Fear & Greed box on every timeframe change; the panel now has its own host (`#chartBoxHost`) and the
gauge survives the swap.

### Reports became a two-pane reading surface

A hero header carries the asset, the as-of stamp, the cited-news count, the live price and the
language/copy actions. The analysis scrolls in its own pane (`max-block-size: calc(100vh - 186px)`,
`overscroll-behavior: contain`, themed scrollbars) beside a sticky chart column, and a section-chip
row jumps inside the pane instead of hunting with the scrollbar. Every source box is now a **bounded
scroll pane** — about four rows visible, «نمایش همه» expands it — with one grid row per citation:
index, Persian title, English original, source, Jalali date, Tehran time, credibility, and the row
itself opens the article. The reveal-on-click accordion and the single-column source walls are gone.
Opening the reports tab before the first `/api/data` lands used to leave the tab empty forever (the
tab needs DATA to pick an asset); `renderAll()` now renders the pending report once the payload
arrives, guarded by `__repPending`.

### The ideas tab is a TradingView-style feed

Hero + sticky filter console (asset / sort / kind / timeframe) and chart-led cards: the idea's own
chart image with its direction and timeframe overlaid, the thesis, the author with follower count,
engagement, and both the full-text + translation action and the permalink. The modal opens from the
image or the title.

### The price ticker is a true infinite marquee

Two identical halves slide exactly `-50%`, and every chip carries its own trailing gap (no flex
`gap`, no padding on the track), so one half's width *is* the loop offset and the seam cannot drift
— the old `gap:16px` version was off by half a gap and jumped every cycle. JS measures one pass and
repeats the series until a half is wider than the bar (measured live: 2 × 4616 px halves inside a
1600 px bar), so the strip can neither run out of chips nor end in a cut gap. It is `direction: ltr`
like the market data it shows (the page stays RTL) and its duration follows the real pixel width, so
the speed is the same at two assets or twenty.

### Source names were removed from the index panels

The Fear & Greed box no longer prints `(alternative.me)` or `(وزن اعتبار منبع + تازگی خبر)`, and the
chart's `(منبع رایگان Yahoo Finance)` caption went with the old panel. Citation rows still name the
outlet — that is what the source boxes are for.

New dev tool: `tools/check_dashboard_js.py` extracts every inline `<script>` from `dashboard_html.py`
and runs `node --check` on it — the page has no build step and a stray brace there kills the whole UI
silently. Current state: 3 blocks, all parsing.

Not touched on purpose: the WordPress twin (`wp-plugin/mohmd-news/assets/` is regenerated from this
file by `tools/extract_assets.py`); the redesign ships in the Flask app first.

---

## 16. Second pass on the same surfaces + news bodies that are ready before the click (2026-09-26)

Reviewed against the running build rather than the source, so the two reported-but-unexplained items
turned out to be one stale process (`app.py` reads the page once at boot — a hard refresh is not
enough, the server has to restart) and one genuinely missing feature.

### Empty article text on Google News links — solved, not apologised for

Roughly half the feed arrives through `news.google.com/rss/articles/<id>` and the id is encrypted,
so every relay rung returned zero words and the modal ended with the "متن کامل قابل استخراج نبود"
note. The address now gets **exchanged** instead of guessed: the article page carries
`data-n-a-sg` (signature) and `data-n-a-ts` (timestamp), and posting those to the public
`batchexecute` endpoint returns the publisher URL. Free, key-less, ~300ms, and hits are cached in
`.news_links.json` (an id maps to one URL forever). Measured on live rows: **4/4 resolved in ~1.4s**,
and the full ladder then produced 160–400 words on cases that previously returned nothing.
Old-style `CBMi…` ids are base64-decoded locally first, so some need no network at all.

### The modal never waits: bodies are extracted ahead of time and stored in SQLite

Three changes, in order of impact:

1. **A bug, not a missing feature:** `run_cycle()` called `CONTENT_CACHE.clear()` every 3.5 minutes,
   so every completed extraction was thrown away a few times an hour and the same article kept
   showing a spinner forever. Only derived caches (blurbs, reports, FA reports) are cleared now, plus
   bodies of articles that left the window.
2. **Pre-warming:** `warm_article_bodies()` walks the newest articles after boot and after every cycle
   and runs the extraction ladder in the background (concurrency capped at 6, so news translation
   still gets its share of the network).
3. **Persistence:** a new `bodies` table in SQLite (18+ `bodies`/`bodies→fa` rows) keeps bodies and
   their Persian translations across restarts; boot hydrates both caches (70 bodies on the last
   start). Verified: `/api/article/<id>` returns `pending:false` with 569–851 words and the paragraphs
   in place, and the modal paints them on the first frame.

The ladder itself was also trimmed: `r.jina.ai` now answers 403 and both raw proxies time out from this
network, so their timeout is 3s and `DEEP_BUDGET` is 6.5s (they still win when they work — they just no
longer eat the budget when they do not). Live rate over 12 newest articles: 10 full, 1 thin, 1
impossible (the publisher 403s every user agent, including Googlebot, and has no archive snapshot).
When nothing can be fetched the modal says so once, in one line, and offers the publisher link.

### Chart sizes, and two real bugs behind "the chart is tiny"

- Mounting the widget while the reports tab was still hidden sized the iframe to zero and nothing ever
  re-measured it → mounting now waits for a real box (and, for the same reason, tests
  `getBoundingClientRect()` instead of `offsetParent`, which is `null` for every element inside the
  fullscreen panel because its ancestor is `position:fixed`).
- All time frame buttons are gone from the panel (TradingView's own toolbar owns intervals); only
  «📊 نمودار تحلیلی» and «⛶ بزرگ‌نمایی» remain, both 34px with the app's pill radius.
- Inline footprint is now the old chart's: a 600px column beside a 665px reading column, widget
  558×600; in fullscreen the iframe measures 1562×857 — 98% × 86% of a 1600×1000 viewport.

### Filter surfaces: one console model, Persian labels everywhere

`filterbar` (search / labelled selects / credibility slider / a count pill, then horizontally
scrolling pill lanes for assets and topics) is now used by the feed and by the ideas tab. The calendar
kept its own English wording because the chrome translation map did not cover it — "All levels",
"Time of day", "Timezone", "Search", "Hide released" are all mapped now, and the map also rewrites
`placeholder` attributes ("event or currency — e.g. CPI, USD" → Persian), which the text-node walker
could never see.

### Small print, verified on the running page

- Sources are one button per section («🔖 منابع این بخش · ۳ خبر · نمایش منابع»); it opens a bounded
  380px pane with its own scroll, and closes again.
- The report pane scrolls independently (828px tall, 3186px of content) at 16px/2.05 with a
  `78ch` measure; the 24px/13.5px citation rows are now 13px/1.8 over 11px English line.
- `tools/check_dashboard_js.py` — 3 blocks, all parse. `pytest tests/ -q` — 13 passed.

### Blocked publishers: what was tried, and what the modal does now

About one article in five (Forbes, Bloomberg, AZƏRTAC-type sites) returns zero words. The resolver is
not the problem — 40/40 Google-News links unwrap — the publishers are. Measured against live URLs from
this network, every free route fails: plain fetch, Googlebot and Bingbot user agents, browser TLS
fingerprints (`curl_cffi` chrome/chrome124/safari17), `cloudscraper`, the origin's `/amp` and
`?amp=1`/`amp.<host>` variants, the Google AMP cache (`*.cdn.ampproject.org`), the Google Translate
proxy (`*.translate.goog`), `textise.net`, Bing's cache and news vertical, DuckDuckGo's HTML endpoint
(202 challenge), `r.jina.ai` (403), both raw proxies (timeout), Wayback (no snapshot yet). Bloomberg
does hand over a ~46-word free lead; AZƏRTAC hands over nothing at all — its 403 is the same for every
user agent, so it is an IP/JS-challenge wall, not a user-agent rule.

Instead of a dead end, the modal now does three honest things: it says «متن آزاد در دسترس نبود»
(never the old «۰ کلمه · ۰ پاراگراف», which read as a broken page), it puts the publisher link and a
full-text search where the body would be, and it ranks *related* stories by readability — items whose
body is already extracted sort first and carry a «📄 متن کامل» badge, with the section retitled «متن
کامل این‌ها آماده است — به‌جای خبر بالا بخوانید». Wire-story duplicates are de-duplicated by headline
(one Bloomberg story republished five times is not a reading list).

Two more pieces of the same fix: finished *empty* results are now stored in `bodies` too, so the first
click after a restart no longer waits ~15s only to learn there is nothing, and a lead-only body is
retried every 5 minutes instead of every 30 (`THIN_RETRY_SECONDS`).

What would actually unlock those publishers, if you want it: route the fetches through a proxy/VPN
(one env var, and everything blocked per-IP starts working) or a paid text API (ScrapingBee,
Firecrawl, Diffbot) as the last rung. Both are one rung in the ladder; neither is free.

## 17. News bodies: measured failure census, reddit solved, two switches wired (2026-09-26)

Rather than guessing which publishers are "blocked", the ladder was probed from this machine and the
stored bodies were counted: of 105 pre-fetched bodies **89 (85%) are full text** and 16 (15%) are
thin/empty — `robinhood.com` 4, `investing.com` 4, `bloomberg.com` 3, `reddit.com` 2,
`cryptorank.io` 1, `forbes.com` 1, `azertag.az` 1.

Class by class (all measured, not assumed):

- **Reddit — solved in code.** `reddit.com` answers plain clients with an ~8.4 kB JS interstitial
  (a hidden `<form name="solution">` plus a proof-of-work nonce) instead of the post. The "work" is
  the nonce doubled and reddit asks for two consecutive rounds before it sets the `rdt` cookie. New
  `_reddit_html()` rung solves it with two extra GETs and no browser: measured 8407 B challenge →
  554 kB post, post text extracted with `via=reddit-jsc` in 6.8s. This is 90 of the last 400 article
  links, so it matters far beyond those two thin bodies.
- **`investing.com` — rejected at IP/ASN level, not by UA.** Plain request *and* a real Chrome TLS
  fingerprint (`curl_cffi chrome124`) both return **403 with a 3-byte body** — that is an edge/intermediary
  refusal, not a CMS answer. Headers cannot fix it.
- **`bloomberg.com`, `nytimes.com`, `forbes.com`** — 403 + captcha wall (DataDome-class). Needs a real
  browser or a paid extractor.
- **`robinhood.com` news pages** — content exists only after client-side rendering; this environment has
  no browser automation installed (playwright/selenium/undetected all absent).
- **`r.jina.ai` (previously the strongest rung) is dead as a free service**: 401 without a key, 403 with a
  browser UA. The rung is kept and now carries `Authorization: Bearer $MOHMD_JINA_KEY` when that variable
  is set, so it comes back with one env var.
- **`azertag.az`** — 403 to every bot including Googlebot, and no Wayback snapshot.

Two switches wired for the two things that would close the rest (both env-only, nothing in the repo):
`MOHMD_PROXY` is copied into `HTTP_PROXY`/`HTTPS_PROXY` so *every* rung (including curl_cffi and
cloudscraper in `news_bypass`) reroutes at once, and `MOHMD_JINA_KEY` revives the reader rung. A SOCKS
proxy would additionally need `PySocks` in the venv; http(s) proxies work as-is.

## 18. FILTER MODEL 3 — one toolbar line, everything else behind one button (2026-09-26)

Two earlier builds of the filter surfaces were both based on keeping every control *visible*: first
three stacked boxes, then a console of labelled fields over two sideways-scrolling pill lanes. Either
way the feed and the ideas tab opened on a wall of chrome — search, four fields, a slider and two chip
lanes — before the first headline, and the report tab carried a 14-pill scroller across its top.

The model is now inverted. Each view opens on **one 38–50px line**:

- `⚙️ فیلترها` with a **live badge count** of the filters that are on (never a silent hidden state),
- the active filters as **removable chips** (max 4, then “+n فیلتر دیگر”; clicking one clears just it),
- the result count on the far side.

Every actual control — search, sort, kind, source, credibility slider, assets, topics — lives in the
`.fsheet` that drops out of that button, grouped under Persian section labels, with the assets and
topics as a **wrapping `fgrid`** instead of a sideways lane, a footer (“پاککردن همه” + “نمایش نتیجه”),
and the same `#id`s as before so no renderer had to change behaviour.

Measured live on port 5055 (1500×900), all five surfaces are a **single line**: feed 1185×50,
ideas 1185×50, reports 1202×50, calendar 822×50, ETF 1135×52. The report picker wraps into 3 rows
*inside* its sheet; the sheet's own height is clamped to the room left below its button
(`min(70vh, toggle-bottom…)`), so the footer is never off-screen, and it closes on outside click,
`Esc` and window resize.

Three real traps found while wiring it:

1. **`backdrop-filter` on the toolbar** would have made it a containing block for a `position:fixed`
   bottom sheet *and* localised the sheet's `z-index` — so the toolbar is a plainly positioned
   `z-index:40` element and the glass look comes from the background token alone.
2. **The mobile bottom sheet could never work as `position:fixed`**: `.view.active` carries a
   `transform`, which makes it the containing block for fixed children — the sheet landed 160 000px
   down the page. It is `position:absolute` at every width, with its own scroll.
3. **Dead CSS out-specifying the new layout**: the old `#repChips{flex-wrap:nowrap;overflow-x:auto}`
   (id) beat `.fgrid{flex-wrap:wrap}` (class), so the report picker refused to wrap inside the sheet
   until that rule was deleted.

Also fixed while testing: the ideas setters now sync their `<select>` (the toolbar chip names the
selected option, so a programmatic change used to leave it naming the old value), and an unavailable
idea timeframe is dropped rather than filtering the list to nothing while the select says “همه”.

One more real bug came out of that testing, in the app itself: **a click inside the sheet used to close
the sheet.** `setAssetFilter()` re-renders the chip grid, so the node the click landed on is detached by
the time the event bubbles to the document listener, `closest('.tb')` returns null, and the “click
outside” handler fired on every filter toggle. The hit is now recorded in the **capture** phase (while
the node is still attached) and detached targets are ignored — so you can turn on several filters in
a row without reopening the panel.

## 19. A single-file maquette for review — `tools/make_maquette.py` (2026-09-26)

`python tools/make_maquette.py` writes `mockup/mohmd-dashboard-maquette.html`: **the real page** — the
same stylesheet, markup and renderers — with every `/api/…` call answered from a JSON snapshot pulled
off a running server. That choice matters: a hand-redrawn mockup would drift from the product on the
next change, while this one cannot, because it *is* the product with frozen data and no backend.

- `window.fetch` is wrapped before the app's scripts run: exact route match first, then a match on
  `sym`/`tf`/`id`/`lang`, then an honest `{ok:false,error:'maquette'}` 404 so nothing hangs. Non-`/api`
  requests (the TradingView widget, the TradingView idea charts) still go to the network as usual.
- Verified with the Flask process **stopped**: 36 news cards, a 56-chip price marquee with two
  identical 4616px halves and `tkRoll 58s` running, 14 assets in the strip, the report with its four
  sources buttons, the Persian report, 16 idea cards, the calendar, the ETF board, and the article
  modal opening with text instead of a spinner.
- Snapshots are trimmed (36 articles, 10 archive, 24/36 calendar events, 100 candles per series rounded
  to 2–6 decimals, 16 ideas for BTC and 6 for the rest) so the file stays ~1.2 MB — mail/messenger
  sized — and the script prints the heaviest routes so the budget stays visible. It also **waits for
  the market cycle** before snapshotting (a freshly booted server has articles but no prices, which
  gave the first build an empty ticker) and **refuses to write** a snapshot missing `/api/data` or
  `/api/econ` rather than shipping a file that looks broken.
- A dismissable badge marks the file as a maquette so nobody mistakes the frozen numbers for live ones.
  Fonts, news thumbnails and the TradingView widget still need the internet, exactly like the app.

## 20. DESIGN LANGUAGE 3 — “Engraved Instrument” (2026-09-27)

A full visual rebuild of the single-file UI (`dashboard_html.py`): new token system, new markup
pass, new stylesheet, and the runtime pieces that make the interface read as one instrument. The
maquette (`mockup/mohmd-dashboard-maquette.html`) is regenerated from the same source, so the
review copy and the product cannot drift.

**The plan it was built to (DL3).** Warm graphite surfaces (`--bg #0B0A09`, `--panel #121110`,
`--panel-2/3/4` stepping up in warmth, sheets at `rgba(19,17,15,.96)`); hairlines in warm ivory
(`--rule` .10 / `--rule-2` .055 / `--rule-3` .20 / `--rule-strong` .30) instead of shadows on cards;
an ink ramp `#EFE8DD → #6F6659` (both superseded by DL4, below); copper stays *the* accent (`--cu #C8965D`, `--cu-hi #E6BE8B`,
`--cu-2 #A87A4A`, `--cu-txt #EBD2AC`) with washes and lines derived from it. Secondary semantics are
deliberate and muted: `--up #57B183` (verdigris), `--dn #D96A55` (oxide), `--warn #D8A93F`,
`--info #7FA6C9`, `--hol #8C93A6` — the old cyan/purple/gold/slate are deleted. One type scale
(`--t-xs 11.5 → --t-3xl 27`) with `--lh-tight/--lh/--lh-fa`, tabular numerals, no monospace-as-decoration
and no tracked ALL-CAPS eyebrows. Spacing `--s1 4px … --s8 40px`, radii `--r1 3 / --r2 6 / --r3 9 / pill`,
three durations on one easing, and shadows reserved for popovers and modals.

**Shell and views.** A 56px topbar with a 34px engraved ticker under it, and a 232px index rail
(60px when collapsed) that carries a 2px copper edge bar and the three authored groups
(پایش بازار / سیستم و سلامت / مدیریت و پیکربندی) with live counts and a persisted collapse state.
Dense lists are one toolbar line → lead story → a rules-bordered grid; the report is a paper-toned
reading column (76ch, 15px/2.05) with a sticky chart and fear-and-greed rail. The economic calendar is
a full-tab LTR island (`#view-calendar{direction:ltr}` / `.cal-board`), and — as decided — its
*content* stays 100 % English: table head, week navigator, sessions clock, hero, explainer and
countdowns all read `21 Sept – 27 Sept`, `in 1d 19h`, `0 events`. Only the sidebar entry
«تقویم اقتصادی» is Persian, like the rest of the menu (§14); the copy that claimed a Persian
calendar chrome was wrong and has been corrected here.

**Chrome polish (one pass, no retrofits).** A single IIFE walks every text node the UI renders:
emoji in chrome become sprite glyphs (50+ inline symbols, `ic()` / `assetIc()` / `topicIc()`) and the
middle-dot the old build strung through its meta lines becomes a hairline separator (`.vr`). Prose is
skipped by design — article bodies, news cards, report text, the Telegram message and its preview keep
exactly what was written. Asset marks are code-derived (coin / ingot / drop / swap / chart / pulse),
so no emoji from the registry reaches the interface; registry emoji and English source names stay in
the data, and the UI falls back to a built-in Persian name table when a stored name has no Persian
letter in it (fa:"Bitcoin" renders as «بیت‌کوین», data untouched).

**CSS as a build artifact.** The stylesheet is authored as four files — `tools/theme_v3_a…d.css`
(tokens/base/icons/forms/buttons/shell · chips/toolbar+sheet/panels/feed/modals/toast ·
reports/chart/ideas/calendar/ETF · telegram/palette/a11y/print/responsive) — and installed into the
`<style>` block by `python tools/splice_theme.py tools/theme_v3_{a,b,c,d}.css`. Edit the CSS there and
re-splice; the stylesheet shrank 124.8 KB → 83.6 KB (1476 lines) with a single `:root` and no
duplicate tokens.

**Verification.** `pytest`: 13 passed (`test_dashboard_ships_dl3_layers` now asserts the DL3 marker,
a single `:root`, and that `--bg:`/`--cu:`/`--ink-3:`/`--r3:` are declared exactly once).
`tools/check_dashboard_js.py` parses all four inline script blocks. Live DOM sweeps: 12/12 views render
with content, the command palette lists 29 destinations, the calendar board renders its English
header and rows, the citation rows in the report carry sprite icons, and the maquette was re-verified
**with the Flask process stopped** (badge present and dismissable, ticker marquee, 12 views, LTR
calendar, hairlines).

**Not built (from the optional list):** report compare mode, browser push notifications, first-visit
guidance. **Not verifiable offline:** the TradingView ideas grid and the live chart need the network —
the section that renders them is unchanged apart from styling.

---

## 21. DESIGN LANGUAGE 4 — measured contrast, picture and touch (2026-09-27)

A refinement pass over the DL3 build (same four `tools/theme_v3_*.css` files, same splice pipeline):
fix what measured badly, then let the material carry the design. Backups of everything it touched are
in `backups/*.pre_uux_20260927_115425.bak` plus `backups/snapshot_pre_uux_20260927_115416.zip`.

**Ink ramp re-solved, not patched.** `--ink-3 #9A9083 → #B2A798` and `--ink-4 #6F6659 → #918779`:
the old pair measured 5.28 and 2.94 on `--panel-3` (the bottom step failed outright), the new pair
measures 7.01 and 4.70 with a 1.39–1.49× step between every rung — measured values are written into
the comment in `theme_v3_a.css`. `--doc:#141210` is new, so the report reads as paper against the
shell, and `box-shadow:var(--inset-hi)` gives `.panelbox` / `.lead-card` / `.ncard` / `.idea-card` /
`.etfgroup` an engraved edge instead of a floating one.

**The picture gets in.** The lead story renders its 21:9 banner (`.thumb`, image + proxy fallback +
pre/post wash), and every thumbnail shares one duotone filter —
`grayscale(.50) sepia(.20) saturate(1.30) contrast(1.05) brightness(.82)` — with hover/focus restoring
the original and print switching it off. The news grid went from an accidental two columns to a real
four: `grid-template-columns:repeat(auto-fill,minmax(306px,1fr))` → 317px cards at 1357px.

**One language per surface, enforced.** `renderReport` stamps `data-lang="fa|en"` on `.rep-doc`;
`[data-lang="en"] .rep-sec, .rep-toc` then run `direction:ltr; text-align:left`. Verified live on BTC:
English → `1. Market Overview` / ltr / left, Persian → `۱. مرور بازار` / rtl / start. The calendar is
fully English as decided (§14, §20), `#view-calendar` is `direction:ltr`, `.cal-info` has a min-height
so the toolbar no longer jumps, and the event counter reads a proper singular (`0 events`).

**Touch and semantics.** Under `@media (pointer:coarse)` the star/delete buttons grow to 44×44,
`.cal-info` and every chip/button to 44px (desktop tightens star/delete to 24×24); the 12 nav buttons
carry `aria-controls` and the 12 views `role="tabpanel"` + `aria-labelledby`; the filter-sheet search
label is جستجو; `.topbar-telemetry` is forced LTR. The TradingView widget was aligned to the tokens
(`backgroundColor #121110`, `gridColor rgba(236,224,206,.07)`).

**Emoji audit.** Every emoji left in `dashboard_html.py` is deliberate: a chrome-polish input (the
IIFE's `MAP` swaps it for a sprite, and the `MutationObserver` covers dynamically injected nodes), a
text symbol (`✓ ✗ → ⇅ ↗ ✕ ↑ ↓`), or prose kept on purpose (the Telegram template and previews).
No emoji reaches the chrome from the registry.

**Verification.** `splice_theme.py --check` clean (1476 lines / 85591 bytes), `check_dashboard_js.py`
4/4 script blocks parse, `pytest` 13 passed, maquette regenerated (`mockup/mohmd-dashboard-maquette.html`,
70 paths, ~1.15 MB) with every marker confirmed in it. Live sweeps: ink-1…ink-4 measure ≥4.5:1 on every
text-bearing surface (only exception: `--ink-4` on `--panel-4`, which holds no text), `smallTargets: []`
in all 12 views, and the 7 hits a naive contrast script still reports are false positives — six `.btn`
rows whose effective background was computed without the gradient behind them (hand-checked 10.68 and
7.04) and one `span.sep` that is transparent at `font-size:0`.

---

## 22. Full-text extraction — three dead rungs (2026-09-27)

The article modal kept showing «متن استخراج‌شده کوتاه است» — or nothing at all — for whole classes
of sources. Measured on the newest 60 articles *before* this pass: 11 under 120 words, **4 with zero
words** (`via=none`), median body well under the warning threshold. After: **0 empty**, 5 thin (all
reddit image posts, which genuinely have no prose), median 453 words, 3.0 s per article.

**What was actually broken.**

1. **The strongest rung was dead.** `r.jina.ai` answers 403 — a Cloudflare challenge — to the app's
   own `HEADERS` UA (and to most Chrome-looking UAs), while the crawler UA passes. `_jina_reader_text`
   now sends a Googlebot UA and retries once on 403/429: measured 3/3 on the hosts that 403'd every
   other rung (cryptopotato 576 → 453 parsed words, ccn 1168, robinhood 342).
2. **The JSON-LD pass could never run.** `_parse_article_html` decomposed `<script>` *before* calling
   `_jsonld_body(soup)`, so `articleBody` was never reachable; and the last-resort `<p>` sweep
   unconditionally overwrote whatever it found, discarding a JSON-only body. Both fixed (the sweep now
   only replaces text when it has more of it).
3. **SPA payloads were invisible.** The article often ships inside `__NEXT_DATA__` / `self.__next_f` /
   `__INITIAL_STATE__` rather than in the DOM. `_payload_paragraphs` reads them with two tiers — the
   keys a CMS uses for the article itself (first hit per key, so a *related articles* list of the same
   field never leaks in), then the shape of the document when tier 1 stays thin. The Robinhood
   prediction-market page went 28 → 251 words from `event.longDescription` alone.
4. **Reddit's body lives behind an XHR.** The solved session now reads the post's `.json` endpoint
   (selftext + comment tree); pullpush.io mirrors selftext that moderation has `[removed]`; a post with
   no text of its own gets its top comments, and a link post is followed to the article it points at.
   The flagged thread went 22 → 1456 words.
5. **Reader-text and paragraph hygiene.** `_parse_reader_text` strips images before links, drops lines
   that still hold a link (the page's nav used to arrive as a paragraph of image labels) and rejects
   low-letter lines; `_looks_like_paragraph` rejects bare media URLs — the exact shape a reddit image
   post produces. The modal's yellow warning no longer blames a paywall for every short body: a reddit
   post or a one-line market page gets an honest ℹ️ note instead.

**Verification.** `pytest` 16 passed (3 new: JSON-LD survives the script strip, `__NEXT_DATA__` body is
extracted, bare media URLs are rejected), `check_dashboard_js.py` 4/4, maquette rebuilt, server
restarted, and all three failure classes confirmed in the live modal (251 / 355 / 1456 words where the
screenshot showed 28 / 0 / 22).

---

## 23. FXEmpire's outbound sources — roster completion (2026-09-27)

The user supplied FXEmpire's own 27-source list. 21 were already in `SOURCES`; the six that were
missing are now added with feeds that were discovered and verified live:

| source | feed | items | in the 24h window | full text (`/api/article`) |
|---|---|---|---|---|
| Coin Tribune | `www.cointribune.com/feed/` | 10 | 8 | 664 w, direct |
| Invezz | `www.invezz.com/feed/` | 15 | 1 | 742 w, direct |
| Unchained | `unchainedcrypto.com/feed/` | 10 | 0 (newest is 35.2 h old) | 381 w, direct |
| DailyCoin | `dailycoin.com/feed/` | 8 | 0 (newest is 25.5 h old) | 487 w, direct |
| Coinpaper | `coinpaper.com/feed` | 20 | 8 | 297 w, direct |
| Cryip | `cryip.co/rss` | 25 | 7 | 442 w, bingbot |

`PUBLISHER_TRUST` entries went in with them, and `load_config()` already defaults every new builtin
source to enabled, so no settings migration was needed.

**Two real scraper bugs the end-to-end run surfaced.**

1. **`status["http"]` was never set on an HTTPError**, so `_classify_failure` saw `http=None`, called
   every 403/404/429/415 a generic `"exception"`, and *every* status-driven rung of `_fetch_one`'s
   ladder — the 429 backoff, the 403 reader-UAs, the 404 → Google News mirror — was unreachable code.
   The response code is now read off `ex.response.status_code` first.
2. **The Google News lifeline queried a window Google News does not have.** `_mirror_url` built
   `when:48h site:host` (valid windows are `1h/1d/7d/30d`) and got zero entries back, so a dead feed
   recovered nothing. The bare `site:host` query returns items, and a mirror fetch now strips the
   "- Publisher" suffix and scores the real outlet, exactly like a search feed.

Plus one tuning change: cryip's edge answers a flaky `415` at random while the same URL returns a
perfect feed a second later, so 415 joined the backoff rung (5 attempts now) — measured 3/5 and 2/3
on rapid retries, and 1/1 in the production cycle.

**Verification (end to end).** Production cycle: **112/113 feeds OK** (only `cryptonewsz` timed out,
pre-existing), the six new feeds returned 10/15/10/8/20/25 items, 25 of their articles are in the live
feed, and `/api/article/<id>` returns 297–742 words for every sampled source — with the modal chip
showing `۴۴۲ کلمه · ۷ پاراگراف` for Cryip, a host that blocks direct fetches. `pytest` 16 passed,
`check_dashboard_js.py` 4/4.

---

## 24. Requested UI adjustments (2026-09-27)

Seven changes from one review pass, each verified in the live DOM:

1. **Brand line gone** — `.brand-desc` («مرکز فرمان هوش بازار») removed; the topbar now reads as the
   wordmark plus the live pill only.
2. **Refresh is English** — the topbar button, its two states (`Refresh` / `Refreshing…`), and the
   command-palette row (`Refresh now`) now match the rest of the topbar's terminal vernacular.
3. **No TradingView link in the calendar explain** — the «مشاهده در تریدینگ‌ویو» button left
   `.cal-doc-foot`; the local, rule-based disclaimer stays.
4. **Timezone defaults to Tehran** — the select marks `Asia/Tehran` selected, and the fallback in
   `calTz()`, the toolbar's “reset timezone” chip and `resetCalFilters()` all agree on it (previously
   all three said UTC). The calendar stays English/LTR, as decided in §14/§20.
5. **Currency is a multi-select** — the single-value `#calCountry` dropdown became a row of tick-boxes
   (`.ccy-list` / `.ccy`), one per currency, rebuilt only when the data's currency set changes; empty
   means “all”, `clearCalCcy()` backs both the toolbar chip and the filter reset. Measured on 30 Sep:
   **119 events → 39 (USD) → 79 (+EUR) → 88 (+GBP) → 119 restored**.
6. **Archive boxes are six to a row** — `.archgrid` is now `repeat(6, minmax(0,1fr))` instead of
   `auto-fill,minmax(320px,1fr)` (which capped at four), stepping 4 / 3 / 2 / 1 down the existing
   1400 / 1180 / 980 / 780 breakpoints. Computed style in the live view: **6 tracks**.
7. **Direction label off the idea image** — `.idea-thumb .idea-dir` is gone from the card markup and
   the stylesheet; the timeframe stamp stays on the chart picture (24/24 thumbs) and the direction
   still sits in the card body (24/24 `.idea-top .dir`).

**Verification.** `splice_theme.py --check` clean (1501 lines / 87098 bytes), `check_dashboard_js.py`
4/4, `pytest` 16 passed, maquette rebuilt (70 routes, 1174 KB), server restarted, live DOM sweeps
above.

## 25. Paywall republishers — screening batch (2026-09-27)

Two research lists (~100 outlets that re-run Bloomberg / Reuters / FT / WSJ copy for free) were
screened against fixed criteria: English, free, market-focused, a real parseable RSS feed, and
output that survives `is_relevant()` + `validate_article()`.

**Added — 12 feeds** (all verified 125/125 OK in a full roster run):

| key | outlet | feed | trust |
|---|---|---|---|
| `et-markets` | Economic Times Markets | markets RSS | 0.72 |
| `business-standard` | Business Standard Markets | markets desk RSS | 0.72 |
| `livemint` | LiveMint Markets | `/rss/markets` | 0.72 |
| `businessline` | Hindu BusinessLine | feeder RSS | 0.70 |
| `dawn-business` | Dawn Business (PK) | `/feeds/business` | 0.74 |
| `euronews-biz` | Euronews Business | `?level=vertical&name=business` | 0.72 |
| `finwire` | Finwire | `rss.xml` | 0.70 |
| `marketnews` | Market.News (AI aggregator, cites originals) | `rss.xml` | 0.66 |
| `thestreet` | TheStreet | `.rss/full/` | 0.70 |
| `ibd` | Investor's Business Daily | `/feed/` | 0.66 |
| `gulfnews` | Gulf News | `/feed/` | 0.66 |
| `hurriyet-dn` | Hurriyet Daily News | `/rss/news` | 0.64 |

Yield measured at the default 72h window: **63 articles**, best contributors ET (11), LiveMint (9),
Dawn (9), Market.News (11). Section feeds were preferred over home feeds wherever the site exposes
one (Dawn Business, Euronews Business, the three Indian market desks) so general-news noise never
enters the pipeline. `PUBLISHER_TRUST` gained a matching block so Google-News-attributed headlines
score at outlet level.

**Screened OUT, with reasons** (recorded in a comment beside the batch):

- *Yonhap / Korea Herald / Korea Times* — general wires whose front page was 80% Asian Games medal
  tables; after the sports gate below, measured yield was **0 of 60 raw** (politics + chip-industry
  stories outside the tracked assets). Fetch cost with no payoff.
- *Business Insider* (no markets feed exists — `custom/all` yielded longevity/nursing-home stories)
  and *Business Day NG* (stale) — nothing usable.
- *Moneycontrol, NDTV Profit, CNBC-TV18, Business Recorder, The News, Profit.pk, DailyFX, FXStreet,
  IG, Zawya, Al Arabiya, Arab News, This is Money, StreetInsider, ForexFactory, FinanceFeeds…* — no
  parseable RSS at any probed path, or non-English.

**Three gate fixes in `sources.py` came out of the screening** (all `pytest` 16 green):

1. `SPORTS_NOISE_PATTERN` — «S. Korea captures gold in women's sabre» used to match XAU and sail in
   through the `assets` shortcut. Sports/medal headlines are now rejected before anything else;
   measured: **0 sports leaks** in the full 868-article roster run.
2. `HARD_NOISE_PATTERN` — stock-picking SEO («stocks to buy | Target, SL», «buy points», «stock
   picks»), IPO/DRHP filings, dividend and insider boilerplate are rejected *even when the headline
   names an asset* (the old code skipped the noise screen whenever `assets` was non-empty). The
   softer `NOISE_PATTERN` still only applies when no asset is named, so «gold price target $4,000»
   survives — it contains «price target».
3. **Headline-first relevance** — `is_relevant()` now requires the asset hit *in the headline*, or a
   `RELEVANCE_PATTERN` match on the text; a stray «oil» buried in a summary no longer promotes an
   unrelated story to WTI. `RELEVANCE_PATTERN` gained the commodity/index vocabulary this needs
   (crude, Brent, OPEC, natural gas, Nasdaq, Dow Jones, S&P 500, Wall Street, Nifty, Sensex) and
   lost the bare `\bexchange\w*\b` that was matching «red blood cell exchange». `scraper.py` mirrors
   it for tagging: title assets first, summary assets only as a fallback.

**Verification.** full roster `scrape_all()` → **125/125 feeds OK, 868 articles (63 from the new
sources), 0 sports leaks**; `pytest` 16 passed; `check_dashboard_js.py` 4/4; `splice_theme.py
--check` clean (1501 lines / 87098 bytes).

## 26. MASTER-file screen — crypto_sources_MASTER.md vs the roster (2026-09-28)

The user supplied `crypto_sources_MASTER.md` (450+ sources in 18 categories). The roster already
held most of its RSS-bearing news sites (CoinDesk, CoinTelegraph, The Block, Decrypt, Blockworks,
Bitcoin Magazine, Bitcoin.com, CryptoSlate, BeInCrypto, CoinGape, Bitcoinist, NewsBTC, DailyHodl,
ZyCrypto, CryptoPotato, DailyCoin, CoinJournal, CoinPedia, U.Today, AMBCrypto, Cryptonews,
Watcher.Guru, Crypto Briefing, Finbold, The Tokenist, NFT Evening-adjacent, The Defiant, Rekt
News, DL News, Messari, BitMEX Research, Coin Metrics, Unchained, r/CryptoCurrency, r/Bitcoin,
r/Ethereum, Kitco, Mining.com, Trading Economics-equivalents…). The **delta** was screened the
same way as section 25: probe for live RSS → 72h freshness → `is_relevant()` pass-rate, then a
`scrape_all()` yield check.

**Adopted (14 feeds added to `SOURCES`, roster 125 → 139):**

| Key | Feed | Kind | Probe result |
|---|---|---|---|
| `nftevening` | NFT Evening | crypto | 100 items, 15/15 relevant |
| `bankless` | Bankless | crypto | 5 items in 72h, 13/15 relevant |
| `a16zcrypto` | a16z Crypto | research | 30 items, RWA/SEC policy analysis |
| `blockchainrep` | Blockchain Reporter | crypto | 10/10 fresh in 72h, 9/10 relevant (own research) |
| `bitcoinke` | BitcoinKE | crypto | 10/10 fresh, 10/10 relevant (own research — African crypto desk) |
| `kingworldnews` | King World News | metals | 6 items in 72h, gold-focused interviews |
| `goldseek` | GoldSeek | metals | live at `news.goldseek.com/newsRSS.xml` (the MASTER file's URL was wrong) |
| `financemagnates` | Finance Magnates | macro | 9 items in 72h, FX/industry wire |
| `actionforex` | Action Forex | macro | 20/20 fresh, gold/FX technical analysis |
| `rektcapital` | Rekt Capital (substack) | research | live, cycle analysis |
| `pomp` | The Pomp Letter (substack) | research | live, BTC + macro |
| `cobie` | Cobie (substack) | research | live, market commentary |
| `tokenunlocks` | Token Unlocks (substack) | research | live, supply-unlock coverage |
| `reddit-defi` | r/DeFi | social | 9 items in 72h of real discussion |

All 14 got `PUBLISHER_TRUST` entries (substacks/research 0.68–0.82, tier-3 news 0.62–0.64,
Reddit 0.50 sequential like the other subs).

**Rejected with evidence (from the same file + own research):** wublock.com/feed and
wublockprint.com (connection timeouts/dead host), weekinethereumnews.com (SSL error), milkroad,
delphidigital.io, galaxy.com/research, goldtelegraph (HTTP 200 but **zero** feed entries),
research.binance.com (HTTP 202, empty body), coinbase.com/blog/rss and goldsilver.com (403),
paradigm.xyz, mechanism.capital, defireports.substack, gold.org, bullionvault, miningweekly
(404), azcoinnews (503), crypto-news.land, coinpath.io (timeouts), r/CryptoTechnology (429
throttling), r/altcoin (pinned-post only). The Daily Gwei, Lyn Alden, Crypto Trader Digest are
live but weekly/monthly cadence — their 72h pipeline yield is ~0, so they were left out for now.

**Verification.** new-14 `scrape_all()` → 14/14 feeds OK, **48 articles** (265 raw → 48 kept,
190 scored out incl. 166 stale); full-roster sanity + `pytest` 16 passed; `check_dashboard_js.py`
4/4; `splice_theme.py --check` clean; server restarted with the new roster and `/api/data` +
`/api/econ` answer 200; maquette rebuilt (1139 KB, 70 routes). Backup:
`backups/sources.py.pre_master_20260928_*.bak`.

## 27. Social popularity gate — Reddit posts need 2000 upvotes (2026-09-28)

User request: **"یه فیلتر برای شبکه های اجتماعی منابع بزار — خبرهایی که زیر ۲۰۰۰ تا لایک داره رو
اصلا نیارش"** (filter the social sources: never show posts with fewer than 2000 likes).

**Why a bridge was needed.** Reddit's RSS carries *no* score field, and every official JSON
endpoint (`*/new.json`, `api.reddit.com`, `old.reddit.com`) answers **403/429** to this server.
Upvote counts are therefore recovered from the **Arctic Shift** public archive
(`arctic-shift.photon-reddit.com/api/posts/ids?ids=t3_…`) — verified live: a 140h-old post
reports `score=18, comments=5` while a 15h-old one reports `score=1`, i.e. *current* counts, not
ingestion-time snapshots (pullpush.io was tested first and rejected for exactly that reason:
it freezes `score=1` forever).

**Pipeline.**
- new module `reddit_scores.py`: `attach_scores(articles, min_score, min_comments,
  max_age_hours)` extracts the post id from each RSS link, batches the ids (25/request,
  0.4s pause) and stamps `reddit_score` / `reddit_comments` onto the article dicts.
- **Cache** `.reddit_scores.json` (gitignored): a score younger than **6h** is trusted; an
  archive *miss* (post only minutes old) is parked for **10min** before re-probing, so one
  cycle cannot hammer the API; re-fetch is bounded by `max_age_hours` (stale-bound posts
  never trigger a request).
- `scrape_all()` gained `social_score_min` / `social_comments_min` parameters: social-kind
  articles are scored right after the fetch phase and below-minimum posts are **dropped
  before validation** (they count in `stats.rejected`). Policy is **fail-closed**: an
  unreadable score (archive lag, API down) drops the post; the next cycle re-probes and a
  post that genuinely earns ≥min re-enters the feed.
- `app.run_cycle()` passes the settings through; `api_settings` accepts `social_score_filter`
  (master switch), `social_score_min`, `social_comments_min` and **re-scores what is already
  in memory** (`refilter_state`) so saving takes effect immediately; the choice persists in
  `settings.json` and survives restarts.
- UI: the feed filter sheet has a **«حداقل لایک شبکه‌های اجتماعی»** checkbox + minimum-upvote
  field (default 2000); social cards that carry a score show a `▲ N` badge; `_ser_article`
  ships `reddit_score`/`reddit_comments` and `/api/data.rules` exposes the gate state.

**Verification.** `pytest` **20 passed** (4 new: id extraction, gate on/off, min-comments —
suite stays network-free by stubbing `fetch_scores`); full boot cycle on 139 sources:
2966 raw → 516 articles, social gate logged *"33 posts below the minimum"*; settings POST
→ `settings.json` shows `social_score_filter: true, social_score_min: 2000`; restart keeps
the gate on; `check_dashboard_js.py` 4/4; `splice_theme.py --check` clean.

**Known limits.** r/* subreddits intermittently 429 (their feeds still work most cycles);
the maquette snapshot keeps a demo `social_score_filter` value but has no live archive
calls — the demo feed simply renders what the snapshot captured.

## 28. Cross-asset correlation matrix (2026-09-28)

New view **«ماتریس همبستگی کلان»** (`#nav-correlation` → `#view-correlation`) — a rolling
Pearson correlation heatmap over ten core assets: **BTC, ETH, SOL, XRP · XAU, XAG, WTI ·
DXY, SPX, VIX**. Lookbacks: **24h (hourly), 7D, 30D, 90D (daily)**, switchable in one toolbar line.

**Math (`indicators.py`, pure & tested).** `pct_returns()` builds
`Rₜ = (Pₜ − Pₜ₋₁) / Pₜ₋₁` (skipping rows whose previous close is missing/zero instead of
faking a 0.0 return), `pearson()` returns r or `None` when it is mathematically undefined
(<3 paired points, zero-variance series), and `correlation_matrix()` returns a
symmetric matrix with an exact 1.0 diagonal plus the observation counts per asset.

**Endpoint.** `GET /api/correlation?window={24h|7d|30d|90d}[&force=1]` (app.py) reuses the
daily Yahoo history already held in `STATE['market']` and pulls Yahoo chart data directly for
the hourly window (`60m`/`5d`) — ten series fetched in parallel, cached for **15 min**
(`CORR_CACHE`), and the payload always carries: the 10×10 grid (each cell `{r, est}`), the
asset list with Persian/English names and kind, per-asset sample counts, `missing`,
`source` (`live` | `mixed` | `fallback`), the strongest direct and inverse pair, and the
four window labels.

**Fallback, and why it is mathematically sound.** If a series cannot be fetched (or the
whole computation throws) the grid is filled from `_corr_fallback_matrix()`: correlated
returns generated from a **three-factor model** (risk appetite / dollar / real-rate–energy)
with fixed loadings per asset — DXY inverse to gold and crypto, SPX direct with crypto,
VIX inverse to SPX — so the matrix is positive semi-definite by construction rather than a
hand-typed table, and the seed is fixed so the demo never flickers. Cells that come from
the model are flagged `est` and rendered with a dotted underline + «تخمینی» in the detail
card; the source pill says «داده زندهٔ بازار» / «ترکیبی» / «مدل جایگزین».

**UI (DL3 «Engraved Instrument»).** A semantic `<table role="grid">` — chosen over a bare
`display:grid` of divs so both axes can stay `position:sticky` inside the scroll container
while rows/columns keep real header semantics (`scope`, `aria-labelledby`) — with a
copper-bordered diagonal, Persian labels, `font-variant-numeric: tabular-nums` and
`direction: ltr` on every figure, insight chips (strongest direct / strongest inverse /
estimated count / recompute), and a sticky detail card showing the pair, the r value with a
signed bar, the verbal category and a one-sentence reading — pair-specific copy for the
classic relationships (DXY↔XAU, BTC↔ETH, SPX↔VIX, WTI↔DXY …) and a band sentence otherwise.

**Heat bands (per spec).** Exactly three zones: **≥ +0.50 verdigris** (`--up`),
**−0.49 … +0.49 graphite wash** (`rgba(236,224,206,.05)`), **≤ −0.50 oxide** (`--dn`). Inside
the two strong zones the alpha is written inline by `corrTint()` (`0.12 → 0.42` as |r| goes
0.5 → 1.0) so the grid still reads as a gradient without inventing a fourth colour zone;
the diagonal is transparent with a copper hairline and shows `۱٫۰۰`.

**Hover relationship tooltip.** `corrTipShow()` fills a fixed-position card (`role="tooltip"`,
never clipped by the scroll container) with the pair in Persian + ticker, the signed r in heat
colour, the verbal category, the one-sentence analytical reading and an «تخمینی» flag for
model-filled cells; it is placed above the hovered cell when there is room and clamped to the
viewport otherwise. It is driven by `mouseenter`/`focus` (keyboard users get the same card),
and dismissed on `mouseleave`, on matrix scroll, on click (the pinned card takes over) and on
Esc. The transition was deliberately removed: an animated opacity can strand a tooltip at 0 in
any environment that does not tick the compositor — the card is readable the instant the
pointer lands.
Keyboard: arrows roam the grid (mirrored for RTL so the focus ring follows the eye),
Home/End jump, Enter pins a pair, Esc unpins — the untouched cells keep `tabindex="-1"`
(roving tabindex), and the whole grid is reachable from the region's own tab stop.
Responsive: below 1100px the detail card drops under the grid and the matrix keeps its
sticky row header while scrolling horizontally (verified at a 414px viewport:
`scrollWidth 720 > clientWidth 335`, header offset unchanged during scroll).

**Maquette.** `make_maquette.py` snapshots all four windows and now matches on the `window`
query param, so the demo's timeframe switcher really switches (verified: 90D in the offline
file → 90 observations from the snapshot). 74 routes, 1182 KB.

**Verification.** `pytest` **25 passed** (5 new: returns/edges, Pearson perfect + undefined,
matrix symmetry/diagonal/min-points, endpoint contract incl. the exact ten-asset order and
mirrored cells, bad-window 400); `check_dashboard_js.py` 4/4 (2868 lines);
`splice_theme.py --check` clean (1597 lines / 93399 bytes); live `source: live` with
30D `BTC/ETH +0.93`, `XAU/DXY −0.59` — i.e. the real-world signs, measured, not asserted;
the in-browser passes covered hover highlighting (4 header cells), the hover tooltip
(`بیت‌کوین (BTC) ↔ اتریوم (ETH)` · `+۰٫۹۳` · «همبستگی مستقیم بالا» · one-sentence reading,
positioned above the cell, fully inside the viewport, dismissed on leave/scroll/click),
click → detail (`طلا (XAU) ↔ شاخص دلار (DXY)`, −۰٫۵۹, «همبستگی معکوس قوی»), arrow-key roaming
with exactly one roving tab stop, Esc unpin, window switching (24h → `obs 24`, hourly), the
exact heat classes (`BTC/ETH` → `is-pos` + `rgba(87,177,131,.38)`, `BTC/XAU` at +0.12 →
`is-neutral` graphite, `XAU/DXY` → `is-neg` + `rgba(217,106,85,.176)`), and a crafted `mixed`
payload rendering 18 estimated cells with the «تخمینی» chip.

**Note on the icon sprite.** `#i-grid`/`#i-swap` are now declared exactly once (an earlier
duplicate pair was removed): duplicate IDs are invalid markup and the browser silently keeps
the first definition, so the nav/heading would have rendered while the second copy stayed dead.

## 29. AI narrative radar — storyline clustering in the browser (2026-09-28)

New view **«رادار روایت‌ها»** (`#nav-narratives` → `#view-narratives`). The feed is linear
and asset-tagged; this groups the *same* articles into macro storylines and measures their
momentum. No endpoint was added: everything runs over `DATA.articles` + `DATA.archive` the
page already holds, so the maquette clusters offline too.

**Clustering (`dashboard_html.py`, pure client-side).** `NARR_RULES` holds eight storylines
— Middle East energy / Hormuz, hawkish Fed & sticky inflation, institutional ETF flows,
tokenization & banking rails, regulation, leverage & liquidations, precious metals,
institutional accumulation — each a lexicon of word/entity patterns with an asset map and a
score threshold. A hit in the title scores 3, in the summary 1, and owning one of the rule's
assets scores 1 more; **a story must also clear two distinct patterns**, so a single generic
token (“Fed”, “gold”) cannot drag the whole feed into a narrative. One article can belong to
several storylines by design.

**Metrics.** Volume (articles inside the active window, 24h or 48h), velocity (articles per
hour over the last 6h, falling back to the whole window), acceleration (the last 6h bucket
against the previous one; a brand-new story is capped at 2× instead of infinite), sentiment
bias from a counted bullish/bearish lexicon (`(bull − bear) / (bull + bear)`), mean
credibility, and a status derived from all of it: **در حال شکل‌گیری / در اوج / در حال سرد
شدن**. Cards sort by volume plus a 4× weight on the last six hours.

**UI.** One card per storyline: rank, Persian title + English subtitle, status pill, a
one-sentence reading built *from the card's own numbers* (sample, last-6h rate, bias,
impacted assets, two headline titles), a four-metric strip, a diverging sentiment gauge
(bull vs bear widths), asset badges, a four-item chronological mini timeline, and a footer
that opens the **storyline drawer** listing every clustered article with its match score,
source, age and ▲ Reddit score. Clicking a drawer row opens the article modal itself.
Status chips filter the grid and carry live counts (all / emerging / peaking / cooling).

**Accessibility.** Cards are `role="button"` with a Persian `aria-label` (title, status,
volume) and Enter/Space activation; the window group is a real `radiogroup` with roving
`tabindex` and Home/End/arrow roaming (mirrored for RTL); the drawer is a dialog that takes
focus on open and returns it to the card on close, and Esc closes it.

**Verification.** Live feed clustered in **5 ms**: 8 storylines over a 24h window out of
850 articles, 196 matched (**23% coverage**); the co-occurrence gate is what keeps one
buzzword from dragging the feed in — the same pool matches 18% on a single-token rule.
Browser checks: 8 cards (volumes 59/54/49/18/15/15/5/4), gauge + timeline + badges present,
`≡/✦/▲/▼` status chips counting correctly, 48h switch → 7 storylines / 118 matched, cooling
filter → exactly the one cooling card, card click → drawer with 11 rows (scores 3…5),
drawer row → `artOverlay` opened for that article id, Esc closes. Offline maquette verifies
4 storylines from its 36-article snapshot.

**A bug the new test caught.** Every lexicon pattern was originally written without the
`/i` flag, so `\bfed\b`, `\betfs?\b`, `\bcpi\b`, `\bopec\+?\b` … never matched a headline
that capitalises them — the radar was silently reading only the lowercase half of the feed
(6 storylines / 9% coverage, with ETF, RWA and regulation structurally missing).
`tests/test_dashboard_logic.py` (below) pins the flag down.

## 30. Historical price reaction inside the calendar explainer (2026-09-28)

The calendar already showed forecast vs actual; it did not say what the number *did* to the
tape. `openCalDoc()` now appends a collapsible **«واکنش تاریخی قیمت»** section
(`calReactHTML` → `#calReactBody`) with a reference dataset of last-four-release reactions
for the indicators desks actually trade: US CPI, PPI, NFP, ADP, FOMC rate decision, weekly
jobless claims, EIA crude inventories, retail sales, GDP, ISM/PMI and the ECB rate decision.

**How a row is built.** Directional bias per pairing is encoded as `dir` — the sign the
asset takes when the print lands **above** forecast (a hot CPI lifts DXY and pressures gold,
crypto and equities; a crude build pushes WTI down; a claims miss lifts gold). Typical moves
at minute 15 and 60 come from `m15`/`h1`, the surprise magnitude from `typ.sd` with a
`typ.rel` share of the consensus so a fixed delta cannot break on series of a different
scale (jobless claims run in the hundreds of thousands, continuing claims in the millions),
and the 15-minute leg is front-loaded (`CAL_REACT_FRONT`, 35% of the path) because a release
travels most of its distance in the first quarter hour.

**Honesty rules — the important part.** There is no live tick backtest endpoint, so:
- rows the model produces are **badged «مرجع»**, dates follow the indicator's own release
  cadence (weekly Wed/Thu markets, monthly, quarterly, 6-weekly policy meetings) counted
  back from the event date, the consensus is taken from this same calendar feed where it
  exists, and the footnote spells all of it out;
- rows that the calendar feed *does* carry a published number for are tagged **«زنده»**;
- the summary is explicitly **not a win-rate**: every path is generated by the same rule a
  hit-rate would measure, so instead it states the rule itself (real desk knowledge), the
  sample split (above/below/in-line) and the *modelled* average move at 15 and 60 minutes;
- ECB matching was tightened to rate decisions only — “ECB Machado Speech” is not a policy
  surprise; an event outside the covered indicator set renders an explicit “no reference”
  note rather than invented numbers.

**UI.** `<details open>` (native keyboard toggle) headed by the indicator label and an
«آرشیو مرجع · ۴ انتشار اخیر» badge; asset chips switch the pairing (`±` marks two-sided
reactions); an inline SVG draws the zero baseline as a dashed hairline with one copper-free
path per release — `--up` green when the 60-minute move is up, `--dn` oxide when it is down,
grey dashed for an in-line print — with `<title>` tooltips and a Persian `aria-label`;
a seven-column table lists date, actual, forecast, signed surprise, the 15m and 60m move and
a live/reference tag.

**Verification.** Browser end-to-end on a real row click (Dallas Fed Manufacturing Index):
4 reference rows (۵۲/۵۰، ۴۸/۵۰، ۵۲/۵۰، ۵۰/۵۰), path strokes measured as
`rgb(87,177,131)` up, `rgb(217,106,85)` down, grey dashed in-line, zero line
`rgba(236,224,206,.2)`, chip switch to XAU recomputing the model (PMI hot → gold −0.34%
at 60m) and rewriting the aria-label and the rule sentence, and the uncovered-event branch
rendering its note. Offline maquette renders the same block from its `/api/econ` snapshot.
`pytest` **25 passed**, `check_dashboard_js.py` 4/4 (3598 lines), `splice_theme.py --check`
clean (1802 lines / 107336 bytes).

## 31. `tests/test_dashboard_logic.py` — the browser logic under test (2026-09-28)

Everything the narrative radar and the reaction model *decide* runs in the browser, where
`pytest` cannot see it; `check_dashboard_js.py` only proves the blocks parse, so a flipped
reaction sign or a loosened clustering rule would ship silently. The new test extracts the
individual `const`/`function` units from `dashboard_html.py` with a quote-aware
brace/bracket scanner (a `{0,24}` inside a regex literal must not end a unit early), runs
them under `node` with the few helpers they lean on stubbed (`toFa`, `esc`, `faAssetName`,
`tzDayFa`), and asserts ~45 behaviours — the co-occurrence gate, cluster volumes, velocity,
status transitions (emerging → peaking → cooling), window filtering and determinism for the
radar; rule matching (a Lagarde speech is not an ECB decision, a US map is never applied to
a UK print), sample construction, sign conventions (hot CPI ⇒ DXY up, gold and crypto
down), the front-loaded 15-minute leg, compact number formatting, SVG path classes and the
collapsible/`aria` markup for the reaction block. It skips cleanly when `node` is absent.

**Verification.** `pytest` **26 passed** — 25 in `test_core.py` plus the new
`test_pure_dashboard_logic` (which runs ~45 node assertions internally); it was this harness
that caught the missing `/i` flag described in § 29. `check_dashboard_js.py` 4/4 (3601 lines),
`splice_theme.py --check` clean (1802 lines / 107336 bytes).

## 32. Smart alert rules — condition engine, builder, dispatch (2026-09-28)

The Telegram view (`view-alerts`) used to be a periodic digest only. It now also holds
**«قوانین هشدار هوشمند»**: `[condition…] AND/OR → [action]`, evaluated in the browser on
every price tick and every news cycle.

**Rule schema.** Conditions come in four kinds — `price` (a live quote against a threshold),
`change` (the 24h percentage), `event` (a calendar release that actually printed, optionally
filtered to High/Medium impact) and `news` (title/summary keywords **plus** a credibility
floor **plus** a freshness window). Operators are `> ≥ < ≤ = contains`; a rule joins them with
AND or OR and carries a per-rule cooldown and an actions set (`toast` sticky card, `tone`
squawk, `tg` Telegram, `push` desktop notification). Rules live in `localStorage['mohmd_alert_rules_v1']` together with the
execution log (last 60 firings), per browser — same policy as the bookmarks.

**Engine.** `arCondOk(cond, ctx)` answers three ways on purpose: `false` (not met), `null`
(no data — a missing quote or an unprinted event must never look like a match) and an object
(the matched reading, which carries what to print). `arRuleEval(rule, ctx)` is pure and
`arBuildCtx()` is the only part that touches globals (`LIVE`, `ECON`, `DATA`). `arTick()`
coalesces bursts into one evaluation 400 ms later, so a rule can never sit inside the render
path of `pollLive()` or `renderAll()`.

**Two firing rhythms, deliberately different.** A threshold/event rule is a *state*: once it
fires it stays quiet for its cooldown even while the reading keeps wiggling. A headline is an
*event*: the same article never fires the same rule twice, however long the rule runs.

**Actions.** Four of them, and an alert is never lost silently: a **sticky toast** in a fixed
`.alert-stack` (`aria-live="assertive"`, newest five kept, per-card dismiss, oxide styling for
failures) instead of the single transient `#toast`; a **browser notification** through the
Notification API, whose permission is only ever requested from the click that saves such a rule
(and which, when permission is refused or the API is absent, falls back to a warning card in the
stack rather than vanishing); the **squawk**; and the **telegram** dispatch. The
squawk is a two-tone WebAudio burst unlocked on the first user gesture, because browsers block
audio before one — and a blocked context can never break a rule. Telegram posts the rendered
template to the new **`POST /api/telegram/send`**, so the bot token never reaches the browser:
the server holds the credential, the HTML parse mode and the send lock, and guards empty text
and anything over 3500 characters before Telegram's own 4096 limit.

**Bugs the tests and the browser caught.** (1) `rule.cooldown || 30` silently turned an
explicit `0` (“fire on every tick”) back into 30 minutes — now `== null ? 30 : n`.
(2) Price rules re-fired on every 15s tick because the dedupe signature changes whenever the
price moves a fraction — fixed by the state/event split above. (3) `esc()` is the page's
`.replace()`-based escaper, so passing a *number* (the credibility field) threw and took the
whole condition row down; every value is stringified first, and the test harness now renders
each field shape.

**Verification.** End-to-end in the browser, not just asserted: a saved `WTI > 1` rule fired
**by itself** from a real 15s `/api/live` poll tick (WTI 95.6), the card and execution-log row
appeared with the live quote in the body, and repeated evaluations inside the 30-minute
cooldown stayed silent; a `news` rule with `Hormuz` at a 50% floor fired on a real headline
whose summary reads “renewed geopolitical uncertainty over the Strait of Hormuz”, then refused
to fire again on the same article id; toggling the switch off persisted `enabled:false` and
stopped it firing; edit repopulated the whole form (and the button becomes «بهروزرسانی قانون»);
delete removed it from memory and storage; an empty form saved nothing and coloured the hint
oxide red; the trial-run button listed each condition with its verdict and previewed a card
(with the distinct failure styling when `/api/telegram/send` answers
`telegram_not_configured`, which is exactly what the endpoint returns when no bot is set).
The four endpoint guards were hit directly: `empty_text`, `text_too_long`,
`telegram_not_configured`, and `{"ok": true}` shape on the happy path. `pytest` **26 passed**
(node harness now ~85 assertions, including the engine, the runner’s dedupe/cooldown and every
builder field shape), `check_dashboard_js.py` 4/4 (4135 lines), `splice_theme.py --check`
clean (1886 lines / 112953 bytes), maquette rebuilt at 72 routes / 1263 KB with the alert
builder live offline (its `/api/telegram/send` demo route answers `demo_no_bot`, so the offline
demo tells the truth about not having a bot).

---

## 33. Offline-first PWA — `MohmdNewsDB`, full-text index, cache-mode telemetry (2026-09-28)

**Goal.** State lived in memory (`DATA` / `ECON`) plus `localStorage`, which is capped at 5 MB
and synchronous. The terminal had to keep opening — and keep being *readable* — with Flask down,
on a cache-cleared machine, or while a cycle is mid-flight.

**The layer.** A new `web/` directory holds the three files a browser insists on addressing by
URL: `sw.js` (must own the root scope), `manifest.webmanifest`, and `storage_engine.js`
(the IndexedDB engine, served as a file and inlined into the maquette by
`tools/make_maquette.py`). Flask serves them from disk — `/sw.js` with
`Service-Worker-Allowed: /` and `no-cache`, icons with a week-long cache — because Flask's own
static folder would put the worker under a scope that excludes the app.

**IndexedDB.** One database, `MohmdNewsDB`: `articles` (full snapshots, indexed by `ts`, `topic`
and multi-entry `assets`), `reports` (keyed by symbol), `calendar` (cached multi-week events),
`bookmarks` (starred snapshots, mirrored to `localStorage` so the existing renderer is unchanged),
plus `terms` — an inverted index — and `meta`. Writes happen off the response path for every JSON
answer the page receives (`/api/data`, `/api/report/*`, `/api/econ`, `/api/article/*`), and the
cache is bounded by a retention window plus a profile cap, pruned once per page load.

**Search.** Query tokens are folded (Persian `ي/ك`, Latin diacritics, both stopword sets) and
expanded by prefix inside a single key range, then the posting lists are merged and scored by
idf, field boost (headline 3×, asset tag 2.5×) and a 36-hour recency half-life. Nothing walks the
article rows, which is why a query costs a handful of key reads. In the browser: **1 252 cached
articles, 10 600+ indexed terms, 1 ms `took`, 3.3 ms average per query over 12 runs**. The feed
search box falls back to it when the live window has no match, and labels those results
`از حافظهٔ محلی`.

**Telemetry.** The topbar capsule gained one item: `Online (Synced)` / `Syncing…` /
`Offline (Cache Mode)`. It reads what the *last request actually did* (including the worker's
`X-MOHMD-Cache: hit`), never `navigator.onLine` — a WAN that is up but cannot reach Flask is
still cache mode. Its tooltip carries the live row counts, and the cycle pill follows suit
(`حالت آفلاین — داده ذخیره‌شدهٔ آخر`) instead of repeating a cached "cycle running…".

**Verified by stopping the server** (which is the only honest way to test this): the page booted
from the worker's shell, the feed rendered 400 cards from the database, `/api/report/BTC` answered
`200` from IndexedDB, `/api/econ` answered from its stored snapshot, the calendar board rendered
17 rows for the selected day, and a query the live window could not answer (`apollo`, two aged-out
stories) was served from the index in 0 ms.

`pytest` **46 passed** (two new files: `tests/test_pwa_layer.py` — engine logic under node, the
manifest against the icons it promises, the served URLs, the page's wiring — and the stream suite
below), `check_dashboard_js.py` 5 inline blocks + 2 files in `web/`, `splice_theme.py --check`
clean. Two real bugs surfaced in the browser that no unit test would have caught: every report was
being stored under the literal key `"report"` (a wrong path segment), and offline hydration left
the source `<select>` empty, which the feed filter reads as "show only articles with no source" —
a silently blank feed.

**Honest limitations.** The IndexedDB copy lives in the browser that made it (no cross-device
sync); market prices are deliberately *not* persisted (stale quotes dressed as live ones are worse
than none — the worker's own `/api/data` cache covers "show me the last snapshot"); and the app
only writes to the database while a tab is open (no background sync).

---

## 34. Real-time stream — one connection, three channels, no parallel polling (2026-09-28)

**Goal.** The dashboard *was* the clock: prices every 15 s, the feed every 60 s, a 120 s safety
net, and each of those refreshes re-rendered a whole component — the ticker rebuilt its markup on
every tick, the feed replaced `#newsGrid` (taking the reader's scroll position with it). Ten open
tabs meant ten upstream quote fetches for the same numbers.

**`StreamManager` (client).** One connection carrying three channels — `prices`, `news`,
`calendar` — routed by event name. Transport preference is **WebSocket → SSE → HTTP polling**:
the client asks `/api/stream/info` what the server can offer instead of guessing, and a forced
WebSocket (tested) fails once, steps straight down to SSE *without* waiting out the backoff (a
ws the server cannot serve is not a terminal failure), then walks
**1 s · 2 s · 5 s · 10 s · 20 s · 30 s** with jitter, capped at 30 s. Polling is started by the
failure path alone and cleared the moment a transport connects — with the stream alive,
`counters.polls` stays at **0** while `counters.prices` climbs.

**Micro-updates.** One `requestAnimationFrame` per batch. A price frame is diffed against the
previous one (`smPriceDiff`), and only the `.p` / `.c` nodes whose value actually moved are
written and flashed; the index is built from `data-sym` in the markup, so an unchanged symbol
costs zero layout work and a new component gets live ticks the moment it declares its symbol.

**Incremental feed.** New headlines are merged (`smMergeNews`: newest-first, no duplicates, no
reordering), prepended to the grid, and the reader's position is preserved *by reference*: the
topmost visible card is the anchor, and `scrollTop` moves by exactly what that card moved. Height
deltas were the wrong measure here — the feed is a multi-column grid, so inserting one card
repacks the columns and the total height can even shrink. Measured in the browser: anchor shift
**0 px** across three inserts, with native scroll anchoring both on and off.

**Server push (`stream_ticker_loop`).** While at least one client is attached, prices are
refreshed and pushed every 12 s (`MOHMD_PUSH_SECONDS`) and a release scan runs every 60 s;
`live_prices()` keeps doing the broadcast so its own TTL dedupes the upstream fetch and two tabs
never produce two frames. With nobody attached the loop does *nothing* (`stream_push_once()`
returns 0 without touching the quote APIs) — the free quote endpoints are rate-limited, so an idle
terminal must cost nothing. Newly released indicators are announced once on the `calendar`
channel, keyed to the exact row the renderer builds (`<epoch>_<title>`), with the first scan after
a restart announcing nothing older than 30 minutes instead of flashing a week of history. `ws` is
advertised only when `MOHMD_WS_URL` is set (behind a proxy that upgrades); this deployment pushes
over SSE, which needs no dependency.

**Verified in the browser with real interaction:** the pill reported `SSE live` with counts
(3 price frames, 139 micro-writes, 0 polls); a synthetic news frame prepended a card with the
`card-enter` marker, updated the count to ۶۰۱, and did not move the anchor; a synthetic release
frame turned a `pending` row into `released just-released flash-dn` and wrote `3.10%` into the
actual cell (and into `ECON`, so the next render keeps it); killing Flask dropped the state to
`polling` with the ladder walking 1→30 s and the poll timers running; restarting it returned to
`live` with the poll timers cleared. `pytest` **46 passed** — `tests/test_stream_manager.py`
adds ~30 node assertions on the ladder, routing table, diff, merge and anchor maths, plus the
server-side release scan (announce once, revisions announce again, idle costs nothing) and the
"no parallel polling" invariant.

**Honest limitations.** The client's WebSocket transport is complete but unexercised in this
deployment (Werkzeug cannot upgrade a connection — set `MOHMD_WS_URL` behind a proxy that can);
the stream only runs while a tab is open; and the calendar channel announces the figures the
cached calendar page exposes, so a release appears within one calendar TTL of it being published
upstream, not the instant the number prints on the wire.

## 35. Windowed grids, one clock, and a markup gate (2026-09-28)

**The bill for a linear feed.** `renderFeed()` drew `list.slice(0,400)` cards. At ~27 nodes per
card that is a 10 900-node subtree — and 200 more stories in the payload were not merely slow,
they were unreachable. The archive did it again with its own 250, and every 60-second payload
threw the entire subtree away and rebuilt it, which is also why the reader's scroll position kept
going back to the top. Three separate problems with one cause: the list was the DOM.

**`VirtualScroller`** keeps the *cards* windowed and nothing else. A spacer is sized to the total
computed height, so the scrollbar still measures the whole list; the cards live in an
absolutely-positioned layer whose rows sit at calculated offsets; a row is built when it comes
within one screen of the viewport and is then *kept* while the reader moves back and forth inside
it. The grid model is exactly the one CSS grid already had — equal columns, each row as tall as
its tallest card — so the look does not change, only the number of nodes that exist. Item heights
are cached by key (a story keeps its measured height across filters, sorts and re-renders) and a
card nobody has measured contributes the median of the ones that have, which is the safe
direction for a wrong guess: it costs a little slack, never an overlap.

Three bugs in that engine were found in the browser, and each was the kind that looks like a
cosmetic glitch and is really a correctness problem:

  * `spans[i]` is `1` for an ordinary item, and `1` is truthy — so "is this item full-width"
    answered yes for every item, and a 600-story feed laid out as 600 rows of one. The test that
    pins it (`per-item spans of one do not collapse the grid`) is in the harness now.
  * the row signature was `idx.join(',')` — *which slots*, not *which stories*. A re-render that
    put different articles in the same indices kept the old markup, which is how the loading
    skeletons survived the arrival of the real feed. It is keyed by item now.
  * `smScroller()` accepts an ancestor only if it *currently* overflows, and at mount time the host
    is empty — so the grid attached itself to the document instead of `.app-main` and every window
    was measured from the top of the page. `vsScroller()` resolves the scroller from `overflow-y`
    alone.

**One clock.** Fourteen `setInterval` loops drove this page: two 1-second countdowns, the session
clock, the ETF poll, two feed safety nets, the deep-recovery poll, the sentiment poll and the
stream's three fallback timers. They are all slots on `Clock` now, on a single pump. While the
page is visible the pump is a `requestAnimationFrame`; while it is hidden it is *one* 4-second
timeout. That second half is the part worth arguing about: rAF sleeps in a background tab, and the
neat version of this change would have been to let the whole clock sleep with it — which would
have silently turned every price rule in § 32 into a foreground-only feature, because the rule
engine runs on the live-price tick. One slow heartbeat keeps the polls that matter alive and stops
the page paying for frames nobody is looking at. Coming back is not a stampede either: an overdue
slot is re-based to "now + interval" *before* its job runs, so an hour in the background costs one
run per slot rather than thirty fused requests, and a frame fires at most two slots so a restored
tab spreads its catch-up over a few frames. A slot that throws is isolated, counted, and logged
with its label; the schedule survives it.

**A markup gate.** `esc()` was doing three jobs and doing the third one badly: it escaped `'` as
`\'` so a value could be dropped inside a JS string in an attribute, which holds for a quote and
fails for a backslash — a feed id of `a\'` closed the string and the rest of the attribute became
script. The three jobs are now separate and each call site says which one it means: `esc()`/`attr()`
for text and attributes, `jsArg()` for a value about to sit inside a handler (it emits a real JSON
literal and then attribute-escapes that), and `safeUrl()` for a URL from a feed. Escaping was also
the wrong answer for a URL all along: `href="…esc('javascript:…')…"` is escaped and still runs,
because the parser decodes character references *before* the URL is interpreted. `safeUrl()`
decodes first, strips every space and control character, and then refuses anything whose resolved
scheme is not `http`, `https`, `mailto`, `tel` or a real inline bitmap — so `JaVaScRiPt:`,
`java&#x09;script:`, `&#106;avascript:` and `data:text/html` all come back empty, and every feed
image and link in the page now goes through it. `Sanitizer.sanitize()` (a DOM walk with an
allowlist; the escaping fallback is what runs where there is no `DOMParser`) stays available for
the day a component wants upstream markup instead of rebuilding it — nothing asks for that today,
and grep says so rather than a comment saying so.

**Leaving a view releases it.** The TradingView embed is an iframe with its own connection to its
own backend, and it used to stay alive in a hidden tab forever. It is torn down now when the
reports tab is left (`showView()` releases on the way out, and the tab re-mounts it on the way
back in); nothing else is released on a tab switch, because nothing else belongs in that path. (The
feed did carry a candlestick engine for one revision; releasing *it* was tried and the page came
back unresponsive once after a re-mount into a container that still held the old canvases — not
reproducible on demand is exactly the wrong trait for something a tab switch touches. The engine
itself is gone now, removed on request in §36, so the question is moot.) The windowed grids keep
their rows: they are a few dozen nodes and they *are* the reader's scroll position.

**The numbers.** `PERF.paint()`, the کارایی pill in the topbar, or `Alt+Shift+P` prints them live;
the window paint figure is `Clock`-independent, so it is a floor on the cost of one frame of
scrolling and not a promise about compositing:

| measurement | before | after |
|---|---|---|
| feed, 600 stories | 400 cards = 10 886 nodes (and 200 stories unreachable) | 9 cards / 3 rows, **4 450 nodes** in the whole document |
| archive, 250 stories | every card, day boxes and all | 12 cards / 5 rows, **4 454 nodes** |
| projection at 2 000 stories | ~54 000 nodes | **~4 700 nodes**, flat in list length |
| window paint, 18 cards (warm) | n/a | p50 **5.9 ms**, p95 9.6 ms |
| the same markup parsed by the browser, no layout | 3.3 ms p50 | 3.3 ms p50 — the engine adds ~2.6 ms |
| `setItems` on a 2 000-item list (full relayout + first paint) | n/a | 27–56 ms, once, not on the scroll path |
| timers | 14 `setInterval` loops | 1 pump, 6–8 slots, ≤ 2 slots per frame |

A read that follows a write is what makes the browser lay the page out again, so a row whose items
have all been measured is not read a second time — that change alone is the difference between the
warm paint above and 17 ms. A resize, or an image that lands late, clears the measurements of the
rows on screen so the cache cannot serve a height the row no longer has.

**Verification.** `pytest` **46 passed** — the node harness now carries ~50 more assertions over
the layout maths (row packing, full-span rows, the two binary searches, the window clamped at both
ends, the median estimate), the clock (period, no double fire, one run per slot across an
hour-long gap, ≤ 2 slots per frame, isolation of a throwing job, `when()`, `off`, `clear`) and the
sanitiser (every quote/backslash trap round-tripped through `JSON.parse`, ten URL schemes refused,
the DOM-walk fallback counted rather than silent). Extracting those units needed a real fix to the
harness itself: `/…/` literals and comments are stepped over now, and a skipper hands back the last
character it consumed — swallowing the character after a regex is how a `]` disappears and a unit
never closes.

In the browser: 600 stories scrolled from top to bottom with the DOM holding 3–7 rows throughout
and the last rendered card being the last story in the list; a full `loadData()` at `scrollTop`
15 000 kept the position and the same 18 cards; a stream frame prepended one story and moved the
scroll by exactly one row (+472 px, arithmetic, not a probe) with the entrance animation intact
and the scroll left alone when the reader was already at the top; the archive rendered 250 stories
under full-width day headers; resizing 1440 → 900 → 1440 re-packed the grid 3 → 1 → 3 columns; the
page served from the service worker with Flask killed restored 600 stories from IndexedDB and
rendered them windowed (9 cards, 3 rows); the perf HUD reported its own numbers; and with the
`reports` view left, `tvTeardown` ran exactly once when leaving it and never for archive, feed or
bookmarks. `check_dashboard_js.py` 5/5 inline blocks + both `web/` files; the maquette rebuilt
(72 routes, 1 391 KB) and renders both grids windows offline.

**Honest limitations.** The measured paint numbers come from a *hidden* preview tab on a loaded
development box — a hidden tab is throttled, so treat them as an upper bound and re-measure with
the perf HUD on a real screen. The per-card estimate is refined as rows come into view, so a first
hard scroll to the very bottom of a 2 000-story archive can shift the scrollbar once as unmeasured
cards are replaced by their real heights. Virtualisation covers the feed, the archive and the
bookmarks; the calendar board, the correlation matrix and the narrative cards still render whole
(they are bounded by the week or by the cluster count, not by the archive). And the CSS in the
page still carries 8 lines of the RTL/LTR direction layer that are not in `tools/theme_v3_*.css`,
so `splice_theme.py --check` reports that drift — my new rules were appended to both places
deliberately, to keep working around a concurrent editor rather than over their work.

---

## 36. The chart under the feed, and the language layer, come out (2026-09-28)

**Two requests, and each one had a tail that only showed up after it was gone.**

**The candle panel under the news.** `#chartSection` sat directly under the feed: an asset select,
a timeframe select, a price/volume read-out and a `#chartContainer` filled by **Lightweight
Charts**, pulled from unpkg by a `<script src>` tag on every page load. All of it is gone — the
section, the library tag, and the module behind it (`initChartAssets()`, `initChart()`,
`loadChart()`, `_chart`, `_candleSeries`, `_volumeSeries`, `_ema20Series`, `_ema50Series`,
`_rsiSeries` and its `DOMContentLoaded` bootstrap). The page no longer reaches unpkg at all and no
longer calls `/api/chart/<sym>`; it is one fewer third-party origin on a page whose whole point is
reading news offline. `releaseChart()` went with the module, so `teardownView()` now releases
exactly one thing — the TradingView embed it still mounts when the reports tab is left. The
reports tab keeps that embed, and its own pair of dead comment headers (the ones advertising a
`/api/candles`-fed SVG engine that had already been removed in an earlier pass) went too.

**The language layer.** Added earlier the same week, removed on request: the `#langSwitcher` in
the topbar, the `#settingsLangSwitcher` row in Settings, all 20 `data-i18n` /
`data-i18n-placeholder` attributes, the whole i18n script (`_currentLocale`, `_translations`,
`loadLocale`, `t`, `applyTranslations`, `setLanguage`, the `initI18n` IIFE), the
`GET /locales/<lang>.json` route in `app.py` and the `locales/` directory with its five files. The
app is Persian RTL and nothing else again: `<html lang="fa" dir="rtl">`, confirmed in the browser
(`htmlDir=rtl`, `htmlLang=fa`, no switcher anywhere in the DOM), and `/locales/en.json` now
answers 404. `tests/test_core.py` lost `test_locales_structure_and_routes` with it.

**The tail: a stream frame that lands before the payload.** `Stream.on('news')` needs somewhere to
put a merged list, so on a frame that arrives before the first `/api/data` response it fabricates
`DATA = {}` — and `DATA = {}` is not a payload. `renderChips()` then read `DATA.topics_meta`
through `Object.keys()` and `DATA.config.assets` by bare index, and `cardHTML()` read
`DATA.kind_labels` from inside the virtual scroller's render path, so an early news frame produced
`TypeError: Cannot convert undefined or null to object` in the console instead of a page that
renders. Neither crash was caused by the removals — both were found by re-reading the console
afterwards — but this is where they get fixed: `renderChips()` returns early when there is no
`DATA` at all and reads the rest through defaults, `orderedAssets()` stopped indexing
`DATA.config` twice per call, and the card renderer defaults its label and escapes it. A frame
that beats the payload is now a non-event rather than the one thing on the page that throws.

**Verification.** `check_dashboard_js.py`: 5/5 inline blocks (6 184 lines) + both `web/` files.
`pytest`: **45 passed** (was 46; the locales test left with the layer). Served HTML: zero matches
for `langSwitcher`, `chartSection`, `data-i18n`, `lightweight-charts` or `loadChart`, and the page
now runs its news channel with no exception at all — the only console error left is a
`403 FORBIDDEN` on `/api/ai/predictions`, which predates this section and every one before it. In
the browser: 600 stories windowed to 3 rows, 11 topic chips, 14 asset chips, no chart, no
switcher, `LightweightCharts === undefined`. The maquette was rebuilt (71 routes, 1 386 KB — one
route fewer, because it no longer asks for a locale file) and carries none of the removed names.

**Honest limitations.** `GET /api/chart/<sym>` and `GET /api/candles/<sym>` are still in `app.py`
with no caller in the page — deliberately kept, because deleting a live HTTP endpoint is a
different decision from deleting its UI, and nothing here knows whether an external client polls
them. The Persian-only copy is hard-coded in the markup again, so re-introducing a locale means
re-introducing the layer, not flipping it on; git history has it (`dashboard_html.py` is the same
file, so the removed script block is one revert-shaped diff away). And `splice_theme.py --check`
still reports the same 8 lines of RTL/LTR drift it reported before this section, for the reason
given at the end of §35.

---

## 37. اخبار منتخب — a twenty-story carousel above the feed (2026-09-28)

**The row was three cards and it never moved.** `#leadRow` held the three highest-credibility
stories above the grid. Three is not a section, and the top three by credibility barely change
between two payloads — so the same three headlines sat at the top of the feed all day while six
hundred stories turned over underneath. On request it now selects **twenty** stories and walks
through them **four per row, one page at a time**.

**Which twenty.** `leadPick()` filters to a credibility floor (`LEAD_MIN_CRED` 0.55, was a hard
0.6 for a top-3) and sorts by `leadScore()`, which is credibility first and freshness as the
tie-breaker: a 0.80 story from an hour ago outranks a 0.75 one from this morning, and nothing
buys its way in on age. It then takes **the best story per asset first** and fills the rest by
score — four cards in one row being four takes on the same coin is the failure mode a score
alone does not prevent. A millisecond epoch from a stray upstream feed is normalised, not trusted,
as everywhere else that touches `published_ts`.

**Which four.** The pool pages as `ceil(20/4) = 5` windows, with wrap-around in both directions
(`leadWindow(pool, -1)` is the last page, not `undefined`). The head carries the label, the count
(«۲۰ خبر برتر»), a dot per page, the position («۳ / ۵»), and prev/next/pause. A rotation slot on
the **single Clock** (`lead-rotate`, 10 s) does the moving, and everything that should stop it
lives in that slot's `when` rather than in five scattered guards: not the feed view, hidden tab,
paused, or the pointer or the keyboard inside the row — and `prefers-reduced-motion: reduce` means
no rotation at all. A new payload does not snap the row back to page one: `renderLead()` re-finds
the story that was on screen and keeps its page, so a 60-second refresh cannot yank the page out
from under a reader.

**The controls are not decoration.** An auto-rotating block that moves for more than five seconds
needs a visible stop, so the pause button is the accessibility requirement first and a nicety
second; it flips its own icon, its title and `aria-pressed`, and the dots are real buttons with
`aria-current`. Cards are only re-rendered on the page they enter — the fade-in class is applied
at creation, so a page change is one animation instead of a swap plus a timer waiting to start
one — and the whole row collapses to the label alone when the pool fits on one page.

**One fix on the way through:** the thumbnail's proxy fallback used to be built from the raw feed
string (`data-orig`), i.e. the one URL in the card that `safeUrl()` had not seen. It now carries
the sanitised URL, and a story whose image is refused renders no banner at all instead of an
empty frame that tries the refused URL.

**Verification.** The node harness grew 26 assertions over the new units — the floor excludes a
0.40 story, equals break on freshness, the pick is deterministic, five pages cover all twenty
stories exactly once, a negative page wraps backwards, and a `javascript:` image URL never
reaches a `src`. `pytest` **45 passed**, `check_dashboard_js.py` 5/5 blocks (6 213 lines) + both
`web/` files. In the browser: twenty stories in five pages, four columns of 277 px in a 1 157 px
pane at 1440, `page` walking 0 → 1 → 2 → 3 unattended; thirteen seconds with the pointer on the
row and the run count frozen; the pause button holding it for eleven seconds and `when()` back to
`true` on resume; the last page wrapping to page one with the same first card id; and one column
below 780 px, head and pager included.

**Honest limitations.** Hover-pause means a parked pointer stops the rotation indefinitely —
deliberate (a reader's pointer in the row is a claim on it), but it also means the pause button
is rarely needed by mouse users; a keyboard user tabbing into the row stops it the same way.
The pool is rebuilt from scratch on every payload, so a story that drops out of the credibility
floor between two refreshes disappears from the rotation rather than being kept for its page. The
carousel ignores the feed's own filters, exactly as the three-card row did — it is an editorial
pick over the whole window, not a view of the filtered list. And `splice_theme.py --check` now
reports far more than its 8 lines: a concurrent editor has ~99 lines of in-flight CSS in the page
(a squawk-box block and RTL/LTR overrides) that are not in `tools/theme_v3_*.css`, plus a sixth
inline `<script>` block that takes `check_dashboard_js.py` to 6 blocks / 7 008 lines (both parse). This section's
rules were appended to **both** places as usual — the diff between the page and the theme files
contains no `lead-` line — so nothing here added to that drift, and the style block is still not
re-spliced over their work.

## 38. Three topbar buttons and everything behind them come out (2026-10-04)

**Removed, end to end — not hidden.** «اعلان‌ها», «بولتن روزانه (PDF)» and «ویجت سایت» were the
three buttons left in `.topbar-actions`; each owned a backend module that existed for that button
and nothing else. All three are gone from the tree:

| Gone | What it took with it |
|---|---|
| اعلان‌ها | `FreebuffNotifier` (the module, the `playChime` oscillator, `checkCalendarAlerts`, `updateButton`), the `loadCalendar()` hook that fed it, the button, and its line in the expansion-suite comment header |
| بولتن روزانه (PDF) | `/api/report/daily/print` + `/api/report/daily/html`, the import, `daily_briefing.py`, and the button |
| ویجت سایت | `/embed/ticker` + `/embed/news` (with their `X-Frame-Options: ALLOWALL` and `frame-ancestors *` headers), the import, `embed_widgets.py`, the `#embedOverlay` modal, `.embed-preview-box` / `.embed-code-area`, `openEmbedModal()`, and the button |

The topbar is now one button wide (`#refreshBtn`), verified against the served HTML rather than
the source. The service worker needed the change too: `/api/report/daily/print` was the one
network route in the `SHELL` precache list, so leaving it would have made every install burn a
404 on every activate. Removed, and `SW_VERSION` bumped to **v9** per the file's own rule.

The `navigateFirst` guard that refuses to cache anything but `/` under the shell stayed. Its
comment cited the ticker embed as the reason, which no longer exists, so the comment was reworded
around the invariant instead of the example — the guard is what stops any future sub-page from
becoming the offline boot, and `/post-trier` is still a second document.

**Verification.** `py_compile` on `app.py` + `dashboard_html.py`, `node --check web/sw.js`,
`check_dashboard_js.py` 7/7 inline blocks + 4/4 `web/` files, and `pytest` **192 passed** (the
one failure is the pre-existing `test_database_messenger_posted_dedup`, which writes real rows to
`.mohmd_news.db` and is unrelated). In the browser on a scratch port: `/embed/ticker`,
`/embed/news`, `/api/report/daily/print` and `/api/report/daily/html` all **404**; `/` and
`/api/channel/feed` still 200; `FreebuffNotifier` and `openEmbedModal` are `undefined`, the four
removed DOM ids are absent, `.topbar-actions` holds exactly one button, the console is clean on
worker v9 with no 404s in the network log, and the calendar — the view whose loader used to call
into the notifier — still renders 319 events and its day table with no `ReferenceError`.

**Deliberately kept.** `arNotify` / `arAskNotify` are the squawk-box notices inside the ask panel,
not the browser-notification feature; the `i-bell`, `i-file` and `i-external` icons stay because
four, six and two other places use them; and the TradingView chart embed is unrelated to the
site widgets and untouched.
