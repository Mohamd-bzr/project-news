# AGENT OPERATING RULES — MOHMD NEWS

Read this file completely before any action. It overrides your default habits.
A byte-identical copy lives at `CLAUDE.md`; if you edit one, edit both.

## 0. Prime directive

Make the smallest change that satisfies the request. A correct diff is small, local and boring.

Do NOT "clean up", modernize, reformat, rename or restructure anything the request does not name.
If you notice a problem outside scope, list it in your final report. Do not fix it.

## 1. Before editing

1. `git status` must be clean. If not, stop and report.
2. Create branch `agent/<short-task-name>`.
3. Run the baseline gates and record results:
   `python tools/check_dashboard_js.py` and `python -m pytest tests/ -q`.
   If baseline is red, stop and report. Do not fix unrelated failures.
   On this Windows checkout `python` is a Store stub — use `.venv/Scripts/python.exe`
   (Python 3.14; `.venv311/Scripts/python.exe` reproduces the CI interpreter, 3.11).
4. Locate targets by SYMBOL or banner comment (`grep -n "def <name>"`, `grep -n "══ <TITLE>"`).
   Never trust line numbers from docs; they drift.
5. Read only the target function/block plus its direct callers and tests, using view ranges.
   Never load `app.py` or `dashboard_html.py` in full (7.2k / 9.3k lines — you will be truncated
   and then guess).
6. Before the first edit, state a plan: files, symbols, expected diff size.

## 2. How to edit

- Targeted replacements only (`str_replace` / small patch hunks).
  NEVER rewrite, regenerate, re-indent, re-wrap or re-sort a whole file or a whole function
  when only a few lines change.
- LINE ENDINGS: git stores LF blobs; the working tree is CRLF because `core.autocrlf=true`
  (verified: `app.py`, `dashboard_html.py` and `web/*.js` have 0 CRLF in the blob).
  Do not add or run anything that renormalizes line endings repo-wide, and do not "fix" the
  CRLF in the working tree. After every edit run `git diff --stat`: a 1-line change must show
  a handful of lines, not the whole file. If a whole file shows up, your tool rewrote it —
  revert and use a byte-safe method (Python with `newline=''` / binary patch).
- Preserve each file's encoding (UTF-8), line endings, comments, banners, import order.
- Do not touch: `static/sw.js`, `settings.json`, `*.db`, `*.json` caches, `backups/`, `_archive/`,
  `*.bak`, `tools/theme_v3_*`, any file not in your plan.
- No new dependencies, no build step, no new threads/timers (JS timers only via `Clock.every`),
  no new global state.
- Domain modules never import `app`. Put logic in the domain module; `app.py` gets only
  route/wiring code.
- `dashboard_html.py` holds one raw Python string: never introduce `"""`, edit only inside the
  target block, keep Persian/RTL text intact.
- Every external string in the UI goes through `esc()`/`attr()`/`Sanitizer`; numbers through `toFa()`.
- Never rename or remove a JS function without grepping `on(click|change|input|keydown)=` handlers
  and callers in `dashboard_html.py` and `web/*.js`. `tests/test_handlers_defined.py` guards the
  inline handlers — do not weaken it.
- Contract pairs change together: `_ser_article` (server) <-> `cardHTML` (client);
  `web/channel.js` <-> the channel board payload. If shell assets change, bump `SW_VERSION`
  in `web/sw.js`.
- Never fabricate data. Missing data is shown as an explicit gap ("—").
- Do not "fix" unused imports, f-string warnings, `except: pass` or other pyflakes noise unless
  the request names them.
- The five long functions — `run_cycle` (286 lines), `api_settings` (281),
  `fetch_article_content` (236), `_post_cycle_ideas` (161), `api_ideas_send_single` (112):
  read the ENTIRE function before editing; change only the lines required.
- Tests: never write the real `settings.json` (redirect `app.CONFIG_FILE` to a tmp file).
  Never delete, weaken or rewrite an existing test to make it pass. A failing existing test
  means your change is wrong, unless the request explicitly changes that contract.

## 3. After editing

1. `git diff --stat`: every changed file must be in your plan. Revert anything unplanned.
2. If deletions are far larger than intended, stop and re-inspect the diff.
3. Re-run both gates; both must be green. Add or adjust a test for new behavior.
4. One commit: `type(scope): what`. Do not push. Do not merge.
5. Final report, max 15 lines: what changed (file:symbol), proof (commands + results),
   things noticed but NOT touched, assumptions made.

## 4. Stop and ask (do not improvise) when

- the request is ambiguous about layer or data contract,
- the fix needs more than 3 files or noticeably more lines than planned,
- a gate fails for a reason outside your own change,
- you would have to delete or rewrite code beyond the target.

## 5. Measured baseline (2026-10-10, after `50833c4` + the light-theme CSS commit)

- `python tools/check_dashboard_js.py` — **green** (8 inline blocks + 3 `web/*.js`).
- `python -m pytest tests/ -q` — **RED at baseline: 231 tests, 11 failures, 0 errors**,
  all in the messenger / content-ideas domain introduced by `50833c4`:
  `test_messenger_gateway.py` (8: ideas_summary cut/paragraph/link behaviour,
  `_tg_render_digest` / `_bale_render_digest` paragraph contract, push tests),
  `test_ideas_dispatch.py::...test_dispatch_ideas_to_both_messengers`,
  `test_content_studio.py::test_merged_client_does_not_double_quote_jsarg`
  (expects a `jsArg(` call that `web/channel.js` no longer makes).
  These are pre-existing and NOT yours. While they are red, "both gates green" means:
  the JS gate is green and the pytest failure set is exactly these 11 — no new ones.
- File shapes: `app.py` 7266 lines / 70 routes, `dashboard_html.py` 9286 lines
  (one raw string, `APP_HTML`), `PROJECT_BLUEPRINT.md` 974 lines.
