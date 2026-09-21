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
| `calendar_data.py` | 190 | ForexFactory weekly JSON, Fear&Greed (alternative.me), Farside BTC-ETF flows, macro quotes (DXY/SPX/VIX/WTI via Yahoo) — all cached, independent failure |
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
| `GET /api/chart/<sym>` | indicator chart payload (RSI/MACD/BB/levels) for the reports tab |
| `GET /api/live` | live prices (CoinGecko→Binance→Yahoo ladder) + global Fear&Greed, 15s poll |
| `GET /api/etf` | live spot-ETF quotes (8 symbols: BITO/IBIT/FBTC/GBTC/ARKB/ETHA/ETH/ETHE) via Yahoo v8, 60s cache |
| `GET /api/fng/<sym>` | **per-asset sentiment** 0–100 from that asset's last-24h headlines (credibility-weighted + freshness boost), 15min cache |
| `GET /api/candles/<sym>` | live candles (60m/240m/1d) for the in-app candlestick chart |
| `GET /api/article/<id>` | full article content; paywalled domains go through `news_bypass` ladder, others direct with bypass as fallback; Persian option; cached |
| `GET /api/report/<sym>` | full bilingual report (sections list) |
| `GET /api/report/<sym>/markdown` | markdown export |
| `POST /api/refresh` | manual cycle trigger |
| `GET /api/econ` | calendar (ForexFactory week) + F&G + ETF flows (Farside) + macro quotes |
| `POST /api/telegram/*` | test / preview / send-now |
| `GET /api/monitor` | per-source health: ok, latency, last count, failure **cause** (English), 30-cycle sparkline history |
| `POST /api/recover` | one-button recovery: retries broken feeds (mirrors → AMP → alternate UA) |
| `POST /api/settings` | persists assets/window/interval/auto-reports/sources |

---

## 5. UI tabs (Persian RTL, dark copper theme, WCAG-minded)

1. **📰 News Feed** — 4-wide card grid, thumbnails (RSS media → og:image fallback → 📰 placeholder), credibility badge on image, Persian headlines (bold 800), Persian dates (Jalali) + EDT times, filter stack: search box / source-kind / source / sort / credibility slider (0–100%) / asset+topic tag bar. Default sort **Newest first**, 400 rendered cards.
2. **📊 Analysis & Reports** — per-asset report document + copy (text only) + markdown + Persian version toggle + **TradingView Advanced Chart widget** (free official embed) + in-app candlestick with indicators.
3. **🩺 Source Health** — all 107 sources with ✓/✗, latency, news count, failure cause (English), 30-cycle health sparkline, single **Recover** button.
4. **📅 Economic Calendar** — ForexFactory week grouped **per-day boxes**, impact badges (🔴🟡⚪), FCST/PREV chips, per-event live segmented countdown (days/hours/min/sec boxed timer), released events ticked **✔ منتشر شد** with distinct style, sort by time/impact, filters (impact/country/hide-past), header countdown to next High event. Sidebar: BTC-ETF flows table (Farside) + **live ETF quote cards**.
5. **🗄 Archive** — articles that fell out of the 24h window (server keeps ≤1200, serves ≤250 newest).
6. **😱 Fear & Greed** — global index gauge + 8-day history **+ per-asset sentiment cards** (10 assets, live from `/api/fng/<sym>`).
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
so the dashboard is no longer empty after a restart; and reports no longer describe ETF-flow data
as unavailable — the Farside/alternative.me feeds are served in the ETF/F&G tabs.
- Feed fetches are now conditional (`If-None-Match` / `If-Modified-Since`); publishers answering 304
  cost a few hundred bytes instead of a full feed re-download, which shortens every cycle.
- The report now cites live derivatives data (Binance futures funding / open interest / long-short
  account ratio, free and key-less) in section 6, plus Farside spot-BTC ETF net flow and the
  alternative.me Fear & Greed reading in section 4 — each degrades to an explicit "data gap" line
  when an endpoint does not answer.
- Images reserve their box (`aspect-ratio`) so lazily-loaded thumbnails cannot shift the layout.
