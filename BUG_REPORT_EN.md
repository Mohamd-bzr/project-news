# FreeBuff — Bug Report & Fix Prompts

> **Date:** 2026-09-28  
> **Method:** Line-by-line scan of all core files  
> **Total bugs found:** 74 (Critical 5 / High 20 / Medium 34 / Low 15)  
> **Approach:** Each section targets ONE file. Copy the prompt at the end of each section to fix that file. Do NOT mix files in a single pass.

---

## Table of Contents

| # | File | Bugs | Severity Range | Prompt Section |
|---|------|------|----------------|----------------|
| 1 | `app.py` (lines 1–800) | 22 | Critical → Low | [→ Section 1](#section-1---apppy-lines-1800) |
| 2 | `app.py` (lines 801–1600) | 20 | Critical → Low | [→ Section 2](#section-2---apppy-lines-8011600) |
| 3 | `app.py` (lines 1601–end) | 18 | Critical → Low | [→ Section 3](#section-3---apppy-lines-16013286) |
| 4 | `sources.py` | 7 | High → Low | [→ Section 4](#section-4---sourcespy) |
| 5 | `scraper.py` | 6 | High → Low | [→ Section 5](#section-5---scraperpy) |
| 6 | `translate.py` | 1 | Low | [→ Section 6](#section-6---translatepy) |
| 7 | `market_data.py` | 1 | Medium | [→ Section 7](#section-7---market_datapy) |
| 8 | `indicators.py` | 3 | High → Low | [→ Section 8](#section-8---indicatorspy) |
| 9 | `report_generator.py` | 2 | Medium → Low | [→ Section 9](#section-9---report_generatorpy) |
| 10 | `database.py` | 2 | Medium → Low | [→ Section 10](#section-10---databasepy) |
| 11 | `fa_format.py` | 4 | Medium → Low | [→ Section 11](#section-11---fa_formatpy) |
| 12 | `calendar_data.py` | 2 | Medium → Low | [→ Section 12](#section-12---calendar_datapy) |
| 13 | `news_bypass.py` | 3 | High → Low | [→ Section 13](#section-13---news_bypasspy) |
| 14 | `tv_ideas.py` | 2 | Medium → Low | [→ Section 14](#section-14---tv_ideaspy) |
| 15 | `smoke_test.py` | 2 | High → Low | [→ Section 15](#section-15---smoke_testpy) |
| 16 | `dashboard_html.py` (JS) | 10 | Critical → Low | [→ Section 16](#section-16---dashboard_htmlpy-javascript) |

---

# RULES FOR THE FIXING MODEL

1. **One file per pass.** Never mix files in a single edit session.
2. **Preserve all imports.** Do not add or remove imports unless a bug explicitly requires it.
3. **Preserve all function signatures.** Do not rename, reorder, or restructure functions.
4. **Preserve all comments.** Only modify the specific lines listed for each bug.
5. **Do not refactor.** Even if code is ugly, only fix the listed bugs.
6. **After each file:** verify the file still loads (`python -c "import <module>"`) or, for `app.py`, verify Flask starts.

---

# Section 1 — `app.py` (lines 1–800)

## Bug 1.1 — CRITICAL — Shared article dicts mutated during translation
**Lines:** ~391  
**Problem:** `_translate_articles_inplace()` writes `title_fa`/`summary_fa` into article dicts that are already visible via `STATE['articles']`. Flask request threads reading the same dicts see partial writes mid-translation.  
**Fix:** Deep-copy articles before placing them into STATE, OR complete translation before exposing articles.

## Bug 1.2 — CRITICAL — Cache dicts mutated without locks
**Lines:** ~382–388  
**Problem:** `CONTENT_CACHE`, `FA_CONTENT_CACHE`, `FA_REPORT_CACHE` are plain dicts modified by `run_cycle` (purge) and by Flask request handlers (read/write/pop) concurrently. No lock protects them.  
**Fix:** Add three dedicated locks: `_CONTENT_LOCK`, `_FA_CONTENT_LOCK`, `_FA_REPORT_LOCK`. Wrap every access in `with <lock>:`.

## Bug 1.3 — HIGH — CONFIG read without lock
**Lines:** ~267–270, ~442, ~449  
**Problem:** `run_cycle` and `scheduler_loop` read CONFIG keys without any lock. `api_settings` writes CONFIG from Flask threads.  
**Fix:** Add `_CONFIG_LOCK = threading.Lock()`. Wrap all CONFIG reads and writes.

## Bug 1.4 — HIGH — LIVE_CACHE busy-flag TOCTOU race
**Lines:** ~800–814  
**Problem:** Two concurrent requests can both see `busy=False` and both spawn refresh threads.  
**Fix:** Add `_LIVE_LOCK = threading.Lock()`. Make check-then-set atomic.

## Bug 1.5 — HIGH — LIVE_CACHE ts/data non-atomic dual-write
**Lines:** ~867–868  
**Problem:** `LIVE_CACHE['ts']` and `LIVE_CACHE['data']` written separately. Reader can see new ts + old data.  
**Fix:** Write both fields inside `_LIVE_LOCK`.

## Bug 1.6 — MEDIUM — Intermediate last_duration misleading
**Lines:** ~372  
**Problem:** `last_duration` is set before translation/report, giving wrong value to readers mid-cycle.  
**Fix:** Remove the intermediate update at line 372. Set `last_duration` only once at the end of `run_cycle`.

## Bug 1.7 — MEDIUM — FA_REPORT_CACHE cleared every cycle
**Lines:** ~388  
**Problem:** `FA_REPORT_CACHE.clear()` drops all cached Persian translations unconditionally.  
**Fix:** Delete this line. Let TTL-based expiry handle it.

## Bug 1.8 — MEDIUM — Unbounded thread spawning for article warming
**Lines:** ~422  
**Problem:** New daemon thread spawned every cycle. If warming takes > cycle interval, threads pile up.  
**Fix:** Before spawning, check `if warming_thread and warming_thread.is_alive(): return`.

## Bug 1.9 — MEDIUM — Report write failures silently swallowed
**Lines:** ~400–403  
**Problem:** `except Exception: pass` hides disk errors.  
**Fix:** Change to `except Exception as e: log(f"  x report save failed: {e}")`.

## Bug 1.10 — MEDIUM — Shallow copy of STATE['stats']
**Lines:** ~624  
**Problem:** `dict(STATE['stats'])` shares nested `cycle_stats` dict.  
**Fix:** Use `json.loads(json.dumps(STATE['stats']))`.

## Bug 1.11 — MEDIUM — `now = now or time.time()` treats 0 as falsy
**Lines:** ~1029  
**Problem:** `now=0` (valid epoch) is replaced with current time.  
**Fix:** `if now is None: now = time.time()`.

## Bug 1.12 — MEDIUM — FNG_SYM_CACHE unbounded + no lock
**Lines:** ~1057–1070  
**Problem:** Grows by one entry per symbol, no eviction, no thread safety.  
**Fix:** Add cap of 200 entries with oldest-eviction. Add `_FNG_LOCK`.

## Bug 1.13 — MEDIUM — MACRO_CACHE empty-list defeats cache
**Lines:** ~1102–1108  
**Problem:** `not MACRO_CACHE['data']` is True for `[]`.  
**Fix:** Change to `MACRO_CACHE['data'] is None`.

## Bug 1.14 — MEDIUM — CANDLES_CACHE unbounded
**Lines:** ~1123  
**Problem:** No eviction.  
**Fix:** Cap at 200 entries. Evict oldest when full.

## Bug 1.15 — MEDIUM — Thundering herd on CANDLES_CACHE
**Lines:** ~1195–1197  
**Problem:** Multiple simultaneous requests for same (sym, tf) all call Yahoo.  
**Fix:** Add `_CANDLES_INFLIGHT = set()`. If key is in-flight, return stale or wait.

## Bug 1.16 — MEDIUM — KeyError on `art['id']`
**Lines:** ~1216, ~1253, ~1297  
**Problem:** No `.get()` guard.  
**Fix:** Replace all `a['id']` and `art['id']` with `a.get('id')` / `art.get('id')`, skip if None.

## Bug 1.17 — MEDIUM — Image proxy downloads full body before size check
**Lines:** ~1369  
**Problem:** Oversized images fully downloaded into memory.  
**Fix:** Use `stream=True`. Check `Content-Length` header before reading body.

## Bug 1.18 — MEDIUM — Concurrent file write race in image cache
**Lines:** ~1381–1382  
**Problem:** Two threads writing same cache file simultaneously.  
**Fix:** Write to `.tmp` file first, then `os.replace()`.

## Bug 1.19 — MEDIUM — Empty Persian translation served instead of English fallback
**Lines:** ~1440  
**Problem:** When translation fails, empty string is returned.  
**Fix:** `table.get(val.get('en')) or val.get('en') or ''`.

## Bug 1.20 — MEDIUM — FA_REPORT_CACHE written without lock
**Lines:** ~1447  
**Problem:** Concurrent translation requests race on cache write.  
**Fix:** Wrap in `_FA_REPORT_LOCK`.

## Bug 1.21 — LOW — Redundant import every cycle
**Lines:** ~285  
**Fix:** Move `from database import hidden_ids` to module top.

## Bug 1.22 — LOW — Auth token read from env on every request
**Lines:** ~571  
**Fix:** Cache at startup: `_MOHMD_TOKEN = os.environ.get('MOHMD_TOKEN', '').strip()`.

---

# Section 2 — `app.py` (lines 801–1600)

## Bug 2.1 — HIGH — `api_recover` TOCTOU race
**Lines:** ~1872  
**Problem:** Two POST requests can both see `running=False` and both start recovery workers.  
**Fix:** Use `_RECOVER_LOCK` for the check-then-set.

## Bug 2.2 — HIGH — RECOVERY_JOB mutated under wrong lock
**Lines:** ~1876–1942  
**Problem:** `_recover_view` reads under `_RECOVER_LOCK` but worker mutates under a local `job_lock`. Different locks = torn state.  
**Fix:** Use `_RECOVER_LOCK` consistently in both reader and writer.

## Bug 2.3 — HIGH — api_settings mutates CONFIG without lock
**Lines:** ~1959–2108  
**Problem:** Flask request threads write to CONFIG while background threads read it.  
**Fix:** All CONFIG writes in `api_settings` must be under `_CONFIG_LOCK`.

## Bug 2.4 — HIGH — IDEA_FA_CACHE check-then-act race
**Lines:** ~1620–1636  
**Problem:** `_IDEA_INFLIGHT` check and `.add()` are not atomic.  
**Fix:** Use a lock around the check-then-act sequence.

## Bug 2.5 — HIGH — FA_CONTENT_CACHE / _ART_INFLIGHT race
**Lines:** ~3131–3153  
**Problem:** Same check-then-act race as Bug 2.4.  
**Fix:** Same fix — use lock.

## Bug 2.6 — MEDIUM — CONTENT_CACHE write inside extraction thread
**Lines:** ~3109  
**Problem:** Background thread writes while Flask threads read.  
**Fix:** Wrap in `_CONTENT_LOCK`.

## Bug 2.7 — MEDIUM — Custom source key hash collision
**Lines:** ~2072  
**Problem:** `hash(url)` collision overwrites existing source silently.  
**Fix:** Use `'custom_' + uuid.uuid4().hex[:8]`.

## Bug 2.8 — MEDIUM — save_cache() called from multiple threads
**Lines:** ~1631, ~3142  
**Problem:** Concurrent file writes.  
**Fix:** Use a `threading.Lock` around `save_cache()`.

## Bug 2.9 — MEDIUM — warm_article_bodies unbounded busy-wait
**Lines:** ~3192  
**Problem:** `while len(_ART_INFLIGHT) >= 6: time.sleep(0.5)` blocks forever if jobs stall.  
**Fix:** Add a max wait of 60 seconds: `waited = 0; while ... and waited < 60: time.sleep(0.5); waited += 0.5`.

## Bug 2.10 — MEDIUM — api_settings exposes telegram token
**Lines:** ~2108  
**Problem:** Response includes full CONFIG with `telegram_secret` and `telegram_chat_id`.  
**Fix:** Filter sensitive keys before serializing: `safe = {k: v for k, v in CONFIG.items() if k not in ('telegram_secret', 'telegram_chat_id')}`.

## Bug 2.11 — MEDIUM — Telegram digest hard-truncated at 4000
**Lines:** ~1744  
**Problem:** Cuts mid-HTML-tag. Telegram limit is 4096.  
**Fix:** Truncate at 4096, and before truncating, find the last `</p>` or `</b>` before the limit.

## Bug 2.12 — MEDIUM — _save_newslinks TOCTOU
**Lines:** ~2244–2252  
**Problem:** Snapshot under lock, write outside lock.  
**Fix:** Keep lock held during file write, or use atomic write pattern.

## Bug 2.13 — LOW — Pre-warm thread swallows exceptions
**Lines:** ~3236  
**Fix:** Wrap each call in try/except with logging.

## Bug 2.14 — LOW — ThreadPoolExecutor per _bounded() call
**Lines:** ~2175–2189  
**Fix:** Use a module-level shared pool, or accept the overhead (low priority).

---

# Section 3 — `app.py` (lines 1601–3286)

## Bug 3.1 — CRITICAL — pinChatMessage uses GET
**Lines:** ~1787–1788  
**Problem:** Telegram API requires POST for pinChatMessage.  
**Fix:** Change `requests.get(` to `requests.post(`.

## Bug 3.2 — CRITICAL — fetch_article_content crashes on None URL
**Lines:** ~2905, ~2912, ~2922  
**Problem:** `urlparse(None)` raises AttributeError. `'x' in None` raises TypeError.  
**Fix:** Add guard at function entry:
```python
if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
    return {"paragraphs": [], "word_count": 0, "partial": True, "title": "", "url": url or "", "method": "none"}
```

## Bug 3.3 — HIGH — SSRF via redirect following
**Lines:** ~1335–1387  
**Problem:** `_blocked_host()` checks initial URL, but redirects go to internal addresses (e.g., `169.254.169.254`).  
**Fix:** Use `allow_redirects=False`. Check Location header on each redirect hop.

## Bug 3.4 — HIGH — DNS rebinding bypasses SSRF
**Lines:** ~1353  
**Problem:** `getaddrinfo()` resolves at check time; `requests.get()` resolves again independently.  
**Fix:** Resolve once, connect to the resolved IP directly, or pin the resolved IP in the request.

## Bug 3.5 — HIGH — No rate limiting on /api/refresh
**Lines:** ~1510–1513  
**Problem:** Any client can POST repeatedly to exhaust resources.  
**Fix:** If `STATE['stats']['cycle_running']` is True, return `429`. Or track last refresh timestamp.

## Bug 3.6 — HIGH — run_cycle in daemon thread swallows exceptions
**Lines:** ~1512  
**Problem:** `except Exception: pass` in thread target.  
**Fix:** Add `except Exception as e: log(f"  x cycle crashed: {e}")`.

## Bug 3.7 — MEDIUM — Falsy-zero in `now` parameter
**Lines:** ~1029  
(Already covered in Section 1 Bug 1.11)

## Bug 3.8 — MEDIUM — Translation failure produces blank Persian
**Lines:** ~1440  
(Already covered in Section 1 Bug 1.19)

## Bug 3.9 — LOW — api_econ inconsistent error response
**Lines:** ~1574–1575  
**Problem:** Error state mixed with live data.  
**Fix:** If `ctx` has an error key, return the error response without attaching live data.

## Bug 3.10 — LOW — `FA_REPORT_CACHE` None stamp comparison
**Lines:** ~1426  
**Problem:** If `generated_at` is None, cache never hits.  
**Fix:** Guard: `if rep.get('generated_at') is None: pass` (skip caching).

---

# Section 4 — `sources.py`

## Bug 4.1 — HIGH — Regex typo: `malf?are` does not match "malware"
**Line:** 48  
**Problem:** `malf?are` matches "malare" / "malfare" but never "malware" (has 'w', not 'f').  
**Fix:** Change `malf?are` to `mal(?:w|f)are` in the `security` topic keyword pattern.

## Bug 4.2 — HIGH — Missing trailing `\b` on "solana"
**Line:** 66  
**Problem:** `\b(?:solana|sol\b)` — "solana" branch has no trailing `\b`. Matches "solanas", "solanaist".  
**Fix:** `\b(?:solana|sol)\b`

## Bug 4.3 — HIGH — Missing trailing `\b` on "cardano"
**Line:** 68  
**Problem:** Same as 4.2 for "cardano".  
**Fix:** `\b(?:cardano|ada)\b`

## Bug 4.4 — MEDIUM — Missing trailing `\b` on "bnb", "dogecoin"
**Lines:** 69–70  
**Problem:** "bnb" and "dogecoin" can match inside longer words.  
**Fix:** Add `\b` after each alternative: `\b(?:bnb|binance coin|binance smart chain|bsc)\b` and `\b(?:dogecoin|doge)\b`

## Bug 4.5 — HIGH — `re.escape` space-replacement is a no-op on Python 3.7+
**Line:** 577  
**Problem:** `re.escape()` no longer escapes spaces. `.replace('\\ ', '\\s+')` never finds a match.  
**Fix:** `re.sub(r'\s+', r'\\s+', re.escape(k))`

## Bug 4.6 — LOW — Dead code in pivot_levels
**Lines:** 116–123  
**Problem:** `lo` and `hi` computed but never used.  
**Fix:** Delete those two lines.

## Bug 4.7 — LOW — RSI returns 100.0 when both gains and losses are zero
**Line:** 45–46  
**Problem:** Flat market (no movement) reports RSI=100 instead of ~50.  
**Fix:** `if avg_loss == 0 and avg_gain == 0: return 50.0`

---

# Section 5 — `scraper.py`

## Bug 5.1 — HIGH — `urllib3.disable_warnings()` permanently disables SSL warnings
**Line:** 584–585  
**Problem:** Global, irreversible. Masks real SSL issues in other code paths.  
**Fix:** Remove this line. If warnings are noisy, suppress them locally only.

## Bug 5.2 — HIGH — `socket.setdefaulttimeout(12)` permanently changes global timeout
**Line:** 619  
**Problem:** All subsequent socket operations inherit this 12s timeout.  
**Fix:** Save and restore: `old = socket.getdefaulttimeout(); socket.setdefaulttimeout(12); try: ... finally: socket.setdefaulttimeout(old)`.

## Bug 5.3 — MEDIUM — 304 returns ok=True with empty articles
**Lines:** 691–694  
**Problem:** Conditional GET 304 makes feed look healthy but contributes zero articles.  
**Fix:** Set `status['not_modified'] = True` and keep `ok` based on whether we have cached articles from a previous successful fetch (stored in `_COND[key]['count']`).

## Bug 5.4 — MEDIUM — Dedup key truncated to 64 chars causes false-positive dedup
**Line:** 787  
**Problem:** Two articles with same first 64 alphanumeric chars are incorrectly deduped.  
**Fix:** Change `[:64]` to `[:128]` or hash the full cleaned title.

## Bug 5.5 — MEDIUM — Articles without published_ts bypass freshness cutoff
**Line:** 821  
**Problem:** `published_ts=None` → age=None → never checked. Old articles enter pipeline.  
**Fix:** If `published_ts` is None, set it to `now.timestamp()` so it starts with age=0, or reject the article.

## Bug 5.6 — MEDIUM — OG_CACHE race condition
**Lines:** 172–173  
**Problem:** Multiple threads check `if link in _OG_CACHE` simultaneously, all miss, all fetch.  
**Fix:** Add `_OG_LOCK = threading.Lock()` and check+set atomically, or use `dict.setdefault`.

---

# Section 6 — `translate.py`

## Bug 6.1 — LOW — `_DIRTY` flag written outside lock
**Line:** 208  
**Fix:** Move `_DIRTY = True` inside the existing `_LOCK` block.

---

# Section 7 — `market_data.py`

## Bug 7.1 — MEDIUM — No defensive access on nested Yahoo response
**Line:** 102  
**Problem:** `r.json()['chart']['result'][0]` assumes specific structure. Error responses crash with opaque errors.  
**Fix:** The outer try/except catches it, but add explicit check: `data = r.json().get('chart', {}).get('result'); if not data: return None`.

---

# Section 8 — `indicators.py`

## Bug 8.1 — HIGH — `tail()` padding is a no-op
**Line:** 215  
**Problem:** `([-0.0] * 0) + seq` equals just `seq`. Chart series misalign with dates array.  
**Fix:** `return seq[-points:] if len(seq) >= points else [None] * (points - len(seq)) + seq`

## Bug 8.2 — MEDIUM — RSI 100.0 when both gains and losses are zero
**Line:** 45–46  
(Covered in Section 4 Bug 4.7 — same fix needed here too)

## Bug 8.3 — LOW — `pct()` treats price=0 as invalid
**Line:** 103  
**Problem:** `if not b` is True for `b=0.0`.  
**Fix:** `if b == 0: return None`

---

# Section 9 — `report_generator.py`

## Bug 9.1 — MEDIUM — `a['title']` without `.get()` in sec_macro
**Line:** 259  
**Problem:** KeyError if article has no 'title' key.  
**Fix:** `a.get('title', '')`

## Bug 9.2 — LOW — `_DERIV_CACHE` not thread-safe
**Line:** 302  
**Problem:** Multiple Flask threads can race on check-then-act TTL pattern.  
**Fix:** Add a `_DERIV_LOCK = threading.Lock()` and wrap access.

---

# Section 10 — `database.py`

## Bug 10.1 — MEDIUM — ON CONFLICT updates only 5 of ~20 columns
**Lines:** 220–233  
**Problem:** On re-scrape, `title`, `link`, `source_name`, `published_ts`, `source_trust`, `tier`, `topic`, `topic_fa` are never updated.  
**Fix:** Add these columns to the ON CONFLICT DO UPDATE SET clause.

## Bug 10.2 — MEDIUM — SQLite connections never closed
**Lines:** 43, 107, 119, 142, 161, 219, 298  
**Problem:** `with get_connection() as conn:` commits/rollbacks but does NOT close the connection. File descriptor leak over time.  
**Fix:** Add `conn.close()` in a finally block, or create a proper context manager:
```python
@contextmanager
def db_conn():
    conn = sqlite3.connect(str(DB_FILE), timeout=15)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()
```

---

# Section 11 — `fa_format.py`

## Bug 11.1 — MEDIUM — `fa_ago` returns "۱ دقیقه پیش" for negative hours
**Lines:** 107–109  
**Problem:** Future timestamps (negative hours) produce misleading output.  
**Fix:** Add at function start: `if hours is not None and hours < 0: return ""`

## Bug 11.2 — LOW — `fa_ago(0)` returns "۱ دقیقه پیش"
**Line:** 112  
**Problem:** Zero-age article says "1 minute ago".  
**Fix:** `if hours is not None and hours < 0.017: return "۱ دقیقه پیش"`

## Bug 11.3 — LOW — `to_tehran` silently assumes naive datetime is UTC
**Line:** 63  
**Fix:** Add a comment warning, or log when a naive datetime is received.

---

# Section 12 — `calendar_data.py`

## Bug 12.1 — MEDIUM — Naive datetime in `_calendar_json_mirror`
**Line:** 812  
**Problem:** `datetime.fromisoformat(it['date']).astimezone(timezone.utc)` assumes naive = local timezone.  
**Fix:** `dt = datetime.fromisoformat(it['date']).replace(tzinfo=timezone.utc)` (assume UTC).

## Bug 12.2 — LOW — Cache timestamp set before network calls complete
**Lines:** 886–888  
**Problem:** TTL is shorter than intended.  
**Fix:** Move `CACHE['ts'] = now` and `CACHE['data'] = data` to after all network calls.

---

# Section 13 — `news_bypass.py`

## Bug 13.1 — MEDIUM — Google Cache URL not percent-encoded
**Line:** 359  
**Problem:** Article URL with `&`, `#`, or spaces breaks the query string.  
**Fix:** `from urllib.parse import quote_plus; return f'https://webcache.googleusercontent.com/search?q=cache:{quote_plus(url)}&strip=1'`

## Bug 13.2 — MEDIUM — `cloudscraper.create_scraper()` not guarded
**Line:** 268  
**Problem:** If cloudscraper dependencies are broken, entire reader instantiation crashes.  
**Fix:** Wrap in try/except: `try: self.scraper = cloudscraper.create_scraper(); except: self.scraper = None`

## Bug 13.3 — MEDIUM — Jina reader URL not percent-encoded
**Line:** 448  
**Problem:** URLs with special characters produce malformed requests.  
**Fix:** `from urllib.parse import quote; self.session.get(f'https://r.jina.ai/{quote(url, safe=":/?#[]@!$&\'()*+,;=-_.~")}', ...)`

---

# Section 14 — `tv_ideas.py`

## Bug 14.1 — MEDIUM — Bracket-matching JSON extractor ignores string context
**Lines:** 70–79  
**Problem:** Counts `[` and `]` without accounting for strings containing brackets.  
**Fix:** Replace with `json.JSONDecoder().raw_decode()`:
```python
decoder = json.JSONDecoder()
try:
    obj, end = decoder.raw_decode(seg, start)
    if isinstance(obj, list):
        return obj
except:
    pass
```

## Bug 14.2 — LOW — timestamp=0 treated as falsy
**Lines:** 183–184  
**Problem:** `if ts else None` treats 0 as missing.  
**Fix:** `if ts is not None else None`

---

# Section 15 — `smoke_test.py`

## Bug 15.1 — HIGH — Unconditional access to BTC report crashes on error
**Lines:** 84–85  
**Problem:** Lines outside error guard access `reps['BTC']['sections'][0][1]['asof_fa']`. If BTC report failed, KeyError.  
**Fix:** Wrap in:
```python
btc = reps.get('BTC', {})
if btc and not btc.get('error'):
    print(...)
    # access asof_fa safely
```

## Bug 15.2 — LOW — List bounds not checked
**Lines:** 70  
**Problem:** `c["items"][i+1]` can IndexError if list has 1 item.  
**Fix:** Add `if len(c["items"]) > 1` guard.

---

# Section 16 — `dashboard_html.py` (JavaScript)

## Bug 16.1 — CRITICAL — `esc()` does not escape single quotes
**Line:** ~2545  
**Problem:** Article IDs are interpolated into `onclick="openArticle('${a.id}')"` handlers. A `'` in the ID breaks out and injects JavaScript.  
**Fix:** In the `esc()` function, add: `s = s.replace(/'/g, "\\'");` after the existing replacements.

## Bug 16.2 — HIGH — Article modal poll not cancelled on close
**Lines:** ~3168–3179  
**Problem:** `openArticle()` starts recursive `setTimeout(poll, 1200)` that writes to `#artBody`. Closing the modal never cancels the poll. Opening article B after A causes A's poll to overwrite B's content.  
**Fix:** Add a generation counter:
```javascript
let _ART_GEN = 0;
function openArticle(id) {
    const gen = ++_ART_GEN;
    // ... in the poll callback:
    if (_ART_GEN !== gen) return;
    // ... existing code ...
}
```

## Bug 16.3 — HIGH — Dual setInterval triggers concurrent loadData()
**Lines:** ~2690–2694  
**Problem:** Both 60s idle timer and 20s active timer call `loadData()` without dedup.  
**Fix:** Add `let _LOADING = false;` at top. At start of `loadData()`: `if (_LOADING) return; _LOADING = true;`. In finally: `_LOADING = false;`.

## Bug 16.4 — MEDIUM — renderFeed crashes before DATA loads
**Lines:** ~3011–3017  
**Problem:** `renderFeed()` accesses `DATA.articles` before `loadData()` completes.  
**Fix:** First line of `renderFeed()`: `if (!DATA || !DATA.articles) return;`

## Bug 16.5 — MEDIUM — Calendar event index goes stale after re-render
**Lines:** ~3662, ~3760  
**Problem:** `e._idx = pool.length` captures position. After `renderCalendar()` re-runs, indices shift.  
**Fix:** Use a unique key: `e._key = (e.ts || 0) + '_' + (e.title || '').replace(/[^a-zA-Z0-9]/g, '').slice(0, 20);` Then `onclick="openCalDoc('${e._key}')"` and match by key.

## Bug 16.6 — MEDIUM — Recovery poll writes to detached DOM node
**Lines:** ~2837–2850  
**Problem:** After `renderAll()`, the captured `#recoverBtn` reference may be detached.  
**Fix:** Inside the setInterval callback, re-query: `const b = document.getElementById('recoverBtn'); if (!b) return;`

## Bug 16.7 — LOW — pollLive silently swallows all errors
**Lines:** ~2906–2910  
**Fix:** Add `console.error('pollLive:', e)` inside the catch block.

## Bug 16.8 — LOW — toggleSrc shows success toast before await
**Lines:** ~2959–2961  
**Fix:** Move `toast(...)` after `await postSettings(...)`. Wrap in try/catch.

## Bug 16.9 — LOW — removeAsset doesn't await loadData
**Lines:** ~3502–3504  
**Fix:** `await loadData()` instead of `loadData()`.

## Bug 16.10 — LOW — loadData doesn't check HTTP status
**Lines:** ~2677–2688  
**Fix:** After `fetch()`, add: `if (!r.ok) throw new Error(r.status + ' ' + r.statusText);`

---

# Copy-Paste Prompt: Fix app.py (All Bugs)

```
Fix the following bugs in E:/freebuff/app.py. ONLY modify the specific lines listed for each bug. Do NOT refactor, restructure, or change anything else.

BUG 1 (Critical, ~line 391): Articles placed into STATE['articles'] must be deep-copied so translation doesn't mutate live data. Before the line that does STATE['articles'] = live (or similar), add:
  live = [json.loads(json.dumps(a)) for a in live]

BUG 2 (Critical, ~line 382): Add three locks at module level:
  _CONTENT_LOCK = threading.Lock()
  _FA_CONTENT_LOCK = threading.Lock()
  _FA_REPORT_LOCK = threading.Lock()
Then wrap every access to CONTENT_CACHE, FA_CONTENT_CACHE, and FA_REPORT_CACHE (reads, writes, pops, clears) in the corresponding lock. Be careful not to nest locks.

BUG 3 (High): Add _CONFIG_LOCK = threading.Lock() at module level. Wrap all CONFIG reads in run_cycle/scheduler_loop and all CONFIG writes in api_settings under this lock.

BUG 4 (High, ~line 800): Add _LIVE_LOCK = threading.Lock(). In live_prices(), make the busy-flag check-then-set atomic:
  with _LIVE_LOCK:
      if LIVE_CACHE.get('busy'):
          return LIVE_CACHE.get('data', {})
      LIVE_CACHE['busy'] = True
Also wrap LIVE_CACHE['ts'] and LIVE_CACHE['data'] writes in _LIVE_LOCK.

BUG 5 (Critical, ~line 1787): Change requests.get() to requests.post() for pinChatMessage Telegram API call.

BUG 6 (Critical, ~line 2905): Add at the top of fetch_article_content():
  if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
      return {"paragraphs": [], "word_count": 0, "partial": True, "title": "", "url": url or "", "method": "none"}

BUG 7 (High, ~line 1335): In api_proxy_image(), change requests.get(..., allow_redirects=True) to allow_redirects=False. Then manually follow redirects (check Location header, validate host with _blocked_host, max 3 hops).

BUG 8 (High, ~line 1510): In the /api/refresh endpoint, check STATE['stats']['cycle_running'] first. If True, return jsonify({"ok": False, "error": "cycle already running"}), 429.

BUG 9 (Medium, ~line 2108): In api_settings response, filter sensitive keys before jsonify:
  safe = {k: v for k, v in CONFIG.items() if k not in ('telegram_secret', 'telegram_chat_id')}

BUG 10 (Medium, ~line 442): Remove the intermediate last_duration update. Set STATE['stats']['last_duration'] only once at the very end of run_cycle, after all work (translation + reports) is done.

BUG 11 (Medium, ~line 388): Delete the FA_REPORT_CACHE.clear() line. Let TTL handle expiry.

BUG 12 (Medium, ~line 422): Before spawning the warming thread, check if it's still alive: if warming_thread and warming_thread.is_alive(): skip spawning.

BUG 13 (Medium, ~line 400): Change `except Exception: pass` to `except Exception as e: log(f"  x report save failed: {e}")`.

BUG 14 (Medium, ~line 624): Change `stats = dict(STATE['stats'])` to `stats = json.loads(json.dumps(STATE['stats']))`.

BUG 15 (Medium, ~line 1029): Change `now = now or time.time()` to `if now is None: now = time.time()`.

BUG 16 (Medium, ~line 1102): Change the cache-hit check from `not MACRO_CACHE['data']` to `MACRO_CACHE['data'] is None`.

BUG 17 (Medium): For CANDLES_CACHE, add a cap: if len(CANDLES_CACHE) > 200, delete the entry with the oldest 'ts'. Also add a _CANDLES_INFLIGHT = set() to prevent thundering herd.

BUG 18 (Medium): Replace all `a['id']` and `art['id']` accesses (around lines 1216, 1253, 1297) with `a.get('id')` / `art.get('id')` and skip if None.

BUG 19 (Medium, ~line 1369): In api_proxy_image, use stream=True in requests.get(). Check Content-Length header before reading body. Max 5MB.

BUG 20 (Medium, ~line 1381): Write image cache to .tmp file first, then os.replace().

BUG 21 (Medium, ~line 1440): Change translation fallback from empty string to English original: use `table.get(val.get('en')) or val.get('en') or ''`.

BUG 22 (Medium, ~line 1447): Wrap FA_REPORT_CACHE write in _FA_REPORT_LOCK.

BUG 23 (Low, ~line 285): Move `from database import hidden_ids as _hidden_ids` to module-level imports.

BUG 24 (Low): Cache MOHMD_TOKEN at module level: `_MOHMD_TOKEN = os.environ.get("MOHMD_TOKEN", "").strip()` and use _MOHMD_TOKEN instead of os.environ.get() in the guard function.

After all changes, verify: python -c "from app import app; print('ok')"
```

---

# Copy-Paste Prompt: Fix sources.py

```
Fix the following bugs in E:/freebuff/sources.py. ONLY modify the specific lines listed. Do NOT refactor or change anything else.

BUG 1 (High, line 48): In the security topic regex, change `malf?are` to `mal(?:w|f)are` so it matches "malware".

BUG 2 (High, line 66): Change `\b(?:solana|sol\b)` to `\b(?:solana|sol)\b` — move the trailing \b outside the group.

BUG 3 (High, line 68): Change `\b(?:cardano|ada\b)` to `\b(?:cardano|ada)\b`.

BUG 4 (Medium, lines 69-70): Add trailing \b after each group:
  Line 69: `\b(?:bnb|binance coin|binance smart chain|bsc)\b`
  Line 70: `\b(?:dogecoin|doge)\b`

BUG 5 (High, line 577): In build_custom_patterns, change:
  pats.append(re.escape(k).replace(r'\ ', r'\s+'))
to:
  pats.append(re.sub(r'\s+', r'\\s+', re.escape(k)))

BUG 6 (Low, lines 116-123): Delete the lines `lo = min(window)` and `hi = max(window)` in pivot_levels — they are unused.

BUG 7 (Low, lines 45-46): In rsi_wilder, change:
  if avg_loss == 0: return 100.0
to:
  if avg_loss == 0 and avg_gain == 0: return 50.0
  if avg_loss == 0: return 100.0

After changes, verify: python -c "from sources import SOURCES, ASSETS; print(f'{len(SOURCES)} sources, {len(ASSETS)} assets')"
```

---

# Copy-Paste Prompt: Fix scraper.py

```
Fix the following bugs in E:/freebuff/scraper.py. ONLY modify the specific lines listed. Do NOT refactor.

BUG 1 (High, ~line 584): Remove the `urllib3.disable_warnings()` call entirely.

BUG 2 (High, ~line 619): Replace `socket.setdefaulttimeout(12)` with:
  old_timeout = socket.getdefaulttimeout()
  socket.setdefaulttimeout(12)
  try:
      feed = feedparser.parse(...)
  finally:
      socket.setdefaulttimeout(old_timeout)

BUG 3 (Medium, ~line 262): Change log label from "backoff-4s" to "backoff-3s" to match the actual 3-second sleep.

BUG 4 (Medium, ~line 787): Change `[:64]` to `[:128]` in the dedup key truncation.

BUG 5 (Medium, ~line 821): After the age check, add:
  if pub_ts is None:
      pub_ts = now.timestamp()

BUG 6 (Medium, ~line 172): Add `_OG_LOCK = threading.Lock()` and wrap the OG_CACHE check+set+fetch in it.

After changes, verify: python -c "from scraper import scrape_all; print('ok')"
```

---

# Copy-Paste Prompt: Fix indicators.py, report_generator.py, database.py

```
Fix the following bugs across three files. ONLY modify the specific lines listed.

=== E:/freebuff/indicators.py ===

BUG 1 (High, line 215): In chart_payload's inner tail() function, change:
  return seq[-points:] if len(seq) >= points else ([-0.0] * 0) + seq
to:
  return seq[-points:] if len(seq) >= points else [None] * (points - len(seq)) + seq

BUG 2 (Low, line 103): In pct(), change `if not b:` to `if b == 0:`

=== E:/freebuff/report_generator.py ===

BUG 3 (Medium, line 259): Change `a['title']` to `a.get('title', '')`

=== E:/freebuff/database.py ===

BUG 4 (Medium, lines 220-233): In the INSERT ... ON CONFLICT DO UPDATE clause in save_articles, add these columns to the UPDATE SET:
  title = excluded.title,
  link = excluded.link,
  source_key = excluded.source_key,
  source_name = excluded.source_name,
  published_ts = excluded.published_ts,
  source_trust = excluded.source_trust,
  tier = excluded.tier,
  topic = excluded.topic,
  topic_fa = excluded.topic_fa

BUG 5 (Medium): Create a proper context manager for database connections:
  import contextlib
  
  @contextlib.contextmanager
  def _db_conn():
      conn = sqlite3.connect(str(DB_FILE), timeout=15)
      conn.execute("PRAGMA journal_mode = WAL;")
      conn.execute("PRAGMA synchronous = NORMAL;")
      conn.execute("PRAGMA busy_timeout = 10000;")
      conn.row_factory = sqlite3.Row
      try:
          yield conn
          conn.commit()
      except:
          conn.rollback()
          raise
      finally:
          conn.close()
  
  def get_connection():
      return _db_conn().__enter__()

After changes, verify each file:
  python -c "from indicators import snapshot; print('ok')"
  python -c "from report_generator import build_all_reports; print('ok')"
  python -c "from database import init_db; print('ok')"
```

---

# Copy-Paste Prompt: Fix fa_format.py, calendar_data.py, translate.py, market_data.py

```
Fix the following bugs across four files. ONLY modify the specific lines listed.

=== E:/freebuff/fa_format.py ===

BUG 1 (Medium, line ~107): In fa_ago(), add at the very beginning of the function (after the None check):
  if isinstance(hours, (int, float)) and hours < 0:
      return ""

=== E:/freebuff/calendar_data.py ===

BUG 2 (Medium, line ~812): In _calendar_json_mirror(), change:
  dt = datetime.fromisoformat(it["date"]).astimezone(timezone.utc)
to:
  naive = datetime.fromisoformat(it["date"])
  dt = naive.replace(tzinfo=timezone.utc) if naive.tzinfo is None else naive.astimezone(timezone.utc)

=== E:/freebuff/translate.py ===

BUG 3 (Low, line ~208): Move `_DIRTY = True` inside the `with _LOCK:` block that already exists nearby.

=== E:/freebuff/market_data.py ===

BUG 4 (Medium, line ~102): After `r.raise_for_status()`, add:
  data = r.json().get("chart", {}).get("result")
  if not data:
      return None
  res = data[0]
  (Then remove the old `res = r.json()["chart"]["result"][0]` line.)

After changes, verify:
  python -c "from fa_format import fa_ago; print(fa_ago(-1), fa_ago(0), fa_ago(3))"
  python -c "from calendar_data import market_context; print('ok')"
```

---

# Copy-Paste Prompt: Fix news_bypass.py, tv_ideas.py

```
Fix the following bugs across two files. ONLY modify the specific lines listed.

=== E:/freebuff/news_bypass.py ===

BUG 1 (Medium, line ~359): In _google_cache(), import quote_plus and encode the URL:
  from urllib.parse import quote_plus
  return f"https://webcache.googleusercontent.com/search?q=cache:{quote_plus(url)}&strip=1"

BUG 2 (Medium, line ~268): Wrap cloudscraper.create_scraper() in try/except:
  try:
      self.scraper = cloudscraper.create_scraper()
  except Exception:
      self.scraper = None

=== E:/freebuff/tv_ideas.py ===

BUG 3 (Medium, lines ~70-79): Replace the manual bracket-matching loop in _extract_items() with:
  try:
      decoder = json.JSONDecoder()
      obj, _ = decoder.raw_decode(seg, start)
      if isinstance(obj, list):
          return obj
  except Exception:
      return []
  return []

BUG 4 (Low, line ~183): Change `if ts else None` to `if ts is not None else None`

After changes, verify:
  python -c "from news_bypass import smart_extract; print('ok')"
  python -c "from tv_ideas import fetch_ideas; print('ok')"
```

---

# Copy-Paste Prompt: Fix dashboard_html.py (JavaScript)

```
Fix the following bugs in E:/freebuff/dashboard_html.py (the JavaScript section). ONLY modify the specific lines listed. Do NOT refactor the HTML or CSS.

BUG 1 (Critical, ~line 2545): In the esc() function, add after the existing escape lines:
  s = s.replace(/'/g, "\\'");

BUG 2 (High, ~line 3168): Add a generation counter to prevent stale article poll:
  At the top of the <script> section, add: let _ART_GEN = 0;
  In openArticle(), at the very start, add: const gen = ++_ART_GEN;
  In the poll callback (inside setTimeout), at the very start of the callback, add: if (_ART_GEN !== gen) return;

BUG 3 (High, ~line 2690): Add a loading guard:
  At the top of the <script> section, add: let _LOADING = false;
  At the very start of loadData(), add: if (_LOADING) return; _LOADING = true;
  At the very end (in finally or after all work): _LOADING = false;

BUG 4 (Medium, ~line 3011): At the very start of renderFeed(), add:
  if (!DATA || !DATA.articles) return;

BUG 5 (Medium, ~line 3662): Change index-based calendar event lookup to key-based:
  When building the pool, use: e._key = (e.ts||0) + '_' + (e.title||'').replace(/[^a-zA-Z0-9]/g,'').slice(0,20);
  In the onclick HTML: onclick="openCalDoc('${e._key}')"
  In openCalDoc(), change index lookup to: const e = CAL_POOL.find(x => x._key === key);

BUG 6 (Medium, ~line 2837): In the setInterval callback for recovery poll, re-query the DOM element each time:
  const b = document.getElementById('recoverBtn');
  if (!b) return;

BUG 7 (Low, ~line 2906): In pollLive() catch block, add: console.error('pollLive:', e);

BUG 8 (Low, ~line 2959): In toggleSrc(), wrap in try/catch and move toast after await:
  try { await postSettings(...); toast('...', 'success'); }
  catch(e) { toast('...', 'error'); }

BUG 9 (Low, ~line 3502): In removeAsset(), change loadData() to await loadData().

BUG 10 (Low, ~line 2677): After fetch() in loadData(), add: if (!r.ok) throw new Error(r.status);
```

---

# Final Verification Checklist

After applying ALL prompts, run these checks:

```bash
cd E:/freebuff

# 1. All modules import cleanly
python -c "from app import app; print('app.py OK')"
python -c "from sources import SOURCES; print('sources.py OK')"
python -c "from scraper import scrape_all; print('scraper.py OK')"
python -c "from indicators import snapshot, chart_payload; print('indicators.py OK')"
python -c "from report_generator import build_all_reports; print('report_generator.py OK')"
python -c "from database import init_db; print('database.py OK')"
python -c "from fa_format import fa_ago, fa_date; print('fa_format.py OK')"
python -c "from calendar_data import market_context; print('calendar_data.py OK')"
python -c "from news_bypass import smart_extract; print('news_bypass.py OK')"
python -c "from tv_ideas import fetch_ideas; print('tv_ideas.py OK')"
python -c "from market_data import fetch_market_data; print('market_data.py OK')"
python -c "from translate import translate_many; print('translate.py OK')"

# 2. Flask starts
python app.py --once 2>&1 | head -20

# 3. Smoke test passes
python smoke_test.py
```
