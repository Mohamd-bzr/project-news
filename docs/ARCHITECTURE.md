# MOHMD NEWS — معماری (Architecture)

> این سند جای `PROJECT_BLUEPRINT.md` را می‌گیرد و برای ایجنت‌های تغییر نوشته شده است.
> **دیگر شماره‌خط در آن نیست**: هر اشاره با نام نماد (`app.py::run_cycle`) یا بنر
> (`dashboard_html.py::══ 1 · TOKENS ══`) داده شده و با `grep -n` پیدا می‌شود. معنی لنگر:
> نزدیک‌ترین `def`/`class`/ثابت/بنر در همان خط یا پیش از آن.
> قواعد رفتاری، دروازه‌های قبل/بعد از ویرایش و خط پایهٔ اندازه‌گیری‌شده در `AGENTS.md` هستند.

---

> **این فایل برای چه کسی است؟** برای یک ایجنتِ تغییر. قواعد رفتاری، دروازه‌های قبل/بعد از
> ویرایش و خط پایهٔ اندازه‌گیری‌شده در `AGENTS.md` هستند و بر این سند مقدم‌اند.
> قالب نوشتن درخواست تغییر در §۱۶ آمده است.

---

## فهرست

1. [هویت پروژه و قواعد غیرقابل مذاکره](#۱-هویت-پروژه-و-قواعد-غیرقابل-مذاکره)
2. [اجرا، پیکربندی و متغیرهای محیطی](#۲-اجرا-پیکربندی-و-متغیرهای-محیطی)
3. [معماری کلان و مؤلفه‌ها](#۳-معماری-کلان-و-مؤلفهها)
4. [جریان داده: از منبع تا صفحه](#۴-جریان-داده-از-منبع-تا-صفحه)
5. [کاتالوگ فایل‌به‌فایل با پارتیشن داخلی](#۵-کاتالوگ-فایلبفایل-با-پارتیشن-داخلی)
6. [قراردادهای HTTP API](#۶-قراردادهای-http-api)
7. [اسکیمای SQLite](#۷-اسکیمای-sqlite)
8. [اسکیمای settings.json](#۸-اسکیمای-settingsjson)
9. [لایهٔ آفلاین: Service Worker + IndexedDB](#۹-لایهٔ-آفلاین-service-worker--indexeddb)
10. [سبک کدنویسی و کنوانسیون‌های مخزن](#۱۰-سبک-کدنویسی-و-کنوانسیونهای-مخزن)
11. [تست‌ها و CI](#۱۱-تستها-و-ci)
12. [ابزارها و اسکریپت‌های عملیاتی](#۱۲-ابزارها-و-اسکریپتهای-عملیاتی)
13. [اصطلاح‌نامهٔ فارسی ↔ انگلیسی](#۱۳-اصطلاحنامهٔ-فارسی--انگلیسی)
14. [نقاط توسعه: برای تغییر هر چیز کجا برو](#۱۴-نقاط-توسعه-برای-تغییر-هر-چیز-کجا-برو)
15. [بدهی فنی، driftها و تله‌ها](#۱۵-بدهی-فنی-driftها-و-تلهها)
16. [قالب نوشتن درخواست تغییر](#۱۶-قالب-نوشتن-درخواست-تغییر)

---

## ۱) هویت پروژه و قواعد غیرقابل مذاکره

**MOHMD NEWS** یک ترمینال اطلاعات بازار تک‌پروسس است به زبان فارسی (RTL، تم شبانه/روشن)،
ویندوز-اول، با این مشخصات ثابت:

| ویژگی | مقدار واقعی |
|---|---|
| فریمورک | Flask (WSGI) + `waitress` با ۳۲ ترد؛ fallback به سرور توسعهٔ Werkzeug |
| تعداد منابع خبری | **۱۹۴** (در `sources.SOURCES`) |
| دارایی‌های پیش‌فرض | **۱۳** (`BTC ETH SOL XRP XAU ADA BNB DOGE XAG WTI DXY SPX VIX`) |
| پنجرهٔ خبری | `MAX_AGE_HOURS = 72` |
| دورهٔ چرخه | `interval = 1800` ثانیه (۳۰ دقیقه) |
| کلید API اجباری | ندارد (Iran-friendly، همهٔ سرویس‌ها fallback دارند) |
| دیتابیس سرور | SQLite: `.mohmd_news.db` |
| دیتابیس کلاینت | IndexedDB: `MohmdNewsDB` |
| تست | **234 تست** — با `pytest tests/ -q --collect-only` بشمار |
| فایل ترک‌شده در گیت | با `git ls-files | wc -l` بشمار (عدد ثابت نگذار) |

### چهار قاعده‌ای که هر تغییر باید رعایت کند

1. **هیچ داده‌ای ساخته نمی‌شود.** جای داده‌ی گمشده نمایش صریح «شکاف/داده موجود نیست» است،
   هرگز عدد یا متن placeholder. (نمونهٔ اجرا: `card_render.py` → `CardUnavailable`؛
   `api_data` بخش خالی را با `null` می‌فرستد و UI `—` می‌کشد.)
2. **رایگان و بی‌کلید اول.** هر فراخوانی خارجی یک fallback یا مسیر دوم دارد؛ برنامه
   تنزل می‌کند و از پا نمی‌افتد (نمونه: نردبان استخراج متن در `app.py::fetch_article_content`).
3. **تک‌پروسس.** نه صف، نه DB خارجی، نه Docker، نه Redis. زمان‌بندی با `threading.Thread` daemon.
4. **توضیح‌پذیر.** هر امتیاز فاکتورهایش را سمت سرور و در payload نگه می‌دارد
   (نمونه: `channel_profile.score_article` دیکشنری دلیل برمی‌گرداند؛ `report_generator._cite` دلیل فارسی/انگلیسی هر ارجاع).

**ممنوعیت‌های سبک عملی در این مخزن:** افزودن dependency جدید بدون دلیل قوی، اضافه‌کردن build step،
دور زدن `esc()`/`Sanitizer` برای رشتهٔ ورودی، نوشتن مستقیم روی `settings.json` در تست.

---

## ۲) اجرا، پیکربندی و متغیرهای محیطی

### راه‌اندازی

```bat
:: ویندوز — دابل‌کلیک؛ venv را می‌سازد، requirements را نصب می‌کند، اجرا می‌کند
start.bat
```
```bash
# دستی
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python app.py --port 5055
```

`app.py` از `argparse` استفاده **نمی‌کند**؛ آرگومان‌ها دستی از `sys.argv` خوانده می‌شوند
(بلوک `__main__` در `app.py::__main__` تا `app.py::__main__`):

| فلگ / متغیر | اثر |
|---|---|
| `--port N` | پورت سرور (پیش‌فرض `5055`) |
| `--public` | بایند روی `0.0.0.0` به‌جای `127.0.0.1` (هشدار بلند اگر `MOHMD_TOKEN` نباشد) |
| `--once` | فقط یک چرخه اجرا کن و خارج شو (بدون زمان‌بند/SSE) |

### متغیرهای محیطی — لیست کامل و محل خوانده‌شدن

| متغیر | محل | کار |
|---|---|---|
| `MOHMD_TOKEN` | `app.py::{HEADERS, _dl2_token_guard, api_admin_keys, api_health, _warn_token_gate_exemptions, __main__}` | دروازهٔ کلید مشترک کل اپ (`_dl2_token_guard`) |
| `MOHMD_HOST` | `app.py::__main__` | جایگزین `--public` |
| `MOHMD_PROXY` | `app.py::HEADERS` | پروکسی خروجی |
| `MOHMD_JINA_KEY` | `app.py::HEADERS` | کلید اختیاری Jina Reader |
| `MOHMD_PUSH_SECONDS` | `app.py::STREAM_PUSH_SECONDS` | دورهٔ تیک SSE قیمت‌ها |
| `MOHMD_CAL_SCAN_SECONDS` | `app.py::CAL_SCAN_SECONDS` | دورهٔ پویش تقویم |
| `MOHMD_CAL_WINDOW` | `app.py::CAL_ANNOUNCE_WINDOW` | پنجرهٔ تقویم |
| `MOHMD_WS_URL` | `app.py::STREAM_WS_URL` | آدرس وب‌سوکت قیمت |
| `MOHMD_TG_TOKEN` / `MOHMD_TG_CHAT` | `app.py::_telegram_cfg` | تلگرام بدون ذخیره در فایل |
| `MOHMD_TG_GATEWAY` | `app.py::_tg_base` | درگاه Cloudflare Worker برای تلگرام (docs/telegram-gateway.md) |
| `MOHMD_TG_PROXY` | `app.py::_tg_proxies` | پروکسی تلگرام |
| `MOHMD_BALE_TOKEN` / `MOHMD_BALE_CHAT` | `app.py::_bale_cfg` | بله |
| `MOHMD_UPGRADE_TOKEN` | `app.py::api_billing_upgrade` | مجوز ارتقای tier |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` / `OPENAI_BASE_URL` | `app.py::_init_ai_config` | خلاصه‌سازی AI (اختیاری) |

### شش ترد پس‌زمینه که همیشه در حال اجرا هستند

| ترد | تابع | دوره |
|---|---|---|
| چرخهٔ خبری | `scheduler_loop` → `run_cycle` | `CONFIG['interval']` = ۱۸۰۰s |
| پوش SSE | `stream_ticker_loop` | `MOHMD_PUSH_SECONDS` |
| گرم‌کردن متن مقاله | `warm_article_bodies` | یک‌بار در بوت |
| گرم‌کردن سیگنال استودیو | `_studio_signal_loop` (داخل `__main__`) | ۳۰۰s |
| پیش‌گرم مایکرو/F&G | ترد ناشناس در `__main__` | یک‌بار در بوت |
| ارسال خبرِ جاری | `stream_push_once` | از تیک |

---

## ۳) معماری کلان و مؤلفه‌ها

```
┌──────────────────────────── تک پروسه (app.py) ────────────────────────────┐
│                                                                           │
│  Flask app (app.py::all_sources_view)                                                  │
│   ├─ _dl2_token_guard  → before_request (app.py::TOKEN_GATE_OPEN)  [دروازهٔ توکن]      │
│   ├─ _no_store         → after_request  (app.py::all_sources_view)  [Cache-Control]    │
│   ├─ ۷۰ روت (@app.route) → سرو SPA + API + SSE + webhook                  │
│   ├─ STATE {articles, archive, ...}  (app.py::STATE)   ← RAM، با STATE_LOCK  │
│   ├─ CONFIG (app.py::CONFIG)  ← settings.json، با save_config()               │
│   └─ SSE StreamManager (سقف اتصال) → /api/stream                          │
│                                                                           │
│  ترد زمان‌بند ──► run_cycle() ──► موارد زیر به ترتیب:                     │
│      1. scraper.scrape_all()            جمع‌آوری موازی ۱۹۴ منبع            │
│      2. apply_news_filter()             پاک‌سازی/درست‌کردن فیلدها           │
│      3. _translate_articles_inplace()   ترجمهٔ تیتر/خلاصه به فارسی         │
│      4. news_intelligence.record_news_events()   رویدادها + همبستگی        │
│      5. market_data.fetch_market_data()  قیمت/OHLC                        │
│      6. report_generator.build_all_reports()  گزارش نهادی دوزبانه          │
│      7. database.save_articles()        ماندگاری SQLite                   │
│      8. _post_cycle_alerts()            → _post_cycle_ideas() (بله/تلگرام) │
└───────────────────────────────────────────────────────────────────────────┘
        ▲                                    ▲
        │ fetch/SSE                          │ import (نردبان fallback)
   web/index (SPA)                      ماژول‌های دامنه:
   ├ web/sw.js          پوستهٔ آفلاین    sources / scraper / translate / sentiment
   ├ web/storage-engine IndexedDB        market_data / indicators / calendar_data
   └ web/channel.js     تب ایده‌ها       report_generator / channel_profile / news_editorial
                                         content_studio / card_render / tv_ideas / tv_ta
                                         news_bypass / news_intelligence / social_signals
                                         database / billing / middleware / link_shortener
                                         ai_features / api_docs / logging_config
```

**قاعدهٔ گراف وابستگی (مهم برای جلوگیری از حلقه):** ماژول‌های دامنه هرگز `app` را import نمی‌کنند؛
جهت وابستگی یک‌طرفه است: `app.py → domain modules`. تنها استثنا: `app.py` است که همه را می‌شناسد.
پس برای تغییر رفتار، منطق را در ماژول دامنه بگذار و `app.py` فقط روت/ارکستراسیون باشد.

---

## ۴) جریان داده: از منبع تا صفحه

### الف) چرخهٔ ۳۰ دقیقه‌ای (`run_cycle` — `app.py::run_cycle`)

1. **جمع‌آوری** — `scraper.scrape_all(max_workers=32)`
   - هر منبع از `sources.SOURCES` با یک `key` شناخته می‌شود.
   - `_fetch_one` با ETag/Last-Modified (شرطی) و circuit breaker
     (`_CIRCUIT_N=4`, backoff نمایی تا ۶ ساعت — `scraper.py::══ DL2: per-source circuit breaker ══`).
   - اگر فید بمیرد: `deep_recover` → mirror → proxy → Wayback.
   - dedupe با `sources.make_id(title, link)`؛ سقف `MAX_ARTICLES_PER_FEED = 22`.
   - خروجی: `{"articles": [...], "stats": {total, rejected, stale_rejected, irrelevant, feeds_ok, feeds_total}}`
2. **اعتبارسنجی** — `sources.validate_article` (`sources.py::validate_article`)
   - امتیاز ۰..۱ از `publisher_trust` (جدول `PUBLISHER_TRUST`, پیش‌فرض `0.64`)
     منهای جریمه‌های `QUALITY_PENALTIES`، کلیک‌بیت، اسپانسری، SEO-farm.
   - زیر `MIN_CREDIBILITY = 0.30` حذف؛ گزارش‌ها فقط از `REPORT_MIN_CREDIBILITY = 0.55` به بالا ارجاع می‌دهند.
   - `is_relevant` با الگوهای RELEVANCE/NOISE/HARD_NOISE/SPORTS_NOISE فیلتر می‌کند.
   - تشخیص دارایی: `detect_assets` (regex از `_ASSET_PATTERNS`) + الگوهای دارایی سفارشی کاربر.
   - تشخیص موضوع: `classify_topic` روی `TOPICS` (۸ موضوع: regulation, institutional, etf, macro, security, …).
3. **فیلتر دوم در اپ** — `apply_news_filter`: `news_min_chars=120` و
   حذف خبر شبکهٔ اجتماعی وقتی `news_hide_social` یا امتیاز زیر `social_score_min`.
4. **ترجمه** — `_translate_articles_inplace` → `translate.translate_many`
   - endpoint رایگان `clients5.google.com/translate_a/t`، دستهٔ ۱۶تایی، ۴ worker، کش دیسکی.
   - **دروازهٔ فارسی:** `translate.is_persian(text)` = سهم حروف فارسی ≥ `_PERSIAN_MIN_SHARE=0.45`
     و بلندترین دنبالهٔ لاتین < `_LATIN_RUN_MAX=4`. متنی که رد شود در ارسال حذف می‌شود
     («فقط فارسی بده»). این دروازه در `_post_cycle_ideas` و رندر دیجست اعمال می‌شود.
5. **هوش بازار** — `news_intelligence.record_news_events` / `update_correlation_prices`
   - `Deduplicator` (cosine روی TF برداری)، `CorrelationTracker` (خبر↔قیمت)، `AnomalyDetector` (z-score حجم).
6. **قیمت و اندیکاتور** — `market_data.fetch_market_data` → Yahoo v8 / CoinPaprika / gold-api،
   کش `.market_cache.json`. سپس `indicators.snapshot` (EMA/RSI/MACD/ATR/BB) و
   `indicators.chart_payload` (سری‌های نمودار) → `app.api_chart_data` / `app.api_candles`.
7. **گزارش** — `report_generator.build_all_reports(market_data, articles, symbols)`
   - ۱۰ بخش ثابت (`SECTION_TITLES`): نمای بازار، کلان، اثر خبر، جریان‌ها، مشتقات، تکنیکال،
     سناریوها، نتیجه… هر بخش: متن انگلیسی + ترجمهٔ فارسی + کادر `cites`
     (هر ارجاع: منبع، تیتر فارسی، تاریخ/ساعت شمسی، امتیاز اعتبار، لینک).
   - `_local_stance` با رأی TradingView مقایسه می‌کند و در
     تناقض، پاراگراف «Disagreement flag» می‌سازد (مفهوم قرض‌گرفته از kavosh، `docs/related-projects.md`).
8. **ماندگاری** — `database.save_articles`؛ بدنهٔ استخراج‌شده با `save_body`؛
   ترجمهٔ پاراگراف‌ها با کلید `"<id>|fa"`.
9. **انتشار** — `_post_cycle_alerts(articles)` (`app.py::_post_cycle_alerts`) فقط `_post_cycle_ideas` را
   صدا می‌زند؛ دیجست بسته (`_post_cycle_telegram` / `_post_cycle_bale`) به‌طور پیش‌فرض
   خاموش است (`send_digest: False`) و فقط با سوئیچ روشن می‌شود.

### ب) مسیر «ایده‌های محتوا» (قلب تفکیک این پروژه)

```
STATE["articles"]
   └─► channel_profile.rank_for_channel(articles)     امتیاز تناسب پیج + وایرال
         ├─ detect_buckets()      لِین: gold | coin | currency | global | crypto | tech
         ├─ detect_off_profile()  حذف آف‌پروفایل (میم‌کوین، ایردراپ، …)
         ├─ score_article()       امتیاز ۰..۱۰۰ با دلیل (impact, freshness, numbers…)
         └─ viral_score()         احتمال وایرال ۰..۱۰۰
   └─► app._channel_board(force)                      (app.py::_channel_board)  ← تخته، کش‌شده
   └─► app._post_cycle_ideas()                        (app.py::_post_cycle_ideas)
         ├─ لِین‌بندی round-robin تا هر دسته سرِ صف بیاید
         ├─ اخبار جهان نامحدود (بدون سقف)
         ├─ دروازهٔ فارسی: آیتم نیمه‌انگلیسی حذف یا با ترجمهٔ مجدد نجات می‌یابد
         ├─ news_editorial.detect_market_emoji → 🟡 ⚪ 💵 ₿ 🏦 📊
         ├─ news_editorial.clean_editorial_title (سقف ۱۲–۱۵ کلمه)
         ├─ news_editorial.ideas_summary → دقیقاً دو بند، سقف `IDEAS_SUMMARY_CHARS`
         ├─ link_shortener.shorten (opizo → tinyurl → isgd → custom)
         ├─ database.is_messenger_posted / mark_messenger_posted  (dedupe هر پلتفرم جدا)
         └─ _tg_send / _bale_send  با circuit breaker (`_breaker_open`, آستانه ۲ خطای اتصال)
```

قالب پیام نهایی (قرارداد تست‌شده در `tests/test_messenger_gateway.py`):

```
<b>تیتر فارسی</b>            ← یا **تیتر** برای بله

🟡 بند اول خلاصه …

‼️ بند دوم خلاصه …

🔗 https://لینک-کوتاه‌شده       ← همیشه آخرین خط، همیشه روی خط خودش
```

### ج) مسیر «متن کامل خبر» (نردبان استخراج)

`app.fetch_article_content(url, title, publisher)` (`app.py::fetch_article_content`) به ترتیب تلاش می‌کند و
اولین نتیجهٔ قابل‌قبول را برمی‌گرداند؛ هر پله timeout دارد (`_bounded`, `app.py::_bounded`):

1. `_parse_article_html` — استخراج مستقیم + JSON-LD (`_jsonld_body`) + payload‌های inline
2. `news_bypass.smart_extract` — `EnhancedNewsBypassReader` (کوکی/هدر/UA انسانی، نشانه‌های پی‌وال)
3. `trafilatura` / readability (اگر نصب باشند)
4. Jina Reader (`_jina_reader_text`) با کلید اختیاری
5. Wayback (`_wayback_html`) و آرشیوها (`_archive_ph_html`)
6. مسیر رِدیت (`_reddit_content`, `_pullpush_selftext`)
7. `_search_snippet_paragraphs` — آخرین سنگر: بازسازی از اسنیپت جستجو

نتیجه در `CONTENT_CACHE` و `FA_CONTENT_CACHE` (با قفل جدا، `app.py::_article_blurb_fa` به بعد) و در
جدول `bodies` ماندگار می‌شود تا مودال هرگز منتظر استخراج نماند (`warm_article_bodies`).

---

## ۵) کاتالوگ فایل‌به‌فایل با پارتیشن داخلی

> هر ردیف = یک بلوک داخلی فایل. جای دقیق را با `grep -n` روی همان نماد/بنر پیدا کن؛
> در این سند شماره‌خط وجود ندارد و نباید اضافه شود.

### ۵.۱ — `app.py` — ۷٬۲۶۶ خط (مونولیت ارکستراتور)

| پارتیشن |
|---|
| imports، `BASE_DIR`، `CONFIG_FILE` |
| `TG_TEMPLATE_DEFAULT`, `BALE_TEMPLATE_DEFAULT` (قالب پیام) |
| `DEFAULT_CONFIG` (کل اسکیمای تنظیمات + مقادیر پیش‌فرض) |
| `STATE` (رام: articles/archive/…) + `_sse_broadcast` |
| زیرساخت SSE: `_cal_key`, `cal_scan_and_broadcast`, `stream_push_once`, `stream_ticker_loop` |
| `load_config`, `save_config`, `log`, `_looks_crypto`, `all_assets_meta`, `market_maps`, `_init_discord_bot`, `_init_ai_config` |
| **`run_cycle` — قلب زمان‌بند (کل چرخه)** |
| `scheduler_loop` |
| `_translate_articles_inplace`, `_ser_article` (سریال‌سازی سبک برای API), `_news_window_sec`, `all_sources_view` |
| `_no_store` (after_request), `_dl2_token_guard` (before_request) |
| سرو SPA و PWA: `index`, `pwa_service_worker`, `pwa_storage_engine`, `channel_client`, `pwa_manifest`, `pwa_font`, `pwa_icon` |
| SSE: `api_stream_info`, `api_stream`, `api_stream_prices` |
| **`api_data` — بستهٔ اصلی (~۱.۷MB)** |
| `api_article_hide`, `api_article_restore`, `refilter_state`, `api_stats`, `api_chart_data`, `api_sentiment`, `api_intelligence` |
| `manifest` (مشخصات دارایی‌ها) |
| قیمت زنده: `_live_yahoo_quote`, `_live_binance`, `live_prices`, `_live_gold_api`, `_live_paprika`, `_refresh_live`, `api_etf_quotes`, `_etf_quotes` |
| احساسات دارایی: `headline_polarity`, `asset_sentiment`, `api_fng_symbol`, `api_live`, `_fng_cached`, `_macro_cached`, `_candles_cached`, `_candles_store` |
| کندل: `api_candles`, `api_assets_list` |
| **پارتیشن V1 PUBLIC API** — `# === V1 PUBLIC API (requires API key) ===`: `_hash_api_key`, `_save_api_keys`, `_load_api_keys`, `_generate_api_key`, `_check_api_key`, و روت‌های `/api/v1/*` |
| `api_docs` (Swagger)، `/api/admin/keys`، `/webhook/tv`، `/api/alerts`، `/api/ai/*` |
| Content Studio backend: `_studio_config`, `_studio_feed`, `api_studio_feed`, `api_studio_item`, `api_studio_draft`, `api_studio_drafts` |
| **`_channel_board` + `_channel_feed` + `_fast_json`** (منبع تختهٔ ایده‌ها) |
| انتشار: `_tg_send_photo`, `api_studio_publish_telegram`, `api_studio_publish_bale`, `api_studio_signals_refresh`, `api_studio_config` |
| Billing: `api_billing_tier`, `api_billing_upgrade`, `api_billing_usage` |
| مقاله: `_article_blurb_fa`, `api_article`, `api_proxy_image`, `api_report`, `translate_report`, `report_to_markdown(_fa)`, `api_report_markdown` |
| `api_refresh`, `_monitor_view`, `api_econ`, `api_ideas` |
| `api_ideas`, `_idea_paragraphs`, `_schedule_idea_fa`, `api_ideas/translate` |
| **پارتیشن پیام‌رسان — تلگرام:** `_tg_clean_token`, `_tg_clean_chat`, `class TgResult`, `_telegram_cfg`, `_tg_base` (بنگاه)، `_tg_proxies`, `_tg_parse_error`, `_tg_send`, `_tg_escape`, `_ideas_link_last`, `_tg_render_digest`، قالب بله: `_bale_*` + `_bale_render_digest`، `_studio_autopost` |
| `api_studio_autopost_now` |
| `content_studio_signals`, `_post_cycle_telegram`, `_post_cycle_bale` |
| **پارتیشن circuit breaker:** `# ── messenger circuit breaker ──` — `_breaker_open`, `_conn_error`, `_breaker_record` |
| **`_post_cycle_ideas` — ارسال ایده‌ها (مهم‌ترین تابع دامنه در app.py)** |
| `_post_cycle_alerts`, `/api/telegram/get-chat-id`, `/api/ideas/push-debug`, `/api/ideas/push-now`, `/api/ideas/dispatch-status`, `/api/ideas/send-single` |
| روت‌های تلگرام و بله (test/preview/send/send-now/get-chat-id) |
| `api_monitor`, `api_recover`, `_recover_view`, `api_recover_status` |
| **`api_settings` (POST /api/settings) — ذخیرهٔ تنظیمات + اعتبارسنجی** |
| **پارتیشن استخراج متن کامل** — JSON-LD، `_bounded`، `_looks_like_match`، کش لینک‌های گوگل‌نیوز، `decode_google_news_url`، resolverها، Jina/Wayback/proxy، رِدیت، payload-parser، `fetch_article_content`، زمان‌بندی و کش متن (`_schedule_article`, `_schedule_fa`, `article_content_cached`, `warm_article_bodies`) |
| `api_health`, `api_metrics`, `_warn_token_gate_exemptions` |
| `_graceful_shutdown` + بلوک `__main__` (بوت، hydration از SQLite، تردها، waitress) |

**وضعیت رام مهم برای تست:** `STATE` و `CONFIG`.
تست‌ها با `monkeypatch.setitem(app.CONFIG, ...)` و `monkeypatch.setattr(app, "_channel_board", lambda force=False: {...})` کار می‌کنند.

### ۵.۲ — `dashboard_html.py` (لودر) + `web/fragments/` — کل SPA

`dashboard_html.py` دیگر خودِ صفحه نیست: لودری کوتاه است که فرگمنت‌های `web/fragments/`
را به ترتیب نامِ مرتب‌شده می‌چسباند و `APP_HTML` را می‌سازد. نام هر فرگمنت در
`_EXPECTED_ORDER` قفل است، پس افزودن/حذف/تغییرنام بی‌اعلان خطا می‌دهد.
**برای عوض‌کردن UI همان فرگمنت را ویرایش کن، نه `dashboard_html.py` را.** فرگمنت‌ها
در حالت متن (`newline=None`) خوانده می‌شوند، پس LF روی لینوکس و CRLF روی ویندوز همان
`APP_HTML` را می‌سازند (اثبات برش: sha256 متن قبل و بعد از تقسیم یکی است).

| فرگمنت | بلوک |
|---|---|
| `00_head.html` | `<head>` (متا، preload فونت، manifest/icon، عنوان)، اسکریپت «تم قبل از اولین رندر»، تگ بازِ `<style>` |
| `10_style.css` | **کل CSS (۲٬۰۳۹ خط)** — خالص و بدون تگ؛ ورودی `tools/splice_theme.py` |
| `20_head_tail.html` | `</style>`، پایان `</head>`، تگ‌های خارجی `/storage-engine.js` و `/channel.js` (defer) |
| `30_body_head.html` | `<body>` + SVG sprite آیکون‌ها (`#i-mark`, `#i-news`, …) + topbar + ticker + sidebar |
| `40_nav.html` | نوار ناوبری (۱۳ `nav-item` با `data-view` و `onclick="showView('x')"`) + باز شدن ظرف نماها |
| `50_views.html` | **۱۳ `<section class="view">`** (جدول زیر) + بستن ظرف‌ها + تگ بازِ اسکریپت #۱ |
| `60_script_01.js` … `72_script_07.js` | هفت بلوک اسکریپت درون‌خطی؛ هرکدام فرگمنتی خالص از JS و مستقل قابل `node --check` |
| `61_gap_01.html` … `71_gap_06.html` | `</script>` هر بلوک + کامنت‌های بین بلوک‌ها + `<script>` بلوک بعد |
| `99_tail.html` | `</script>` بلوک آخر + `</body>` + `</html>` |

**بدهی باقی‌مانده:** بلوک #۲ (هستهٔ اپ) هنوز تنها فرگمنت بزرگ است (~۴٬۷۹۱ خط). برش داخل
آن در این پاس مجاز نبود، چون بنرهای داخلی می‌توانند وسط یک تابع بیفتند و تکه‌های ناتمام
JS بسازند؛ شکستن آن کار یک فاز جداگانه است (هر تکه باید جداگانه `node --check` شود).

**۱۳ نما (هرکدام یک `<section class="view">`):**

| نما | کار |
|---|---|
| `view-feed` | جریان خبر (کارت‌ها + اسلایدر تیتر + فیلترها) |
| `view-reports` | گزارش نهادی دوزبانه + نمودار + کادر منابع |
| `view-ideas` | ایده‌های تریدینگ‌ویو (per-asset, sort, kind) |
| `view-calendar` | تقویم اقتصادی + واکنش تاریخی قیمت به رویداد |
| `view-etf` | تابلوی نرخ زندهٔ ETF |
| `view-archive` | آرشیو |
| `view-bookmarks` | نشان‌شده‌ها |
| `view-monitor` | سلامت منابع + بازیابی |
| `view-alerts` | قواعد هشدار هوشمند |
| `view-assets` | مدیریت دارایی‌ها |
| `view-sources` | مدیریت منابع |
| `view-settings` | تنظیمات |
| `view-channel` | «ایده‌های محتوا» (تختهٔ ارسال به بله/تلگرام) |

(۱۳ آیتم نوار ناوبری؛ `assets`/`sources`/`settings` از آیتم‌های آیکونی بالای صفحه باز می‌شوند.)

**پارتیشن CSS — عنوان بنرها عیناً در فایل هستند:**

```
  0 · SELF-HOSTED FONTS (OFL)
  ══ theme header
  1 · TOKENS           ← ۵۵ متغیر --x در :root
  2 · BASE
  3 · ICONS
  4 · FORMS
  5 · BUTTONS
  6 · APP SHELL  ├ TOPBAR ├ TICKER ├ SIDEBAR ├ MAIN PANE
  7 · CHIPS, BADGES, CREDIBILITY
  8 · TOOLBAR + FILTER SHEET
  9 · PANELS
  10 · FEED
  DL4 · let the picture into the material
  11 · MODALS
  12 · TOAST
  13 · REPORTS        ├ DL4 report runs one language at a time
  14 · TRADINGVIEW IDEAS
  15 · ECONOMIC CALENDAR ├ historical price reaction
  16 · ETF BOARD
  17 · TELEGRAM DIGEST
  18 · COMMAND PALETTE (Ctrl/Cmd+K)
  19 · ACCESSIBILITY: contrast, motion, touch
  20 · PRINT
  21 · RESPONSIVE
  smart alert rules
  PWA · offline-first status
  LIVE STREAM · incremental UI
  PHONE (≤768px)
  VIRTUALISED GRIDS
  MERGED SUGGESTIONS TAB
  ══ (dark/light theme overrides)
  html[data-theme="light"] { … }   ← بلاک تم روشن تا ۲۰۶۶
```

**پارتیشن JS هسته (بلوک ۳۳۲۹–۸۱۲۰) — بنرها عیناً در فایل:**

| بخش |
|---|
| `toggleSidebar`, `toggleRail` |
| **متغیرهای وضعیت:** `DATA`, `_LOADING`, `_ART_GEN`, `UI`, `TVW`, `LIVE` |
| نگاشت‌های فارسی: `FA_TOPIC`, `FA_ASSET`, `ASSET_ICONS`, `ASSET_FA_FALLBACK`, `C`, `ASSET_ORDER`, `IMPORTANCE`, `toFa` |
| **MARKUP SAFETY — تنها دروازه بین رشتهٔ بالادست و DOM:** `sanDecode`, `esc`, `attr`, `jsLit`, `jsArg`, `safeUrl`, `Sanitizer`, `sanITagAllow/AttrAllow` |
| CLOCK — تنها تایمر صفحه (`clockFactory`) |
| VIRTUAL SCROLLER: `vsScroller`, `vsCols`, `vsLayout`, `vsWindow`, `vsMedian`, `class VirtualScroller`، `VS`/`VS_OPTS_*` |
| perf HUD، `ic()` (آیکون)، نگاشت آیکون دارایی/موضوع، `fmtPrice`, `fmtIran`, `fmtEng` |
| تبدیل جلالی در کلاینت: `g2j`, `JM`, `faDateFromIso` |
| `showView`, `loadData` |
| تیکر قیمت زنده زیر topbar: `tickerChipsHTML`, `renderTicker` |
| **«اخبار منتخب»:** `LEAD_POOL=20`, `LEAD_PER=4`, `leadScore`, `leadPick`, `leadCardHTML`, `paintLead`, `initLead`, `renderLead` |
| `renderAll`, `renderBookmarks`, `renderArchive`, `loadMonitor`, `recoverAll`, `renderMonitor`, `renderStats`, `pollLive`, `paintLive`, `flash` |
| `histSvg`, `renderSources`, `toggleSrc`, `removeSrc`, `addSource` |
| **`renderChips`** (فیلترها) |
| `renderFeed`, `credBadge`, `credChip`, **`cardHTML`** (کارت خبر)، `hideNews`, `paintHygiene`, `restoreHidden` |
| **`openArticle` + مودال مقاله** |
| **`renderRepChips`, `pickReport`, `renderChartInto`, `toggleLang`, `reportText`, `copyReport`, `renderChartPanel`** |
| `renderAssetTable`, `addAsset`, `removeAsset`, `renderSettings`, `saveSettings`, `postSettings` |
| `doRefresh`, `toast` |
| **تقویم اقتصادی و زمینهٔ بازار** — مدیریت timezone (`TZ_FMT`, `tzDay`, `calTz`)، `renderCalendar`, `renderCalHigh`، بخش واکنش تاریخی (`CAL_REACT_*`, `calReactSvg/Table/Stats`)، `openCalDoc`, `renderSessions` |
| تب ایده‌های تریدینگ‌ویو: `IDEAS_CACHE`, `IDEAS_SORTS`, `IDEAS_KINDS`, `TF_LABEL`, `ideaCardHTML`, `loadIdeas`, `openIdeaModal`, `ideaToFa` |
| تابلوی ETF زنده: `ETF_GROUP_FA`, `ETF_GROUP_ORDER`, `etfCardHTML`, `pollEtf` |
| «جدید از آخرین بازدید» + اسکلت بارگذاری (`DL2_*`) |
| دسترس‌پذیری (focus trap)، Fear & Greed، توضیح کوتاه فارسی هر خبر |
| تنظیمات دیجست تلگرام (`TG_TPL_DEFAULT`) |
| **قواعد هشدار هوشمند:** `AR_KEY`, `AR_OPS`, `AR_KINDS`, `arCondOk`, `arRuleEval`, `arEvaluate`, `arBuildCtx`, builder UI |
| تنظیمات پیام‌رسان بله (`BALE_TPL_DEFAULT`) |
| **Stream Manager کلاینت:** `SM_BACKOFF=[1000,2000,5000,10000,20000,30000]`, `SM_CHANNELS=['prices','news','calendar']`, `SM_WIRE` |
| micro-update های DOM + «the manager» |
| wiring نهایی |

پارتیشن بلوک‌های بعدی: `8127` ویجت رسمی TradingView، `8148` آزادسازی نما در خروج،
`8302` **FILTER MODEL 3** (مدل فیلتر مشترک)، `8513` Command Palette،
`8602` لایهٔ آفلاین (status indicator 8669، کپچر JSON 8696، بوت آفلاین 8835،
جستجوی full-text 8877، اعلان 8909، بوکمارک 8929، SW 8952، boot 8985).

**قراردادهای کلاینت که تست‌ها محافظت می‌کنند:**
- هر رشتهٔ ورودی **فقط** از `esc()` یا `Sanitizer` عبور می‌کند (`web/channel.js` از `window.esc` استفاده می‌کند).
- `toFa(n)` اعداد لاتین را فارسی می‌کند.
- ۹ نما از `VirtualScroller` استفاده می‌کنند (`VS.feed`, `VS.archive`, `VS.bmark`).
- تست `tests/test_dashboard_logic.py` وجود `esc`, `Sanitizer`, `toFa`, `VirtualScroller` و
  نبود تزریق ناامن را می‌سنجد.

### ۵.۳ — لایهٔ `web/` (فایل‌های جدا، چون SW باید ریشه را مالک شود)

| فایل | نقش و پارتیشن |
|---|---|
| `web/sw.js` | Service Worker. `SW_VERSION='v16'`، سه کش (`mohmd-shell-*`, `mohmd-api-*`, `mohmd-ext-*`)، `SHELL` فهرست precache، `API_MAX=80`, `EXT_MAX=40`, `NAV_TIMEOUT=4000`. استراتژی‌ها: `navigateFirst`، `networkFirst` (بدون تایم‌اوت)، `staleWhileRevalidate`. `/api/stream` دست‌نخورده. پیام‌ها: `SKIP_WAITING`, `CLEAR_API_CACHE`, `ENSURE_SHELL`, `CACHE_URLS`, `PING`→`PONG` |
| `web/storage_engine.js` | موتور IndexedDB. توابع خالص: `seTok`, `seTs`, `seArr`, `seDoc`, `seSearch`. کلاس `StorageEngine`: `open`, `putArticles`, `count`, `getArticles`, `getArticle`, `search`, `putReport/getReport/listReports`, `putCalendar/getCalendar`, `putBookmark/dropBookmark/listBookmarks/syncBookmarks`, `putMeta/getMeta`, `stats`, `prune`, `clear`. ثابت‌ها: `SE_DB_NAME='MohmdNewsDB'`, `SE_DB_VERSION=1`, `SE_MAX_POSTINGS=600`, `SE_PREFIX_TERMS=8`, `SE_HALF_LIFE_MS=36h`, `SE_PROFILE_MAX=4000`, `SE_FIELD_W={title:3, assets:2.5, topic:1.5, summary:1, source:0.4}` |
| `web/channel.js` | کلاینت تب ایده‌ها: `itemCard`, `render`, `load`, `mount`, `refresh`, `onCycleUpdate`, `pushNow`, `sendSingle`, `openDispatchModal`, `testBalePing`, `openSource`, `getItem`. نگاشت `TAGS` برای برچسب لِین‌ها |
| `web/manifest.webmanifest` | PWA: standalone، fa/rtl، `id="/?terminal=mohmd"`، ۳ آیکون (۱۹۲، ۵۱۲، maskable-512) |
| `web/icons/*.png` | `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` — از `tools/make_icons.py` تولید می‌شوند (نه باینری دستی)؛ تست `test_pwa_layer.py` ابعاد پیکسلی واقعی را با manifest تطبیق می‌دهد |
| `static/sw.js` | **تومب‌استون** — worker بازنشسته که کش `freebuff-v4` را پاک و خودش را unregister می‌کند (fetch handler ندارد). دست نزن، حذف هم نکن |
| `web/fonts/` + `assets/fonts/` | `web/fonts`: نسخهٔ woff2 که مرورگر و SW استفاده می‌کنند (`Vazirmatn-var`, IBM Plex Mono/Sans). `assets/fonts`: نسخهٔ TTF که فقط `card_render.py` برای PNG لازم دارد |

### ۵.۴ — جمع‌آوری داده

| فایل | پارتیشن و توابع مهم |
|---|---|
| `sources.py` | `MAX_AGE_HOURS=72`, `MAX_ARTICLES_PER_FEED=22`, `MIN_CREDIBILITY=.30`, `REPORT_MIN_CREDIBILITY=.55`؛ `TOPICS`/`TOPIC_ORDER`/`_TOPIC_KEYWORDS`؛ `_ASSET_PATTERNS`، `ASSETS`، **`SOURCES`**؛ `_GNEWS_TMPL`/`_GNEWS_QUERIES`/`_GNEWS_WIRES`؛ `_REDDIT_SUBS`؛ `PUBLISHER_TRUST`؛ `KIND_LABELS`، `QUALITY_PENALTIES`، regexهای SPONSORED/CLICKBAIT/RISKY/SEO؛ `publisher_trust`, `make_id`, `classify_topic`, الگوهای RELEVANCE/NOISE, `is_relevant`, `split_keywords`, `build_custom_patterns`, `detect_assets`, **`validate_article`** |
| `scraper.py` | فایل override فید؛ `HEADERS`؛ `_clean_html`، `_parse_date`، `_entry_publisher`؛ کش OG (`_og_image_fallback` ۱۷۲، `_entry_image` ۱۹۶)؛ **circuit breaker** (`_FAILS`, `_CIRCUIT_N=4`, `_CIRCUIT_BASE=900`, `_CIRCUIT_MAX=21600` — ۲۳۲–۲۳۶)؛ **`_fetch_one`**؛ mirror/variants (`_mirror_url` ۳۳۵، `_feed_url_variants` ۳۸۴، `_proxy_feed_urls` ۴۰۳، `_wayback_feed_urls` ۴۱۳، `_mirror_feed_urls` ۴۲۷)؛ **`deep_recover`**؛ `_classify_failure`، `_fetch_attempt`، **`scrape_all`** |
| `market_data.py` | `CACHE_FILE='.market_cache.json'`، `YAHOO_SYMBOLS`، `COINGECKO_IDS`، `_load_cache`/`_save_cache`، `yahoo_candidates`، `_yahoo_chart`، `_coingecko_simple`، **`fetch_market_data`** |
| `indicators.py` | `stochastic`، `resolve_yahoo_symbol`، `yahoo_candidates`، **`yahoo_candles`**؛ پایه‌ها: `sma`، `ema_series`، `ema`، `rsi_wilder`، `macd`، `atr14`، `bollinger`، `pct`، `trend_term`، `pivot_levels`؛ سری‌ها: `ema_aligned`، `rsi_series`، `macd_series`، `bollinger_series`؛ **`chart_payload`**، **`snapshot`** |
| `calendar_data.py` | `CACHE`/`TTL=900`؛ `SESSIONS`، `market_sessions`؛ جداول ترجمه: `IMPACT_FA`, `COUNTRY_FLAG`, `FNG_FA`, `IMPACT_NOTE`, `PERIOD_NOTE`, `COUNTRY_NAME`, `GEO_NAME/FLAG`, `CURRENCY_NAME`؛ `EVENT_DOCS`، `SPEAKER_HINT`، `CATEGORY_RULES`، `CADENCE_RULES`، `WHY_MATTERS`، `HOW_TRADED`؛ `event_doc`، `event_doc_fa`، `MACRO_QUOTES`، `_fetch`، `TV_*`، `_entry`، `TV_COUNTRIES` |
| `news_bypass.py` | `USER_AGENTS`، `REFERERS`، `BYPASS_COOKIES`، `ENHANCED_HEADERS`، **`ENHANCED_SITE_CONFIGS`**، `PAYWALL_INDICATORS`، **`class EnhancedNewsBypassReader`**، کش نتیجه (`_RES_CACHE`, `_RES_TTL_OK=6h`, `_RES_TTL_FAIL=10min` — ۷۷۲–۷۷۴)، `_reader`، **`smart_extract`** |
| `social_signals.py` | UA/تنظیمات؛ کانال‌های پیش‌فرض تلگرام/ساب‌ردیت‌ها/کوئری‌های یوتیوب؛ پارسرها: `ascii_digits`، `parse_age_hours`، `parse_count`، `parse_yt_initial`، `parse_telegram_channel`، `parse_reddit_feed`؛ تاریخچه (`push_hist` ۳۵۱, `hist` ۳۶۵, `hist_change` ۳۷۱)؛ کش/زمان‌بندی (`_load_cache`, `_save_cache`, `_is_stale`, `_schedule`, `cached` ۴۲۸)؛ **`refresh_all`**، `_worker`، `_run`، `_get`، `set_config`، `_yt_api_search` |
| `reddit_scores.py` | `API_URL='arctic-shift…'`, `_BATCH=25`, `_PAUSE=0.4`؛ `_load_cache`, `_save_cache`, `_extract_id`, **`fetch_scores`**، **`attach_scores`** |

### ۵.۵ — متن، ترجمه و فارسی‌سازی

| فایل | پارتیشن |
|---|---|
| `translate.py` | `ENDPOINT`, `MAX_CHARS=4000`, `BATCH=16`, `WORKERS=4`؛ `_cache_key`, `_ensure_loaded`, `_flush`, `cache_stats`؛ `_translate_batch`؛ **دروازهٔ فارسی:** `_FA_CHAR_RE`, `_looks_persian`، `_LATIN_RUN_MAX=4`, `_PERSIAN_MIN_SHARE=.45`, `persian_share`، `longest_latin_run`، **`is_persian`**؛ `to_persian`، `translate_many`، `translate_one`، `translate_paragraphs`، `save_cache` |
| `fa_format.py` | `IRAN_TZ=+03:30`، `_FA_DIGITS`، `_JALALI_MONTHS`، `_WEEKDAYS`؛ `fa_digits`، `gregorian_to_jalali`، `to_tehran`، `fa_date`، `fa_time`، `fa_datetime`، `fa_ago`، `fa_datetime_str`، `fa_fold` |
| `sentiment.py` | واژه‌نامه‌های صعودی/نزولی EN+FA، `_EMOJI_SENTIMENT`؛ `_text_hash`, `_clean_text`, `_vader_score`, `_lexicon_score`, `_emoji_score`, `_detect_language`؛ **`analyze_sentiment`**، `analyze_batch`، `get_aggregate_sentiment` |
| `persian_words.py` | لودر واژه‌نامهٔ وندور (`vendor/persian-crypto-words/*`، MIT)؛ `_MEME_EN`/`_MEME_SYM`، `JARGON`، `load`، **`crypto_evidence`** |

### ۵.۶ — گزارش و محتوا

| فایل | پارتیشن |
|---|---|
| **`report_generator.py`** | ثابت‌ها: `ASSET_NAMES`، `DEFAULT_IS_CRYPTO`، `SECTION_TITLES`، `TOPIC_KEYS`؛ فرمترها `_fmt/_pct/_fmt_price/_mini_ohlc_from_closes/_stamp`؛ ارجاع: `_cite_key`، `count_cited_news`، **`_cite`**، `_rank`، `_eligible`، `select_news`، `top_news`، `_news_sources_used`؛ **بخش‌ها:** `sec_market_overview`، `sec_macro`، `sec_news_impact`، `_derivatives_context`، `_flow_context`، `sec_flows`، `sec_derivatives`، **`_local_stance`**، `sec_technical`، `sec_scenarios`، `sec_conclusion`؛ **`build_report`**، **`build_all_reports`** |
| **`channel_profile.py`** | نرمال‌سازی (`NUMBER_RE`, `_PERSIAN_MAP`, `normalize` ۱۹۱، `article_text` ۲۰۲)؛ `_FA_SUFFIXES`/`_hit`؛ **`detect_buckets`**، `detect_off_profile`، `numbers_in`، `_IMPACT_WORDS`/`_market_impact`، `_freshness`، `_age_hours`، **`score_article`**، `_VIRAL_WORDS`، **`viral_score`**، `_tidy_fa`، `build_caption`، `_dedupe_key`، **`rank_for_channel`**، `slice_board` |
| **`news_editorial.py`** | `FINANCIAL_EDITORIAL_SYSTEM_PROMPT`؛ **`detect_market_emoji`**؛ `clean_editorial_title`؛ `_CONTRAST_MARKERS`؛ `split_sentences`، `editorial_blocks`؛ `IDEAS_SUMMARY_CHARS=1000`، `_IDEAS_CUT_MARKS`، **`ideas_summary`**؛ `format_editorial_summary`، `format_editorial_post` |
| `content_studio.py` | مراجع و وزن‌ها: `REF_*`, `COVERAGE_CAP`, `DEFAULT_WEIGHTS`, `ASSET_WORDS`, `DRAMATIC`, `STOPWORDS`, `FOOTER_FA/EN`؛ `tokens`، `_sentences`، `percentiles`؛ **سیگنال‌ها:** `match_signals`، `claim_signals`، `aggregate_signals`، `coverage_counts`، `format_scores`؛ **`rank`**؛ `DRAFT_SYSTEM`، `parse_draft`، **`template_draft`**، `draft`، `status` |
| `news_intelligence.py` | `_tokenize`، `_cosine_similarity`، `_compute_tf`؛ **`class Deduplicator`**، **`class CorrelationTracker`**، **`class AnomalyDetector`**؛ API ماژول: `dedup_articles`، `record_news_events`، `update_correlation_prices`، `get_intelligence_summary` |
| `card_render.py` | رنگ‌های برند؛ `class CardUnavailable`، `_require_stack`، `_shape`، `_font`، `_wrap`، `_fa_num`، **`render_news_card`** — اگر Pillow/فونت نباشد `CardUnavailable` → روت ۵۰۳ می‌دهد، هرگز تصویر شکسته |
| `tv_ideas.py` | کش `_TTL=1800`, `_FOLLOWERS_TTL=86400`؛ `SORTS=('popular','recent','followers')`, `KINDS=('all','picked','video','education')`؛ `tag_for`، `_extract_items`، `_clean_text`، `fetch_followers(_many)` (۱۲۲/۱۴۹)، `_parse_idea`، `popularity`، `sort_items`، `filter_items`، `fetch_ideas`، `find_idea`، `fetch_asset` |
| `tv_ta.py` | نرخ‌محدودسازی (`_MIN_GAP=1.5`, `_TTL_OK=900`, `_TTL_FAIL=300`)؛ `FA_REC`، **`technical_vote`**، `_fetch` |
| `ai_features.py` | `_SUMMARY_TTL=3600`؛ `_init_openai`، `_call_openai`، `summarize_asset_news`؛ **`class VolumeAnomalyDetector`**، **`class SentimentPredictor`**؛ `get_ai_summary`، `detect_anomalies`، `predict_sentiment`، `get_all_predictions` |
| `api_docs.py` | `OPENAPI_SPEC` + `get_swagger_html` |

### ۵.۷ — ماندگاری، سیستم و یکپارچه‌سازی

| فایل | پارتیشن |
|---|---|
| **`database.py`** | `DB_FILE='.mohmd_news.db'`، `_migrate_legacy_db` (از `.hermes.db`)؛ `db_conn`/`get_connection` (۳۴/۵۶)؛ **`init_db` — کل اسکیمای SQLite**؛ اخبار: `hide_article`، `unhide_all`، `hidden_ids`، `save_body`، `load_bodies`، `load_bodies_fa`، `save_articles`، `_row_to_article`، `load_articles_for_state`؛ استودیو: `save_studio_content`، `update_studio_content`، `studio_content_list`، `mark_studio_posted`، `studio_recent_keys`، `studio_posted_stats`؛ **ارباب پیام‌رسان:** `is_messenger_posted`، `mark_messenger_posted`، `messenger_recent_posted_ids`، `get_messenger_posted_logs` |
| `billing.py` | دیتابیس جدا `freebuff_tiers.db`؛ `_get_conn`, `init_tier_db`، **`TIERS`**، `_is_expired`، `get_user_tier`، `check_feature`، `track_usage`، `register_user` |
| `middleware.py` | سهمیهٔ روزانه: `_utc_day_start`، `_ANON_USAGE`، `_anon_count_and_track`، `_get_daily_usage`، **`require_tier(feature)`** — دکوراتور |
| `link_shortener.py` | `CACHE_FILE='.link_shortener_cache.json'`، `_TIMEOUT=6`، `_PROVIDER_BLOCKED`/`_PROVIDER_COOLDOWN=600`؛ providerها: `_tinyurl`، `_isgd`، `_opizo`، `_custom`، `_PROVIDERS`؛ `_chain`، **`shorten`** |
| `logging_config.py` | `JSONFormatter`، `SafeStreamHandler`، `setup_logging` (۴۰، RotatingFileHandler)، `get_logger` |
| `integrations/tv_webhook.py` | `ALERTS_PATH=data/tv_alerts.json`, `MAX_ALERTS=500`, قفل نوشتن؛ `_load_alerts`, `_save_alerts` (نوشتن atomic با `os.replace`)، **`_strip_secret`** (سکرت هرگز ذخیره/سرو نمی‌شود)، `process_webhook`، `get_recent_alerts`، `get_alerts_for_ticker` |
| `integrations/discord_bot.py` | `class DiscordBot`: `_send_webhook`, `_send_message`, `_send`، `send_digest`, `send_alert`, `send_anomaly_alert` (روی `z_score`/`severity` از `ai_features`) |

---

## ۶) قراردادهای HTTP API

### دسته‌بندی روت‌ها (به ترتیب `app.py`)

**صفحه و PWA**
```
GET  /    صفحهٔ SPA (APP_HTML)
GET  /sw.js    Service Worker (هدر Service-Worker-Allowed: /)
GET  /storage-engine.js
GET  /channel.js
GET  /manifest.webmanifest
GET  /fonts/<name>
GET  /icons/<name>    محافظت path-traversal
GET  /manifest.json    متادیتای دارایی‌ها برای کلاینت
```

**استریم زنده**
```
GET  /api/stream/info    وضعیت SSE
GET  /api/stream    SSE خبر/تقویم
GET  /api/stream/prices    SSE قیمت (هر MOHMD_PUSH_SECONDS)
```

**داده اصلی**
```
GET  /api/data    بستهٔ اصلی: articles, macro, fng, meta, ui…
POST /api/article/hide
POST /api/article/restore
GET  /api/stats
GET  /api/chart-data/<symbol>
GET  /api/sentiment
GET  /api/intelligence
GET  /api/etf
GET  /api/fng/<sym>
GET  /api/live
GET  /api/candles/<symbol>
GET  /api/econ    تقویم اقتصادی
GET  /api/report/<sym>
GET  /api/article/<art_id>    متن کامل (روی نردبان استخراج)
GET  /api/proxy-image    پروکسی تصویر (کش طولانی، از SW کنار گذاشته شده)
POST /api/refresh
GET  /api/monitor
POST /api/recover
GET  /api/recover/status
GET  /api/health
     api_metrics                7077   ⚠️ تابع تعریف شده ولی **هرگز register نشده** — نه
                                       @app.route دارد نه add_url_rule، پس /api/metrics وجود ندارد
GET  /api/ideas    تختهٔ ایده‌ها (نمایشی)
POST /api/ideas/translate
```

**API عمومی نسخهٔ ۱ (نیازمند کلید) — پارتیشن `app.py::══ V1 PUBLIC API (requires API key) ══`**
```
GET  /api/v1/articles
GET  /api/v1/indicators/<sym>
GET  /api/v1/sentiment
GET  /api/v1/calendar
GET  /api/v1/reports/<sym>
GET  /api/v1/health
GET  /api/v1/assets
GET  /api/docs    Swagger UI از OPENAPI_SPEC
GET  /api/admin/keys    مدیریت کلیدها (نیازمند MOHMD_TOKEN)
```

**وب‌هوک و هشدار**
```
POST /webhook/tv    TradingView (secret از settings)
GET  /api/alerts
GET  /api/ai/summary/<sym>
GET  /api/ai/predictions
GET  /api/ai/anomalies
```

**استودیو محتوا**
```
GET  /api/studio/feed
GET  /api/studio/item/<aid>
POST /api/studio/draft
GET  /api/studio/drafts
POST /api/studio/card    PNG فارسی (۵۰۳ اگر Pillow/فونت نباشد)
POST /api/studio/publish/telegram
POST /api/studio/publish/bale
GET/POST /api/studio/config
POST /api/studio/autopost/now
```

**تختهٔ ایده‌ها و ارسال**
```
GET  /api/channel/feed    تخته با فیلدهای نمایشی
GET  /api/ideas/dispatch-status
POST /api/ideas/send-single
POST /api/ideas/push-now    تک‌پروازِ (single-flight)
POST /api/ideas/push-debug
```

**پیام‌رسان‌ها**
```
POST /api/telegram/get-chat-id    |  POST /api/bale/get-chat-id  5173
POST /api/telegram/test    |  POST /api/bale/test         5235
POST /api/telegram/preview    |  POST /api/bale/preview      5250
POST /api/telegram/send-now    |  POST /api/bale/send-now     5277
POST /api/telegram/send    |  POST /api/bale/send         5323
```

**Billing و تنظیمات**
```
GET  /api/billing/tier
POST /api/billing/upgrade
GET  /api/billing/usage
POST /api/settings    ← ذخیرهٔ کل تنظیمات (تست‌شده در tests)
GET  /api/stream/info
```

### قالب پاسخ — قراردادها

- **`GET /api/data`**: `{ articles: [...], archive: [...], macro: [...], fng: {...}, ui: {...}, meta: {...}, updated: ts }`
  هر مقاله: `{ id, title, title_fa, summary, summary_fa, link, source_name, publisher, credibility,
  published_ts, age_hours, topic, topic_fa, assets[], kind, image, score_factors }`.
- **`GET /api/channel/feed`**: `{ ok: true, items: [ { id, title, title_fa, summary_fa, link, source,
  viral, primary_bucket, bucket_label, age_hours, posted_bale } ] }` — فقط فیلدهای نمایشی؛
  جزئیات امتیازدهی سمت سرور می‌ماند.
- **`GET /api/report/<sym>`**: `{ error?, symbol, fa_name, generated_at, sections: [ [kind, payload], ... ] }`
  که `kind` ∈ `h` (سرتیتر)، `p` (پاراگراف)، `cites` (کادر منابع)، `chart`، `tv`؛ هر `payload`
  کلیدهای `en` و `fa` دارد.
- **`POST /api/settings`**: بدنهٔ جزئی مجاز است (merge). تست `tests/test_messenger_gateway.py`
  با `{ "bale": {"send_ideas": false, "send_digest": true} }` این را می‌سنجد.
- **`POST /api/ideas/push-now`**: `{ ok: true, started: true }` یا `{ ok: true, already_running: true }`.
- **`POST /api/ideas/push-debug`**: `{ ok: true, send_digest: bool, send_ideas: bool, ... }`.

---

## ۷) اسکیمای SQLite

فایل: `.mohmd_news.db` (داخل `.gitignore`). ساخت با `database.init_db()` (`database.py::init_db`).
همهٔ جداول `CREATE TABLE IF NOT EXISTS` هستند، پس `tests/conftest.py` یک‌بار در هر سشن می‌سازد.

| جدول | نقش | ایندکس‌ها |
|---|---|---|
| `articles` | آرشیو اخبار | `idx_art_pub_ts (published_ts DESC)`, `idx_art_created (created_at DESC)` |
| `bodies` | 97 | بدنهٔ استخراج‌شده + ترجمهٔ پاراگراف‌ها (کلید `"<id>"` یا `"<id>\|fa"`) | `idx_body_at (at DESC)` |
| `hidden_articles` | 108 | خبرهای پنهان‌شده توسط کاربر | — |
| `news_events` | 114 | رویداد خبری برای همبستگی خبر↔قیمت | `idx_news_events_sym (symbol)` |
| `studio_content` | 131 | پیش‌نویس‌های استودیو | `idx_studio_content_ts (created_ts DESC)`, `idx_studio_content_key (title_key)` |
| `studio_posted` | 148 | لاگ ارسال استودیو | `idx_studio_posted_ts (posted_ts DESC)` |
| `messenger_posted` | 159 | dedupe ارسال هر پلتفرم جدا (`telegram` / `bale`) | `idx_messenger_posted_ts (posted_ts DESC)` |

دیتابیس دوم و مستقل: `freebuff_tiers.db` (فقط `billing.py`) — کاربر/سهمیه/tier.
دیتابیس سوم: `data/freebuff.db` (خالی/قدیمی، استفاده نمی‌شود).

---

## ۸) اسکیمای `settings.json`

فایل در ریشه، **gitignored** (چون می‌تواند توکن داشته باشد). اسکیمای پیش‌فرض در `DEFAULT_CONFIG` است؛ `load_config`/`save_config` در `app.py::load_config`/`613` آن را می‌خوانند/می‌نویسند.

```jsonc
{
  "interval": 1800,                 // دورهٔ چرخه، ثانیه
  "assets": ["BTC","ETH","SOL","XRP","XAU","ADA","BNB","DOGE","XAG","WTI","DXY","SPX","VIX"],
  "custom_assets": {},              // دارایی‌های کاربر: { SYM: {name, fa, yahoo, pattern, ...} }
  "auto_reports": true,

  "sources_enabled": { "<key منبع>": true },   // ۱۹۴ کلید، هم‌نام با sources.SOURCES
  "custom_sources": {},                        // منابع کاربر

  "report_max_age_hours": 24.0,
  "news_min_chars": 120,
  "news_hide_social": false,
  "social_score_filter": false,
  "social_score_min": 2000,
  "social_comments_min": 0,

  "telegram": {                     // ۲۱ کلید
    "enabled": bool, "token": "", "chat": "",
    "min_credibility": float, "max_items": int, "max_age_hours": float,
    "language": "fa", "include_link": bool, "link_on_own_line": bool,
    "include_summary": bool, "hashtags": bool, "emoji": bool, "show_stars": bool,
    "silent": bool, "pin": bool, "quiet_hours": bool,
    "template": "<b>{title}</b>\n\n{summary_blocks}{key_point}{link_line}",
    "send_ideas": true,            // ← سوئیچ «ایده‌ها» (پیش‌فرض روشن)
    "send_digest": false,          // ← سوئیچ «دیجست بسته» (پیش‌فرض خاموش)
    "gateway": "",                 // درگاه Cloudflare Worker بدون فیلترشکن
    "proxy": ""                    // "socks5://…" یا "http://…"
  },

  "bale": {                         // ۱۹ کلید — همان ساختار منهای pin/gateway/proxy، به‌جایش:
    "asset_filter": []              // فیلتر دارایی برای کانال بله
  },

  "link_shortener": { "provider": "auto", "api_key": "", "custom_endpoint": "" },
  "discord": { "enabled": false, "token": "", "channel_id": null, "webhook_url": "" },
  "tv_webhook_secret": "change-me-to-a-random-string",   // ← در بوت هشدار می‌دهد

  "content_studio": {               // ۱۷ کلید
    "enabled": true, "credibility_gate": 0.55, "half_life_hours": 12.0,
    "repeat_penalty": 0.35, "repeat_penalty_hours": 48,
    "min_score": 0.0,
    "weights": { ... }, "asset_weights": { ... },
    "youtube_queries_fa": [], "youtube_queries_en": [],
    "youtube_channels": [], "telegram_channels": [], "reddit_subs": [],
    "youtube_key": "", "instagram_token": "", "instagram_user_id": "",
    "auto_post": { ... }
  },

  "ai": { "enabled": false, "openai_key": "", "openai_model": "gpt-4o-mini",
          "summary_assets": [], "summary_interval": 3600 }
}
```

**تلهٔ مهم:** `settings.json` روی دیسک زنده است. هر تستی که `/api/settings` را صدا می‌زند
**باید** `app.CONFIG_FILE` را به یک فایل موقت تغییر دهد (الگوی موجود در
`tests/test_messenger_gateway.py::test_settings_save_persists_ideas_and_digest_switches`).

---

## ۹) لایهٔ آفلاین: Service Worker + IndexedDB

### Service Worker (`web/sw.js`)

| کلاس درخواست | استراتژی | دلیل |
|---|---|---|
| `navigate` | network-first با `NAV_TIMEOUT=4000` → پوستهٔ کش‌شده | پوستهٔ کهنه بی‌ضرر است؛ JSON خبر را می‌آورد |
| `/api/*` GET (جز `proxy-image`) | network-first **بدون تایم‌اوت** | سرو کش در شبکهٔ کند = «فید روی خبر قدیمی قفل شد» |
| `/api/stream`, `/api/stream/prices` | دست‌نخورده | SSE؛ بافر کردن یعنی فریز شدن تیکر |
| `/api/proxy-image` | دست‌نخورده | هدرهای کش خودش + payload بزرگ‌تر از سایز این کش |
| دارایی‌های پوسته | stale-while-revalidate | بوت فوری |
| cross-origin | stale-while-revalidate (`EXT_CACHE`) | فونت، کتابخانهٔ چارت |

پیام‌های `postMessage` که کلاینت می‌فرستد: `SKIP_WAITING`, `CLEAR_API_CACHE`, `ENSURE_SHELL`,
`CACHE_URLS`, `PING`. پاسخ‌ها: `SW_OFFLINE_TICK`, `SW_CACHE_CLEARED`, `SW_SHELL_OK`,
`SW_SHELL_PRIMED`, `PONG`.

بامپ نسخه: با هر تغییر پوسته، `SW_VERSION` را بالا ببر (اکنون `'v16'`).

### IndexedDB (`MohmdNewsDB`, v1) — `SE_STORES` در `web/storage_engine.js`

| استور | کلید | ایندکس‌ها | نگهداشت |
|---|---|---|---|
| `articles` | `id` | `ts`, `topic`, `assets (multiEntry)` | ۴٬۰۰۰ ردیف تازه‌تر |
| `reports` | `sym` | `ts` | یک ردیف به‌ازای نماد |
| `calendar` | `id` | `ts`, `impact` | پنجرهٔ چند-هفته‌ای |
| `bookmarks` | `id` | `saved_at` | تا لغو ستاره |
| `terms` | `term` | `df` | ۶۰۰ postings تازه‌تر به‌ازای ترم |
| `meta` | `k` | — | شمارنده‌ها |

فرمول امتیاز جستجو (`seSearch`):
`idf = ln(1 + total/(1+df))` · `score = Σ idf·(1+ln(1+w))·(exact?1.6:1)`
سپس `× (0.45 + 0.55·coverage) × (0.35 + 0.65·recency)` با `recency = 0.5^(age/36h)`.
حالت پیش‌فرض AND است و اگر کمتر از ۳ نتیجه بدهد یک بار به OR شل می‌شود (`relaxed: true`).

**قاعدهٔ حیاتی IndexedDB:** داخل یک تراکنش باز **هرگز `await` روی پرامیس غیر-IDB نگذار**
(تراکنش در همان await خودکار commit می‌شود و درخواست بعدی `TransactionInactiveError` می‌دهد).
الگوی درست: درخواست‌ها را صف کن، بعد یک‌بار `tx.oncomplete` را await کن.

---

## ۱۰) سبک کدنویسی و کنوانسیون‌های مخزن

### پایتون

- **زبان کامنت‌ها و docstringها انگلیسی، متن محصول فارسی.** کامنت‌ها معمولاً «چرا» را می‌گویند
  نه «چه»؛ خیلی جاها دلیل یک تصمیم در کامنت نوشته شده (این پروژه عمداً ممیزی‌پذیر است).
- **تابع‌های خصوصی با `_`** (`_tg_send`, `_looks_crypto`, `_fast_json`).
- **نوع‌دهی سبک و تدریجی**: `list[dict]`, `dict | None`, `Optional[...]` — همه‌جا اجباری نیست.
- **هیچ import دامنه‌ای داخل ماژول با cyc**: ماژول دامنه `app` را import نمی‌کند.
- **تنزل مؤدبانه**: هر import اختیاری داخل `try/except` و هر قابلیت گران با fallback
  (`orjson`→`json`، `waitress`→`app.run`، `Pillow`→`CardUnavailable`، `trafilatura`→`None`).
- **هیچ خطای بلعیده‌شدهٔ بی‌صدا** در مسیرهای مهم: یا `log(...)` می‌شود یا به کاربر دامپ می‌شود.
- تورفتگی ۴ فاصله، خطوط کوتاه، بدون formatter اجباری (black/ruff در مخزن تنظیم نشده).
- **نقاط قفل**: `STATE_LOCK`, `_CONTENT_LOCK`, `_FA_CONTENT_LOCK`, `_ALERTS_LOCK`,
  `_FAQ_LOCK`. هر نوشتن روی `STATE` با `with STATE_LOCK`.
- **کش‌ها همیشه دیسک‌دار**: هر کش یک فایل نقطه‌دار در ریشه + TTL داخلی.

### جاوااسکریپت (داخل `dashboard_html.py` و `web/`)

- **ES2019+، بدون build، بدون فریمورک.** فقط DOM خام + `fetch`.
- **هر رشتهٔ ورودی از `esc()`/`attr()`/`Sanitizer` عبور می‌کند.** این خط قرمز است.
- **تنها یک تایمر**: `Clock` (`clockFactory` در ۳۵۸۹). هر نیاز زمان‌بندی به `Clock.every(...)`
  می‌رود — تایمرهای پراکنده در این پروژه حذف شده‌اند (`_calHeroTick`, `_sessTick` نمونه‌اند).
- **اسکرول مجازی**: هر فهرست بلند باید از `VirtualScroller` استفاده کند (تاکنون feed/archive/bookmark).
- **قاعدهٔ نما**: خروج از یک نما باید منابعش را آزاد کند (`app.py` کنار `8148`).
- **`toFa()` برای هر عدد نمایشی**؛ اعداد لاتین در UI فارسی نمی‌مانند.
- **State سراسری محدود و نام‌دار**: `DATA`, `UI`, `TVW`, `LIVE`, `VS`, `AR`, `ECON`, `CAL`, `LEAD`, `SM_*`.

### کامنت‌ها و بنرها

بلوک‌های سند با بنرهای جعبه‌ای جدا می‌شوند:
`/* ── N · TITLE ───── */` در CSS، `/* ══ TITLE ══ */` در JS، `# ── title ──` در پایتون.
اگر بخش جدیدی اضافه می‌کنی، این الگو را ادامه بده (ابزارها و تست‌ها روی همین ساختار حساب می‌کنند).

---

## ۱۱) تست‌ها و CI

اجرا: `.venv/Scripts/python -m pytest tests/ -q` — **234 تست**، همه شبکه‌آزاد
(هر تماس بیرونی monkeypatch می‌شود). `tests/conftest.py` یک fixture سشن دارد که `database.init_db()`
را صدا می‌زند (چون DB در گیت نیست).

**خط پایهٔ فعلی (اندازه‌گیری‌شده): این مجموعه سبز نیست.** ۱۱ تست در حوزهٔ پیام‌رسان/
ایده‌های محتوا قرمز است — فهرست کامل و شرطِ «سبز» در `AGENTS.md` §۵.

| فایل | پوشش |
|---|---|
| `test_messenger_gateway.py` | قرارداد بنگاه تلگرام (`_tg_base`)، قالب پیام ایده‌ها (تیتر → دو بند → لینک)، لینک‌کوتاه‌کن، circuit breaker، لِین‌بندی و نامحدود بودن اخبار جهان، خاموشی دیجست، **دروازهٔ «فقط فارسی بده»**، ماندگاری سوئیچ‌ها در `/api/settings` |
| `test_dashboard_logic.py` | قراردادهای JS صفحه: وجود `esc`/`Sanitizer`/`toFa`/`VirtualScroller`، نبود الگوهای ناامن، ساختار نماها |
| `test_core.py` | هستهٔ سرور: روت‌ها، دروازهٔ `MOHMD_TOKEN`، API v1، کلیدها، webhook، استخراج |
| `test_content_studio.py` | رتبه‌بندی و سیگنال‌ها، `template_draft`، روت‌های استودیو |
| `test_bug_fixes.py` | رگرسیون باگ‌های واقعی گذشته (هر تست یک باگ مشخص) |
| `test_channel_profile.py` | لِین‌ها، آف‌پروفایل، `score_article`, `viral_score`, `rank_for_channel` |
| `test_pwa_layer.py` | موتور IndexedDB زیر Node (۳۰+ assertion)، قرارداد SW، تطابق manifest↔آیکون‌های روی دیسک، روت‌های آفلاین، ترتیب سیم‌کشی صفحه |
| `test_editorial_messengers.py` | ۱۷ استاندارد ادیتوریال: ایموجی بازار، تمیزکاری تیتر، حفظ اعداد، قالب HTML/Markdown، dedup دیتابیس |
| `test_stream_manager.py` | `StreamManager` سرور: سقف اتصال، بی‌هزینه بودن پوش در زمان بی‌کاری |
| `test_ideas_dispatch.py` | ارسال به هر دو پیام‌رسان، رد کامل آیتم انگلیسی، برش‌نشدن جمله در خلاصه |
| `test_features_extended.py` | حذف کامل whale tracker / workspace / squawk، سالم بودن نحو همهٔ بلوک‌های JS، نشتی‌نداشتن `MOHMD_TOKEN` در محیط تست |
| `test_handlers_defined.py` | هر تابعی که از `on*=` درون‌خطی صدا زده می‌شود تعریف‌شده باشد (گارد rename)، به‌همراه canary استخراج‌کننده و ۵ handler حیاتی |

**قاعدهٔ تست در این مخزن:** هر باگ واقعی که رفع می‌شود یک تست می‌گیرد
(الگوی غالب در `test_bug_fixes.py`: کامنت، سپس دلیل دقیق باگ قبلی، سپس assertion).

**CI:** `.github/workflows/ci.yml` روی push/PR به `main`:
1. نصب requirements + pytest
2. `python -m pytest tests/ -q` و چاپ نام تست‌های شکست‌خورده به‌صورت annotation
3. `python tools/check_dashboard_js.py` — **گیت نحوی JS؛ شکستن آن build را می‌اندازد**
4. `bandit` و `pip-audit` — **مشورتی** (`continue-on-error: true`)

**دو دستور دستی حیاتی قبل از هر تحویل:**
```bash
.venv/Scripts/python tools/check_dashboard_js.py     # نحو هر ۸ بلوک inline + web/*.js
.venv/Scripts/python -m pytest tests/ -q
.venv/Scripts/python smoke_test.py                   # اجرای واقعی خط لوله (نیازمند شبکه)
```

---

## ۱۲) ابزارها و اسکریپت‌های عملیاتی

| فایل | کار |
|---|---|
| `tools/check_dashboard_js.py` | هر `<script>` بدون `src` را از `APP_HTML` (متن مونتاژشده) بیرون می‌کشد و با `node --check` چک می‌کند، بعد هر فرگمنت `web/fragments/*.js` را جدا و در آخر `web/*.js`. `--list` برای فهرست |
| `tools/guard_diff.py` | دروازهٔ اندازهٔ diff: هر فایل با بیش از `--max-del` خط حذف (پیش‌فرض ۸۰) یا بیرون از `--allow` → خروج غیرصفر |
| `tools/make_icons.py` | آیکون‌های PWA را از روی پالی‌لاین `#i-mark` می‌کشد (رسترایزر signed-distance + `zlib`؛ بدون Pillow). `--check` تطابق پیکسلی را می‌سنجد (drift ≤ ۰.۱٪) |
| `tools/make_maquette.py` | دموی تک‌فایلی: `/storage-engine.js` را inline می‌کند تا فایل بدون سرور باز شود |
| `tools/splice_theme.py` | فرگمنت استایل‌شیت (`web/fragments/10_style.css`) را با فایل CSS بیرونی جایگزین می‌کند (normalize به CRLF). `--check` = dry run |
| `tools/remap_tokens.py` | `var(--old)`های بیرون از استایل‌شیت را به توکن‌های جدید نگاشت می‌کند؛ به همهٔ فرگمنت‌ها جز `10_style.css` سر می‌زند |
| `tools/_cal_en.py` | دادهٔ کمک‌کنندهٔ متن انگلیسی تقویم |
| `tools/_inventory.py`, `_check_handlers.py`, `_en_scan.py`, `_strip_retrofits.py` | اسکریپت‌های یک‌بارمصرف ممیزی (`_*.py` در گیت‌ایگنور) |
| `tools/theme_v3_a..d.css` | نسخه‌های استایل‌شیت ردیزاین (ورودی `splice_theme.py`) |
| `start.bat` | venv + نصب + اجرا روی پورت ۵۰۵۵ |
| `push.bat` | push یک‌کلیکی (Git Credential Manager) |
| `smoke_test.py` | اجرای واقعی خط لوله بدون سرور: منبع → تازگی ۷۲h → ترجمه → بازار → نمودار → گزارش. چاپ `OK/FAIL` برای هر شرط |
| `GIT_WORKFLOW.md` | چرخهٔ الزامی git + اسکن سکرت (قبل از commit) |
| `docs/telegram-gateway.md` | ساخت درگاه Cloudflare Worker برای تلگرام بدون فیلترشکن |
| `docs/related-projects.md` | چه چیزی از پروژه‌های مرجع گرفته شد و چه چیزی عمداً گرفته **نشد** |

---

## ۱۳) اصطلاح‌نامهٔ فارسی ↔ انگلیسی

| فارسی در UI | مفهوم کد |
|---|---|
| جریان خبر | feed / `/api/data` articles |
| ایده‌های محتوا | `view-channel` (تختهٔ ارسال) |
| ایده‌های تریدینگ‌ویو | `view-ideas` / `tv_ideas.py` |
| نشان‌شده‌ها | bookmarks (`BM_KEY='mohmd_bmarks'`) |
| آرشیو هوشمند | `archive` |
| سلامت منابع | monitor (`view-monitor`) |
| مدیریت منابع / دارایی‌ها | sources / assets managers |
| تقویم اقتصادی | `calendar_data.py` / `/api/econ` |
| نرخ زندهٔ ETF | `_etf_quotes` / `/api/etf` |
| شکاف داده | data gap (نمایش `—`) |
| درگاه | gateway (`_tg_base`) |
| لِین | bucket/lane (`gold`, `coin`, `currency`, `global`, `crypto`, `tech`) |
| وایرال | `viral_score` (۰..۱۰۰) |
| اعتبار | credibility (۰..۱) |
| کادر منابع | citation block (`cites`) |
| رأی مستقل | TradingView vote (`tv_ta.technical_vote`) |
| پرچم ناسازگاری | disagreement flag (`report_generator._local_stance`) |
| فقط فارسی بده | `translate.is_persian` gate |
| ارسال فوری به بله | `_post_cycle_ideas` / `/api/ideas/push-now` |

---

## ۱۴) نقاط توسعه: برای تغییر هر چیز کجا برو

| می‌خواهی… | فایل و محل |
|---|---|
| منبع خبری اضافه/حذف کنی | `sources.py::SOURCES`؛ کلید را در `settings.sources_enabled` هم بگذار |
| دارایی جدید اضافه کنی | `sources.py::ASSETS` + `_ASSET_PATTERNS` + `market_data.YAHOO_SYMBOLS` + `indicators.yahoo_candidates` |
| الگوی استخراج متن را عوض کنی | `app.py::fetch_article_content` و پله‌های بالای آن |
| آستانهٔ اعتبار را عوض کنی | `sources.py`: `MIN_CREDIBILITY`، `REPORT_MIN_CREDIBILITY` |
| قالب پیام تلگرام/بله را عوض کنی | `app.py`: `TG_TEMPLATE_DEFAULT`، `BALE_TEMPLATE_DEFAULT`، `_tg_render_digest`، `_bale_render_digest` |
| منطق ارسال ایده‌ها را عوض کنی | `app.py::_post_cycle_ideas` + `channel_profile.rank_for_channel` |
| متن ادیتوریال/ایموجی را عوض کنی | `news_editorial.py` (کل فایل ۳۸۸ خط) |
| امتیاز وایرال را عوض کنی | `channel_profile.py::viral_score` و `score_article` |
| بخشی به گزارش نهادی اضافه کنی | `report_generator.py`: یک `sec_*` بنویس و در `build_report` وصل کن |
| شکل `api_data` را عوض کنی | `app.py::api_data` — **و** `_ser_article` که قرارداد فیلدها را می‌سازد |
| یک نما یا کارت UI عوض کنی | `dashboard_html.py`: بخش‌های `view-*`، `cardHTML`، `renderFeed` |
| استایل/تم را عوض کنی | `web/fragments/10_style.css` — بنر `══ 1 · TOKENS ══` و بلاک `html[data-theme="light"]`؛ یا `tools/theme_v3_*.css` + `tools/splice_theme.py` |
| رفتار آفلاین را عوض کنی | `web/sw.js` (استراتژی‌ها) و `web/storage_engine.js` (`SE_STORES`, `seSearch`) — **و `SW_VERSION` را بامپ کن** |
| جدول دیتابیس اضافه کنی | `database.py::init_db` + یک متد دسترسی؛ یادت باشد `CREATE TABLE IF NOT EXISTS` باشد |
| سوئیچ تنظیمات اضافه کنی | `app.py::DEFAULT_CONFIG` + `api_settings` + `renderSettings`/`saveSettings` در UI |
| روت جدید اضافه کنی | `app.py` در نزدیک‌ترین پارتیشن موجود؛ اگر عمومی است زیر پارتیشن `V1 PUBLIC API` با `@_check_api_key` |

---

## ۱۵) بدهی فنی، driftها و تله‌ها

**drift مستنداتی — اصلاح‌شده:** اعداد کهنهٔ `README.md` (۱۹۳ منبع/۱۶۹ تست)،
`PROJECT_OVERVIEW.md` (همان دو + ۱۴ نما) و پیام `start.bat` («71 sources») در این پاس با
مقادیر اندازه‌گیری‌شده جایگزین شدند (**۱۹۴** منبع، **۱۳** دارایی، **۱۳** نما). درسِ آن:
عدد را در سند تکرار نکن؛ دستور اندازه‌گیری را بنویس.

**ریسک‌های ساختاری:**

1. **UI در فرگمنت‌هاست، ولی محافظ‌ها همان‌ها هستند.** `py_compile` فرگمنت‌ها را
   نمی‌بیند؛ محافظ‌ها `tools/check_dashboard_js.py`، `tests/test_features_extended.py`
   (نحو) و `tests/test_handlers_defined.py` (تعریف‌شدن هر handler) هستند. هر تغییر UI
   بدون اجرای آن‌ها = ریسک صفحهٔ سفید یا دکمهٔ بی‌کار. `APP_HTML` هم‌زمان از مونتاژ
   می‌آید، پس ویرایش `dashboard_html.py` به‌جای فرگمنت، هیچ اثری روی صفحه ندارد.
2. **`app.py` ۷٬۲۶۶ خط با ۷۰ روت.** هر روت جدید فاصلهٔ «فهمیدن» را بیشتر می‌کند.
   (شمارش دقیق: `grep -cE "^@app\\.route" app.py` → ۷۰، به‌علاوهٔ دو هوک `before_request`/`after_request`.)
3. **اندپوینت ثبت‌نشده:** `api_metrics` کد مرده است — تعریف شده ولی register نشده
   (نه `@app.route` دارد نه `add_url_rule`)، پس `/api/metrics` هرگز در دسترس نبوده است.
4. **دو منبع حقیقت برای قرارداد مقاله:** `_ser_article` (سرور) و `cardHTML` (کلاینت) —
   تغییر یکی بدون دیگری فیلد بی‌صدا از دست می‌دهد.
5. **`settings.json` روی دیسک زنده.** تستی که `CONFIG_FILE` را redirect نکند، تنظیمات
   واقعی کاربر را می‌نویسد.
6. **آرتیفکت‌های اسکرچ — پاک‌سازی‌شده.** `content_studio_export.zip`،
   `dashboard_html.py.pre_sellix_*.bak`، `static/hero-colour-combinations.html` و `backups/`
   به `_archive/` (gitignored) منتقل شدند؛ `static/hero-colour-combinations.html`
   برخلاف ادعای این سند **tracked** بود و از مخزن خارج شد. `tools/theme_v3_*.css` سرِ جایش
   ماند چون ورودی `tools/splice_theme.py` است.
7. **کش‌های رانتایم بزرگ:** `.translate_cache.json` ~۹.۸MB، `.mohmd_news.db` ~۴۳MB،
   `correlation.json` ~۸۸۷KB، `.news_links.json` ~۴۷۰KB.
8. **`static/sw.js` یک تومب‌استون است** — حذفش نکن، منطقش عمدی است (خودش را unregister می‌کند).
9. **تلهٔ IndexedDB:** `await` داخل تراکنش باز = تراکنش خودکار commit‌شده و خطای بعدی.

**تله‌های سطح رفتار (که تست‌ها از آن‌ها محافظت می‌کنند):**

- دیجست بسته به‌طور پیش‌فرض **خاموش** است (`send_digest: false`)، ولی ارسال ایده‌ها روشن.
- سقف `max_items` روی ارسال ایده‌ها **اعمال نمی‌شود** (عمداً؛ همهٔ تولیدشده‌ها باید بروند).
- لینک در پیام ایده‌ها **همیشه** آخرین خط و روی خط خودش است، حتی اگر قالب سفارشی آن را جای دیگری بگذارد.
- آیتم نیمه‌انگلیسی حذف می‌شود، نه منتشر؛ اگر ترجمهٔ مجدد فارسی بدهد، دوباره منتشر می‌شود.
- circuit breaker بعد از **۲ خطای اتصال** باز می‌شود و کل پاس را متوقف می‌کند.

---

## ۱۶) قالب نوشتن درخواست تغییر

برای گرفتن بهترین نتیجه از یک ایجنت روی این مخزن، درخواست را این‌طور بنویس:

```
[هدف]      یک جمله: چه رفتاری باید عوض شود و کاربر نهایی چه چیزی می‌بیند.
[سطح]      لایه: بک‌اند (app.py / ماژول دامنه) | UI (dashboard_html.py) | آفلاین (web/) | هر دو
[قرارداد]  اگر شکل داده یا endpoint عوض می‌شود، دقیقاً بنویس چه فیلدی اضافه/حذف می‌شود.
[قیدها]    کدام قواعد غیرقابل‌مذاکره درگیرند (بدون داده ساختگی، فارسی‌بودن، تک‌پروسس).
[اثبات]    چه چیزی «انجام‌شده» را ثابت می‌کند: نام تست، رفتار در UI، خروجی endpoint.
[دام]      فایل‌هایی که نباید دست بخورند یا وابستگی‌هایی که نباید اضافه شوند.
```

نمونهٔ پرامت خوب برای این مخزن:

> در تب «ایده‌های محتوا» یک فیلتر جدید «فقط لِین طلا» اضافه کن. سطح: UI + یک پارامتر اختیاری
> در `/api/channel/feed`. قرارداد: پارامتر کوئری `bucket=gold` و آیتم‌های برگشتی همان شکل فعلی.
> قید: بدون داده ساختگی، همهٔ رشته‌ها از `esc()`، لِین‌های دیگر حذف نشوند. اثبات:
> تست جدید در `tests/test_messenger_gateway.py` برای فیلتر سمت سرور + اجرای
> `tools/check_dashboard_js.py`. دام: `_post_cycle_ideas` نباید تغییر کند.

---

### ضمیمه: پنج واقعیت که هر ایجنت باید قبل از اولین edit بداند

1. کد در یک مخزن **تک‌پروسس، بدون build** است؛ تغییر UI یعنی ویرایش یک استرینگ پایتون.
2. **`tools/check_dashboard_js.py` و `pytest tests/ -q` تنها دروازه‌های اعتبارسنجی هستند** — هر دو باید سبز بمانند.
3. **قرارداد پیام/داده در تست‌ها قفل شده است**؛ اگر تستی انتظار «لینک در آخرین خط» یا
   «سقف ۱۵۰ کاراکتر» دارد، آن رفتار عمدی است، نه جزئیات.
4. **ماژول‌های دامنه `app` را import نمی‌کنند** — منطق را در ماژول بگذار، `app.py` را نازک نگه دار.
5. **کش‌ها روی دیسک و در ریشه‌اند**؛ اگر رفتار کش را عوض می‌کنی، به TTL و ماندگاری فایل هم فکر کن.
