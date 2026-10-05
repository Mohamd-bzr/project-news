# 🐛 ریپورت باگ‌ها و پرامپت‌های رفع — FreeBuff

> **تاریخ:** ۲۸ سپتامبر ۲۰۲۶  
> **وضعیت:** فقط گزارش — هیچ فایلی تغییر نکرده  
> **تعداد:** ۷۴ باگ (Critical 5 / High 20 / Medium 34 / Low 15)

---

## فهرست

1. [🔴 Critical (5)](#-critical--۵-مورد)
2. [🟠 High (20)](#-high--۲۰-مورد)
3. [🟡 Medium (34)](#-medium--۳۴-مورد)
4. [🔵 Low (15)](#-low--۱۵-مورد)
5. [پرامپت‌های جامع برای رفع گروهی](#پرامپت‌های-جامع-برای-رفع-گروهی)

---

## 🔴 Critical — ۵ مورد

---

### C1. ترجمه دیکشنری مقالات مشترک رو بدون لاک تغییر میده
**فایل:** `app.py` | **خط:** ~391  
**توضیح:** `_translate_articles_inplace(live)` فیلدهای `title_fa`/`summary_fa` رو مستقیماً توی دیکشنری‌هایی می‌نویسه که از طریق `STATE['articles']` برای handlerهای Flask قابل دسترسیه. لاک فقط روی رفرنس لیست اعمال میشه، نه روی فیلدهای داخلی دیکشنری‌ها. خواننده‌ها می‌تونن مقاله‌ای با `title_fa` پر شده ولی `summary_fa` خالی ببینن (یا برعکس).

**تغییر مورد نیاز:**
- هر مقاله‌ای که وارد STATE میشه باید یه کپی مستقل (deep copy) باشه
- یا ترجمه باید روی یک لیست موقت انجام بشه و بعد atomic swap بشه

**پرامپت:**
```
در فایل app.py تابع run_cycle و _translate_articles_inplace رو بررسی کن.
مشکل اینه که article dicts بین STATE['articles'] و worker ترجمه share میشه.
راه‌حل:
1. بعد از scrape_all و قبل از ترجمه، هر article dict رو deep copy کن: 
   live = [json.loads(json.dumps(a)) for a in live]
2. ترجمه رو روی کپی انجام بده
3. کپی ترجمه‌شده رو جایگزین لیست اصلی کن
یا:
1. ترجمه رو کاملاً قبل از قرار دادن در STATE انجام بده
مطمئن شو article dictهایی که توی STATE['articles'] هستن هیچ‌وقت همزمان نوشته نمیشن.
```

---

### C2. کش‌های سراسری بدون لاک تغییر می‌کنن
**فایل:** `app.py` | **خط:** ~382-388  
**توضیح:** `CONTENT_CACHE`، `FA_CONTENT_CACHE` و `FA_REPORT_CACHE` دیکشنری‌های ساده‌ای هستن که همزمان از طرف `run_cycle` (پاکسازی) و handlerهای Flask (خواندن/نوشتن/حذف) تغییر می‌کنن. هیچ لاکی محافظتشون نیست. `dict.pop` همزمان با iteration = `RuntimeError`.

**تغییر مورد نیاز:**
- معرفی یک لاک اختصاصی برای هر کش یا استفاده از لاک مشترک
- تمام عملیات read/write/delete تحت لاک

**پرامپت:**
```
در فایل app.py:
1. سه تا لاک اختصاصی تعریف کن بالای فایل:
   _CONTENT_LOCK = threading.Lock()
   _FA_CONTENT_LOCK = threading.Lock()
   _FA_REPORT_LOCK = threading.Lock()
2. تمام دسترسی‌ها به CONTENT_CACHE (خواندن، نوشتن، pop، clear) رو تحت _CONTENT_LOCK قرار بده
3. تمام دسترسی‌ها به FA_CONTENT_CACHE رو تحت _FA_CONTENT_LOCK قرار بده
4. تمام دسترسی‌ها به FA_REPORT_CACHE رو تحت _FA_REPORT_LOCK قرار بده
مخصوصاً این خطوط: purge loop، cache lookup در handlerها، translate report cache
مطمئن شو در lock nesting اتفاق نمیفته (لاک‌ها nested نباشن).
```

---

### C3. pinChatMessage با GET اجرا میشه
**فایل:** `app.py` | **خط:** ~1787-1788  
**توضیح:** API تلگرام برای pin کردن پیام نیاز به `POST` داره ولی کد `requests.get()` استفاده میکنه.

**تغییر مورد نیاز:**
- `requests.get` → `requests.post`

**پرامپت:**
```
در فایل app.py تابع _tg_send_digest یا هر جایی که pinChatMessage صدا زده میشه:
requests.get( به requests.post( تغییر بده.
فقط همون خط رو عوض کن، بقیه کد دست نخوره.
```

---

### C4. fetch_article_content با url=None کرش میکنه
**فایل:** `app.py` | **خط:** ~2905, 2912, 2922  
**توضیح:** اگه `url` برابر `None` یا رشته خالی باشه، `urlparse(None)` → `AttributeError` و `'news.google.com' in None` → `TypeError`.

**تغییر مورد نیاز:**
- Guard اول تابع: `if not url: return {"paragraphs": [], "word_count": 0, "partial": True, "title": "", "url": url}`

**پرامپت:**
```
در فایل app.py تابع fetch_article_content:
اولین خط عملیاتی تابع رو با یک guard شروع کن:

if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
    return {"paragraphs": [], "word_count": 0, "partial": True, "title": "", "url": url or "", "method": "none"}

این guard باید قبل از هر urlparse یا string operation دیگه‌ای باشه.
```

---

### C5. تابع esc() کوتیشن تکی رو escape نمیکنه → XSS
**فایل:** `dashboard_html.py` | **خط:** ~2545, 2753, 3062-3064  
**توضیح:** `esc()` فقط `& < > "` رو escape میکنه. آیدی مقاله‌ها مستقیماً توی inline `onclick` با کوتیشن تکی قرار میگیرن. آیدی شامل `'` → JavaScript injection.

**تغییر مورد نیاز:**
- اضافه کردن escape کوتیشن تکی: `.replace(/'/g, "\\'")`
- یا بهتر: حذف inline onclick و استفاده از event delegation با `data-id`

**پرامپت:**
```
در فایل dashboard_html.py (بخش JavaScript):
1. تابع esc() رو پیدا کن و این خط رو اضافه کن بعد از بقیه replacements:
   s = s.replace(/'/g, "\\'");

2. بهتره همچنین inline onclick ها رو حذف کنی و از event delegation استفاده کنی:
   - روی container والد یه event listener بذار
   - از data-attributes استفاده کن: data-article-id="..."
   - در handler از event.target.closest('[data-article-id]') استفاده کن

اگه راه‌حل inline میخوای حداقل esc() رو fix کن.
```

---

## 🟠 High — ۲۰ مورد

---

### H1. CONFIG بدون لاک خونده میشه
**فایل:** `app.py` | **خط:** ~267-270, 449  
**توضیح:** `run_cycle` و `scheduler_loop` مقادیر CONFIG رو بدون لاک میخونن، در حالی که `api_settings` از thread دیگه‌ای اونو تغییر میده.

**پرامپت:**
```
در app.py یک لاک اضافه کن:
_CONFIG_LOCK = threading.Lock()

تمام خواندن‌های CONFIG در run_cycle و scheduler_loop رو تحت _CONFIG_LOCK قرار بده.
تمام نوشتن‌های CONFIG در api_settings (POST /api/settings) رو هم تحت _CONFIG_LOCK قرار بده.
مخصوصاً:
- CONFIG.get('sources_enabled')
- CONFIG.get('custom_sources')  
- CONFIG.get('custom_assets')
- CONFIG.get('report_max_age_hours')
- CONFIG.get('interval')
- CONFIG['auto_reports']
```

---

### H2. LIVE_CACHE busy-flag TOCTOU race
**فایل:** `app.py` | **خط:** ~800-814  
**توضیح:** دو درخواست همزمان هر دو `busy=False` میبینن و هر دو thread refresh شروع میکنن.

**پرامپت:**
```
در app.py تابع live_prices():
یک لاک اختصاصی برای LIVE_CACHE تعریف کن:
_LIVE_LOCK = threading.Lock()

check-then-set busy flag رو atomic کن:
with _LIVE_LOCK:
    if LIVE_CACHE.get('busy'):
        return LIVE_CACHE.get('data', {})
    LIVE_CACHE['busy'] = True

همچنین نوشتن LIVE_CACHE['ts'] و LIVE_CACHE['data'] در _refresh_live:
with _LIVE_LOCK:
    LIVE_CACHE['ts'] = time.time()
    LIVE_CACHE['data'] = out
    LIVE_CACHE['busy'] = False
```

---

### H3. SSRF از طریق ریدایرکت
**فایل:** `app.py` | **خط:** ~1335-1387  
**توضیح:** چک `_blocked_host()` فقط دامنه اولیه رو بررسی میکنه. `requests.get()` ریدایرکت‌ها رو follow میکنه و میتونه به `169.254.169.254` برسه.

**پرامپت:**
```
در app.py تابع api_proxy_image:
1. allow_redirects=False بذار روی requests.get()
2. اگه 3xx دریافت کردی، Location header رو چک کن و هاست مقصد رو هم با _blocked_host بررسی کن
3. یا از stream=True استفاده کن و بعد از download هدرها، چک کن

همچنین socket.getaddrinfo رو نه فقط check time بلکه بعد از resolve نهایی هم اجرا کن
(یا allow_redirects=False و follow دستی با چک هر hop).
```

---

### H4. `/api/refresh` بدون rate limiting
**فایل:** `app.py` | **خط:** ~1510-1513  
**توضیح:** هر کسی میتونه POST مکرر بزنه و cycle‌های parallel شروع کنه.

**پرامپت:**
```
در app.py endpoint /api/refresh (POST):
1. چک کن اگه RECOVERY_JOB['running'] یا STATE['stats']['cycle_running'] True هست، 
   429 برگردون با پیام "cycle in progress"
2. یا از CYCLE_LOCK استفاده کن: اگه lock قفله، 429 برگردون
3. یک timestamp آخرین refresh رو نگه دار و اگه کمتر از 60 ثانیه از آخری گذشته، 429 بده
```

---

### H5. api_settings token تلگرام رو برمیگردونه
**فایل:** `app.py` | **خط:** ~2108  
**توضیح:** Response کل CONFIG رو شامل telegram token برمیگردونه.

**پرامپت:**
```
در app.py endpoint api_settings:
قبل از jsonify کردن response، telegram_secret و telegram_chat_id و هر token حساسی 
رو از config کپی حذف کن یا ماسک کن:

safe = {k: v for k, v in CONFIG.items() if k not in ('telegram_secret', 'telegram_chat_id')}
response = {'ok': True, 'config': safe, ...}
```

---

### H6. Thundering herd روی FNG_CACHE
**فایل:** `app.py` | **خط:** ~1090-1096  
**توضیح:** وقتی _fng() خطا برمیگردونه (None)، cache هیچوقت ست نمیشه و هر درخواست دوباره API رو صدا میزنه.

**پرامپت:**
```
در app.py تابع _fng_cached (یا معادلش):
وقتی _fng() None برمیگردونه، cache رو با یک sentinel ست کن تا دوباره fetch نشه حداقل تا TTL:

result = _fng()
if result is None:
    result = {"error": "unavailable", "cached_at": time.time()}
FNG_CACHE['data'] = result
FNG_CACHE['ts'] = time.time()

همچنین یک لاک اضافه کن تا همزمان دو thread refresh نکنن:
_FNG_LOCK = threading.Lock()
```

---

### H7. MACRO_CACHE لیست خالی رو cache نمیکنه
**فایل:** `app.py` | **خط:** ~1102-1108  
**توضیح:** `not MACRO_CACHE['data']` برای `[]` هم True هست.

**پرامپت:**
```
در app.py تابع _macro_cached (یا معادلش):
شرط cache hit رو از:
  if MACRO_CACHE['data'] is not None and ...
تغییر بده به:
  if MACRO_CACHE['data'] is not None and ...
  
یعنی None رو check کن نه truthiness. لیست خالی [] هم باید cached باشه.
```

---

### H8. CANDLES_CACHE رشد نامحدود
**فایل:** `app.py` | **خط:** ~1123  
**توضیح:** هر (sym, tf) ترکیب بدون eviction رشد میکنه.

**پرامپت:**
```
در app.py:
وقتی CANDLES_CACHE بیشتر از 200 آیتم شد، قدیمی‌ترین‌ها رو بر اساس timestamp حذف کن:
if len(CANDLES_CACHE) > 200:
    oldest = min(CANDLES_CACHE, key=lambda k: CANDLES_CACHE[k].get('ts', 0))
    del CANDLES_CACHE[oldest]
```

---

### H9. Thundering herd روی CANDLES_CACHE
**فایل:** `app.py` | **خط:** ~1195-1197  
**توضیح:** درخواست‌های همزمان برای یک sym/tf هر کدوم Yahoo رو صدا میزنن.

**پرامپت:**
```
در app.py:
یک لاک یا asyncio.Lock برای هر sym+tf اضافه کن.
یا ساده‌تر: یک in-flight set نگه دار:
_CANDLES_INFLIGHT = set()

if key in _CANDLES_INFLIGHT:
    return CANDLES_CACHE.get(key, {})  # wait for first request
_CANDLES_INFLIGHT.add(key)
try:
    result = _yahoo_candles(...)
finally:
    _CANDLES_INFLIGHT.discard(key)
```

---

### H10. `art['id']` بدون .get() → KeyError
**فایل:** `app.py` | **خط:** ~1216, 1253, 1297  
**توضیح:** اگه مقاله‌ای فیلد `id` نداشته باشه، KeyError پرتاب میشه.

**پرامپت:**
```
در app.py:
تمام `a['id']` و `art['id']` رو با `a.get('id')` یا `art.get('id')` عوض کن.
بعدش اگه id None بود، اون مقاله رو skip کن:
aid = art.get('id')
if not aid:
    continue
```

---

### H11. ریداکشن‌های Reddit بدون تایم‌اوت و retry
**فایل:** `scraper.py` | **خط:** ~262  
**توضیح:** Reddit throttling سختی داره و تلاش با backoff 3 ثانیه‌ای ولی label "backoff-4s" هست.

**پرامپت:**
```
در scraper.py:
Label "backoff-4s" رو به "backoff-3s" تغییر بده تا با sleep واقعی 3 ثانیه مچ باشه.
```

---

### H12. re.escape space-replacement no-op
**فایل:** `sources.py` | **خط:** ~577  
**توضیح:** از Python 3.7+ `re.escape()` فاصله رو escape نمیکنه. `.replace('\\ ', '\\s+')` هیچوقت match نمیشه.

**پرامپت:**
```
در sources.py تابع build_custom_patterns:
خط زیر رو:
  pats.append(re.escape(k).replace(r'\\ ', r'\\s+'))
تغییر بده به:
  pats.append(re.sub(r'\\s+', r'\\\\s+', re.escape(k)))

یعنی اول escape کن، بعد هر sequence از \\s+ (شامل \\ یکتای) رو با \\s+ جایگزین کن.
```

---

### H13. urllib3.disable_warnings permanently
**فایل:** `scraper.py` | **خط:** ~584-585  
**توضیح:** Warning disable یه بار اجرا میشه و permanently global میمونه.

**پرامپت:**
```
در scraper.py تابع _fetch_attempt:
(urllib3.disable_warnings()) رو حذف کن یا فقط در scope محدود try اجرا کن.
اگه واقعاً نیازه، بعد از اتمام try block اونو restore کن.
```

---

### H14. socket.setdefaulttimeout permanent
**فایل:** `scraper.py` | **خط:** ~619  
**توضیح:** `socket.setdefaulttimeout(12)` timeout سراسری پروسه رو تغییر میده.

**پرامپت:**
```
در scraper.py تابع _fetch_attempt:
(socket.setdefaulttimeout(12)) رو حذف کن.
به جاش timeout رو مستقیماً به feedparser.parse بده اگه API اجازه میده.
یا مقدار قبلی رو save و restore کن:
old = socket.getdefaulttimeout()
socket.setdefaulttimeout(12)
try:
    feed = feedparser.parse(...)
finally:
    socket.setdefaulttimeout(old)
```

---

### H15. smoke_test.py کرش در خط 84-85
**فایل:** `smoke_test.py` | **خط:** ~84-85  
**توضیح:** خارج از if error guard، مستقیماً به `reps['BTC']['sections'][0][1]['asof_fa']` دسترسی داره.

**پرامپت:**
```
در smoke_test.py:
خطوط 84-85 رو داخل یک if wrapper قرار بده:
if reps.get('BTC') and not reps['BTC'].get('error'):
    print(...)
    print("asof_fa:", reps['BTC']['sections'][0][1].get('asof_fa', 'N/A'))
```

---

### H16. indicators.py tail() padding no-op
**فایل:** `indicators.py` | **خط:** ~215  
**توضیح:** `([-0.0] * 0) + seq` یه no-opه. سری‌های EMA/RSI/MACD کوتاه‌تر از dates array میشن.

**پرامپت:**
```
در indicators.py تابع tail():
خط زیر رو:
  return seq[-points:] if len(seq) >= points else ([-0.0] * 0) + seq
تغییر بده به:
  return seq[-points:] if len(seq) >= points else seq

یا اگه واقعاً padding لازمه (برای align شدن با dates array):
  return seq[-points:] if len(seq) >= points else [None] * (points - len(seq)) + seq
```

---

### H17. dashboard_html: renderFeed قبل از DATA null کرش
**فایل:** `dashboard_html.py` | **خط:** ~3011-3017  
**توضیح:** `renderFeed()` قبل از اینکه loadData اولیه تموم بشه صدا زده میشه.

**پرامپت:**
```
در dashboard_html.py تابع renderFeed:
اولین خط:
if (!DATA || !DATA.articles) return;
```

---

### H18. dashboard_html: دو setInterval همزمان loadData
**فایل:** `dashboard_html.py` | **خط:** ~2690-2694  
**توضیح:** هر دو timer بدون dedup loadData صدا میزنن.

**پرامپت:**
```
در dashboard_html.py:
یک flag سراسری اضافه کن:
let _LOADING = false;

در loadData():
async function loadData() {
  if (_LOADING) return;
  _LOADING = true;
  try {
    // ... existing code ...
  } finally {
    _LOADING = false;
  }
}
```

---

### H19. dashboard_html: Calendar index stale میشه
**فایل:** `dashboard_html.py` | **خط:** ~3662, 3760  
**توضیح:** `_idx` بر اساس position توی pool هست و بعد از re-render stale میشه.

**پرامپت:**
```
در dashboard_html.py:
به جای index عددی از یک unique key استفاده کن:
e._key = e.ts + '_' + e.title.replace(/[^a-zA-Z0-9]/g, '').slice(0, 20);
// در HTML:
onclick="openCalDoc('${e._key}')"
// در handler:
function openCalDoc(key) {
  const e = CAL_POOL.find(x => x._key === key);
  // ...
}
```

---

### H20. dashboard_html: Recovery poll DOM جدا شده
**فایل:** `dashboard_html.py` | **خط:** ~2837-2850  
**توضیح:** بعد از renderAll، reference به دکمه قدیمی stale میشه.

**پرامپت:**
```
در dashboard_html.py:
به جای ذخیره reference اولیه، هر بار DOM رو دوباره query کن:
setInterval(() => {
  const b = document.getElementById('recoverBtn');
  if (!b) return;
  // ... write to b ...
}, 3000);
```

---

## 🟡 Medium — ۳۴ مورد

---

### M1. last_duration قبل از ترجمه آپدیت میشه
**فایل:** `app.py` | **خط:** ~372  
**توضیح:** مقدار نادرستی که شامل ترجمه و report نیست.

**پرامپت:** `در app.py خط 372 (آخرین last_duration) رو فقط یک بار در انتهای run_cycle و بعد از همه مراحل ست کن.`

---

### M2. FA_REPORT_CACHE هر cycle پاک میشه
**فایل:** `app.py` | **خط:** ~388  
**توضیح:** `.clear()` بدون بررسی freshness.

**پرامپت:** `FA_REPORT_CACHE.clear() رو حذف کن. بذار TTL خودش expire کنه.`

---

### M3. Thread گرمایش مقالات بدون محدودیت
**فایل:** `app.py` | **خط:** ~422  

**پرامپت:** `یک counter نگه دار. اگه thread قبلی هنوز داره اجرا میشه (is_alive)، thread جدید نساز.`

---

### M4. خطا در نوشتن report JSON بلعیده میشه
**فایل:** `app.py` | **خط:** ~400-403  

**پرامپت:** `except Exception: pass رو به except Exception as e: log(f'  x report save failed: {e}') تغییر بده.`

---

### M5. Shallow copy از STATE['stats']
**فایل:** `app.py` | **خط:** ~624  

**پرامپت:** `از json.loads(json.dumps(STATE['stats'])) یا copy.deepcopy استفاده کن.`

---

### M6. `now = now or time.time()` falsy-zero
**فایل:** `app.py` | **خط:** ~1029  

**پرامپت:** `به if now is None: now = time.time() تغییر بده.`

---

### M7. FNG_SYM_CACHE رشد نامحدود
**فایل:** `app.py` | **خط:** ~1057-1070  

**پرامپت:** `یک سایز cap (مثلاً 200) بذار. اگه بیشتر شد، قدیمی‌ترین رو حذف کن.`

---

### M8. MACRO_CACHE empty-list cache نمیکنه
**فایل:** `app.py` | **خط:** ~1102-1108  

**پرامپت:** `شرط `not MACRO_CACHE['data']` رو به `MACRO_CACHE['data'] is None` تغییر بده.`

---

### M9. CANDLES_CACHE رشد نامحدود
**فایل:** `app.py` | **خط:** ~1123  

**پرامپت:** `cap روی 200 آیتم بذار، قدیمی‌ترین‌ها رو حذف کن.`

---

### M10. art['id'] KeyError
**فایل:** `app.py` | **خط:** ~1216, 1253, 1297  

**پرامپت:** `تمام a['id'] و art['id'] رو با .get('id') عوض کن و اگه None بود skip کن.`

---

### M11. تصویر کامل قبل از چک سایز download
**فایل:** `app.py` | **خط:** ~1369  

**پرامپت:** `stream=True بذار. اول Content-Length رو چک کن. اگه > 5MB بود، stream نخون و قطع کن.`

---

### M12. Race condition نوشتن فایل کش تصویر
**فایل:** `app.py` | **خط:** ~1381-1382  

**پرامپت:** `اول به فایل موقت (.tmp) بنویس، بعد atomic rename کن (os.replace).`

---

### M13. ترجمه خالی به جای fallback به انگلیسی
**فایل:** `app.py` | **خط:** ~1440  

**پرامپت:** `اگه ترجمه خالی بود، مقدار اصلی انگلیسی رو بنویس: val.get('en')`

---

### M14. FA_REPORT_CACHE بدون لاک نوشته میشه
**فایل:** `app.py` | **خط:** ~1447  

**پرامپت:** `زیر _FA_REPORT_LOCK بنویس.`

---

### M15. Telegram digest [:4000] وسط HTML بریده
**فایل:** `app.py` | **خط:** ~1744  

**پرامپت:** `محدودیت رو به 4096 تغییر بده و بعد از آخرین </p> یا </b> ببُر نه وسط تگ.`

---

### M16. Hash collision custom source key
**فایل:** `app.py` | **خط:** ~2072  

**پرامپت:** `یک UUID کوتاه یا timestamp به hash اضافه کن: 'custom_' + uuid.uuid4().hex[:8]`

---

### M17. busy-wait نامحدود warm_article_bodies
**فایل:** `app.py` | **خط:** ~3192  

**پرامپت:** `یک max wait (مثلاً 60 ثانیه) اضافه کن. بعد از اون break کن.`

---

### M18. 304 با ok=True و لیست خالی
**فایل:** `scraper.py` | **خط:** ~691-694  

**پرامپت:** `وقتی 304 دریافت شد، status['not_modified'] = True رو حفظ کن ولی arts رو empty list بذار و ok=True.`

---

### M19. Dedup key 64 کاراکتری false-positive
**فایل:** `scraper.py` | **خط:** ~787  

**پرامپت:** `truncation limit رو به 128 تغییر بده یا hash کل title رو بگیر.`

---

### M20. مقالات بدون published_ts freshness bypass
**فایل:** `scraper.py` | **خط:** ~821  

**پرامپت:** `اگه published_ts None بود، مقاله رو reject کن یا now رو به عنوان timestamp بذار.`

---

### M21. Race condition OG_CACHE
**فایل:** `scraper.py` | **خط:** ~172-173  

**پرامپت:** `یک threading.Lock اضافه کن یا از dict.setdefault برای atomic set استفاده کن.`

---

### M22. RSI = 100.0 وقتی avg_gain و avg_loss هر دو صفرن
**فایل:** `indicators.py` | **خط:** ~45-46  

**پرامپت:** `شرط: if avg_loss == 0 and avg_gain == 0: return 50.0`

---

### M23. database.py ON CONFLICT 5 ستون فقط
**فایل:** `database.py` | **خط:** ~220-233  

**پرامپت:** `تمام ستون‌های مهم (title, link, source_name, published_ts, source_trust, tier, topic, topic_fa) رو هم به ON CONFLICT UPDATE اضافه کن.`

---

### M24. database.py connections هیچوقت close نمیشن
**فایل:** `database.py` | **خط:** ~43+  

**پرامپت:** `به جای sqlite3.connect(...) ساده، یک helper بنویس که connection رو با conn.close() در finally ببنده.
یا context manager اختصاصی بنویس:

@contextmanager  
def db_conn():
    conn = sqlite3.connect(...)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()`

---

### M25. report_generator a['title'] بدون .get()
**فایل:** `report_generator.py` | **خط:** ~259  

**پرامپت:** `a['title']` رو با `a.get('title', '')` عوض کن.`

---

### M26. fa_ago ساعت منفی → "۱ دقیقه پیش"
**فایل:** `fa_format.py` | **خط:** ~107-109  

**پرامپت:** `اول تابع: if hours is not None and hours < 0: return ""`

---

### M27. calendar_data.py datetime خام با timezone سیستم
**فایل:** `calendar_data.py` | **خط:** ~812  

**پرامپت:** `اگه datetime خام بود، explicit UTC فرض کن:
dt = datetime.fromisoformat(it['date']).replace(tzinfo=timezone.utc)`

---

### M28. news_bypass.py Google Cache URL encode نشده
**فایل:** `news_bypass.py` | **خط:** ~359  

**پرامپت:** `url رو با quote_plus encode کن:
from urllib.parse import quote_plus
return f'https://webcache.googleusercontent.com/search?q=cache:{quote_plus(url)}&strip=1'`

---

### M29. news_bypass.py cloudscraper create_scraper بدون try/except
**فایل:** `news_bypass.py` | **خط:** ~268  

**پرامپت:** `cloudscraper.create_scraper() رو داخل try/except قرار بده و اگه fail کرد، self.scraper = None بذار.`

---

### M30. tv_ideas.py bracket matcher string context نداره
**فایل:** `tv_ideas.py` | **خط:** ~70-79  

**پرامپت:** `به جای manual bracket matching، از json.JSONDecoder با raw_decode استفاده کن.`

---

### M31. tv_ideas.py timestamp=0 falsy
**فایل:** `tv_ideas.py` | **خط:** ~183-184  

**پرامپت:** `if ts else None` رو به `if ts is not None else None` تغییر بده.`

---

### M32. dashboard_html: renderFeed null guard
**فایل:** `dashboard_html.py` | **خط:** ~3011  

**پرامپت:** `اول renderFeed: if (!DATA || !DATA.articles) return;`

---

### M33. dashboard_html: Calendar index stale
**فایل:** `dashboard_html.py` | **خط:** ~3662, 3760  

**پرامپت:** `به جای index عددی از unique key استفاده کن (مثلاً title hash).`

---

### M34. dashboard_html: Recovery poll detached DOM
**فایل:** `dashboard_html.py` | **خط:** ~2837-2850  

**پرامپت:** `هر بار getElementById('recoverBtn') رو دوباره از DOM بگیر.`

---

## 🔵 Low — ۱۵ مورد

---

### L1. import تکراری hidden_ids
**فایل:** `app.py` | **خط:** ~285  
**پرامپت:** `import رو به بالای فایل ببر.`

---

### L2. Auth token هر request از env خونده میشه
**فایل:** `app.py` | **خط:** ~571  
**پرامپت:** `مقدار token رو یک بار در startup cache کن.`

---

### L3. BUILTIN_MACRO هر request append میشه
**فایل:** `app.py` | **خط:** ~632  
**پرامپت:** `نتیجه رو cache کن یا فقط وقتی CONFIG تغییر کرد compute کن.`

---

### L4. Log label غلط backoff-4s
**فایل:** `scraper.py` | **خط:** ~262  
**پرامپت:** `به "backoff-3s" تغییر بده.`

---

### L5. _DIRTY بدون لاک
**فایل:** `translate.py` | **خط:** ~208  
**پرامپت:** `زیر _LOCK بنویس.`

---

### L6. pct() مقدار 0.0 رو invalid تلقی میکنه
**فایل:** `indicators.py` | **خط:** ~103  
**پرامپت:** `if not b → if b == 0`

---

### L7. Dead code lo/hi در pivot_levels
**فایل:** `sources.py` | **خط:** ~116-123  
**پرامپت:** `خطوط lo = min(window) و hi = max(window) رو حذف کن.`

---

### L8. to_tehran datetime خام silent UTC
**فایل:** `fa_format.py` | **خط:** ~63  
**پرامپت:** `یک warning لاگ کن یا minimum تغییر بده.`

---

### L9. fa_ago(0) → "۱ دقیقه پیش"
**فایل:** `fa_format.py` | **خط:** ~112  
**پرامپت:** `if minutes < 1: return "همین حالا"` یا `return "۰ دقیقه پیش"`

---

### L10. smoke_test: list bounds check
**فایل:** `smoke_test.py` | **خط:** ~70  
**پرامپت:** `if len(c["items"]) > 1: before accessing [i+1]`

---

### L11. database.py SQL with % formatting
**فایل:** `database.py` | **خط:** ~285-296  
**پرامپت:** `الان safe هست ولی نظرت رو بنویس. اگه user input وارد شد، parameterize کن.`

---

### L12. pollLive silent error
**فایل:** `dashboard_html.py` | **خط:** ~2906-2910  
**پرامپت:** `یک console.error(e) یا toast خطا اضافه کن.`

---

### L13. toggleSrc await نداره
**فایل:** `dashboard_html.py` | **خط:** ~2959-2961  
**پرامپت:** `toast رو بعد از await بزن نه قبلش. try/catch اضافه کن.`

---

### L14. removeAsset loadData await نداره
**فایل:** `dashboard_html.py` | **خط:** ~3502-3504  
**پرامپت:** `await loadData() بزن.`

---

### L15. loadData HTTP status check نداره
**فایل:** `dashboard_html.py` | **خط:** ~2677-2688  
**پرامپت:** `if (!r.ok) throw new Error(r.status + ' ' + r.statusText); قبل از r.json()`

---

## پرامپت‌های جامع برای رفع گروهی

### پرامپت ۱ — رفع همه Critical‌ها
```
فایل E:/freebuff/app.py و dashboard_html.py رو باز کن.

این ۵ باگ Critical رو رفع کن (فقط اینا، بقیه دست نخوره):

1. app.py ~خط 391: مقالاتی که وارد STATE['articles'] میشن باید deep copy باشن.
   قبل از قرار دادن در STATE: live = [json.loads(json.dumps(a)) for a in live]

2. app.py ~خط 382: سه لاک اختصاصی برای CONTENT_CACHE, FA_CONTENT_CACHE, FA_REPORT_CACHE بساز.
   تمام خواندن/نوشتن تحت لاک باشه.

3. app.py ~خط 1787: requests.get() برای pinChatMessage → requests.post()

4. app.py ~خط 2905: guard اول fetch_article_content:
   if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
       return {"paragraphs": [], "word_count": 0, "partial": True, "title": "", "url": url or "", "method": "none"}

5. dashboard_html.py ~خط 2545: تابع esc() رو پیدا کن و بعد از اسکیپ دبل‌کوتیشن، اضافه کن:
   s = s.replace(/'/g, "\\'");

هر تغییر فقط دقیقاً همون خطوط رو عوض کنه. بقیه کد دست نخوره.
```

### پرامپت ۲ — رفع همه High‌ها
```
فایل E:/freebuff/app.py رو باز کن و این ۲۰ باگ High رو رفع کن:

1. یک _CONFIG_LOCK = threading.Lock() تعریف کن و تمام خواندن/نوشتن CONFIG رو تحت اون لاک قرار بده.
2. یک _LIVE_LOCK بساز و busy-flag و نوشتن LIVE_CACHE رو atomic کن.
3. api_proxy_image: allow_redirects=False بذار و ریدایرکت‌ها رو hand-check کن.
4. /api/refresh: اگه cycle_running=True هست، 429 برگردون.
5. api_settings response: telegram_secret رو حذف یا mask کن.
6. FNG_CACHE: اگه _fng() None برگردوند، cache با sentinel بذار.
7. MACRO_CACHE: شرط `not data` → `data is None`
8. CANDLES_CACHE: cap 200 + dedup با in-flight set
9. تمام art['id'] و a['id'] → art.get('id') با guard
10. scraper.py: urllib3.disable_warnings() حذف
11. scraper.py: socket.setdefaulttimeout save/restore
12. smoke_test.py خط 84: if reps.get('BTC') and not reps['BTC'].get('error')
13. indicators.py: tail() padding [None] * (points - len(seq)) + seq
14. sources.py: re.escape space fix: re.sub(r'\\s+', r'\\\\s+', re.escape(k))
15. sources.py: malware regex: malf?are → mal(?:w|f)are
16. sources.py: solana/cardano/bnb/dogecoin trailing \\b اضافه کن
17. dashboard_html.js: renderFeed null guard
18. dashboard_html.js: _LOADING flag for dual setInterval
19. dashboard_html.js: calendar key instead of index
20. dashboard_html.js: recovery poll getElementById هر بار

فقط این ۲۰ تا، بقیه دست نخوره.
```

### پرامپت ۳ — رفع همه Medium‌ها
```
فایل‌های E:/freebuff/app.py, scraper.py, indicators.py, database.py, report_generator.py, 
fa_format.py, calendar_data.py, news_bypass.py, tv_ideas.py, dashboard_html.py رو باز کن.

این ۳۴ باگ Medium رو رفع کن:

app.py:
1. last_duration فقط در انتهای run_cycle آپدیت بشه
2. FA_REPORT_CACHE.clear() حذف بشه
3. Thread گرمایش مقالات: is_alive check
4. except → log
5. stats deep copy
6. now = now or time.time() → if now is None
7. FNG_SYM_CACHE cap 200
8. MACRO_CACHE None check
9. CANDLES_CACHE cap
10. art['id'] → .get()
11. stream=True برای تصویر proxy
12. atomic write تصویر cache
13. fallback to English when translation empty
14. FA_REPORT_CACHE under lock
15. Telegram digest: preserve HTML tags while truncating
16. Custom source UUID key
17. warm_article_bodies max wait

scraper.py:
18. 304 status handling
19. Dedup key 128 chars
20. Reject undated articles
21. OG_CACHE lock

indicators.py:
22. RSI flat market → 50.0

database.py:
23. ON CONFLICT more columns
24. Connection close

report_generator.py:
25. a.get('title', '')

fa_format.py:
26. Negative hours → ""

calendar_data.py:
27. Naive datetime → UTC
28. _fmt_num inf/nan guard

news_bypass.py:
29. Google Cache URL encode
30. cloudscraper try/except

tv_ideas.py:
31. json.JSONDecoder for bracket matching
32. timestamp=0 not falsy

dashboard_html.py:
33. renderFeed null guard
34. calendar unique key

فقط این ۳۴ تا.
```

### پرامپت ۴ — رفع همه Low‌ها
```
فایل‌های زیر رو باز کن و این ۱۵ باگ Low رو رفع کن:

1. app.py: import hidden_ids به بالای فایل
2. app.py: Auth token در startup cache کن
3. app.py: BUILTIN_MACRO cache
4. scraper.py: log label "backoff-4s" → "backoff-3s"
5. translate.py: _DIRTY زیر _LOCK
6. indicators.py: pct() if not b → if b == 0
7. sources.py: dead code lo/hi حذف
8. fa_format.py: to_tehran warning برای naive datetime
9. fa_format.py: fa_ago(0) → "همین حالا"
10. smoke_test.py: list bounds check
11. dashboard_html.py: pollLive console.error
12. dashboard_html.py: toggleSrc try/catch + toast بعد await
13. dashboard_html.py: removeAsset await loadData
14. dashboard_html.py: loadData HTTP status check
15. database.py: SQL % formatting note (اگه safe هست فقط comment بذار)

فقط این ۱۵ تا.
```

---

## 📋 چک‌لیست نهایی

- [ ] ۵ Critical
- [ ] ۲۰ High
- [ ] ۳۴ Medium
- [ ] ۱۵ Low
- [ ] تست نهایی: `python smoke_test.py` بدون خطا اجرا بشه
- [ ] تست: Flask server بالا بیاد و `/api/data` JSON معتبر برگردونه
- [ ] تست: ترجمه فارسی مقالات کار کنه
- [ ] تست: گزارش‌ها حداقل ۴ پاراگراف technical analysis داشته باشن
