# MOHMD NEWS — Project Overview

Single-process **Flask** market-intelligence terminal (Persian RTL, dark theme),
Windows-first, built to run free: no API keys, no paid services, no build step.

> This file replaced a 1,700-line review document written on 2026-09-19 whose
> numbers no longer matched the code (source count, tab count, line counts,
> file table, in-memory vs SQLite). The authoritative, kept-in-sync docs are:
>
> * **README.md** — what the product is, how to run it, the module map
> * **docs/related-projects.md** — vendored/borrowed components and why
> * the git history — the full audit trail (launch audit 2026-10-06: lock
>   ordering, auth hardening, whale tracker removal, dead-code removal)

## The shape of it (current)

* `app.py` — the monolith: ~70 routes, scheduler thread, SSE stream manager
  (capped), settings persistence, Telegram/Bale publishing, content-studio
  API, v1 public API, TradingView webhook.
* `dashboard_html.py` — the whole SPA as one Python string (13 views),
  plus `web/channel.js`, `web/storage-engine.js`, `web/sw.js` (shell v16).
* Pipeline: `sources` → `scraper` → `translate` → `market_data`/`indicators`
  → `report_generator`; page-fit engine `channel_profile` (+ vendored
  lexicon `persian_words`); messaging `integrations/`; freemium
  `billing`/`middleware`; persistence `database` (SQLite).
* 194 sources, 30-minute default cycle, 72-hour news window, 234 tests.

## Non-negotiables (project rules)

1. **No invented data** — missing data renders as an explicit gap, never a
   placeholder number.
2. **Free and key-less first** — every external call has a fallback; the app
   degrades, it does not die.
3. **Single process** — no queues, no external DB, no Docker to launch.
4. **Explainable** — every score keeps its factors server-side.
