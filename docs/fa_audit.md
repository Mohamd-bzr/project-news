# FA translation audit — Phase 0

Measured on 2026-10-12 against `.mohmd_news.db` (18643 articles) and a read-only copy of `.translate_cache.json` (37180 entries).

### 1. Engine facts confirmed by reading `translate.py`

| # | Fact | Evidence (translate.py) |
|---|------|--------------------------|
| A1 | Every non-empty engine result is cached unconditionally, including English echoes; `to_persian()`'s "retry" goes through `translate_one()` → `translate_many()`, which re-reads the very same poisoned entry — no second network request ever happens for a failed text. | cache write: `translate_many` lines 289-298; retry path: `to_persian` 228-240, `translate_one` 304-307 |
| A2 | `_looks_persian()` (>25% Persian chars over *all* chars) identity-maps mixed texts; the `is_persian()` gate (≥45% Persian letters, Latin run < 4) then rejects them, and `to_persian()` cannot rescue them because `translate_one()` hits the same identity bypass. | `_looks_persian` 167-173, identity map 264-267; gate 216-225 |
| A3 | `_translate_batch()` sends up to 16 `q` params in one GET; non-200 (except 429/5xx retries) → `[]` (whole batch stays English); short responses are padded with `""` **at the end**, so a mid-drop misaligns translations with sources. | 131-156, pad at 143-144 |
| A4 | Cached values already have `fa_digits` applied, and the cache key is `md5(source)` only — the `persian_digits` flag is not part of the key. | store at 293-297; key at 60-61 |

### 2. What the dashboard publishes (`title_fa` / `summary_fa`)

- Titles: **18643/18643** rows carry `title_fa`; **17873/18643 pass is_persian = 95.9%** (**770 failing**).
- Summaries (source ≥ 40 chars): **17903/18117** carry `summary_fa`; **17034/17903 pass = 95.1%** (**869 failing**).
- Failure reasons — titles: pure echo (no Persian letters) **41**, half-translated (Latin run ≥ 4) **635**, low Persian share (< 45%) **94**.
- Failure reasons — summaries: echo **10**, half **827**, low share **32**.
- Failure reasons — source language (heuristic screen): **56/770 = 7.3%** of failing titles have a non-English source (top: fr 43, de 7, nl 4, it 1); with `sl=en` those texts cannot be translated by the endpoint at all (see §9).
- Source side: **2/18643** titles and **1/18117** summaries are natively Persian (the rest are English — or French/Spanish, see §5).

### 3. Cache audit (read-only copy of `.translate_cache.json`)

- Entries: **37180** (read from a temp copy; real file untouched).
- Pass is_persian: **35442 = 95.3%**; **fail: 1738 = 4.7%**.
- Failure kinds — pure echo (no Persian letters): **62**, half-translated (Latin run ≥ 4): **1513**, low Persian share (< 45%): **163**.
- Entries whose md5 key joins back to an `articles` source: **28147/37180 = 75.7%** (the rest come from ideas/paragraphs/events).
- Of the joined *echo* failures, **16 are byte-identical to their source** — the endpoint literally answered with the input again (A1).
- Values containing Persian digits: **18985/37180 = 51.1%** — `fa_digits` runs before the store (A4).

### 4. Identity-mapped by `_looks_persian` but rejected by `is_persian` (never rescuable today, A2)

- Texts flowing into `translate_many` (titles + summaries ≥ 40 chars): **36760**.
- `_looks_persian(t) and not is_persian(t)`: **0** = 0.0%.
- Of those, currently published unchanged (output == input): **0**.

### 5. 100 most frequent untranslated Latin tokens in published outputs

Counted over every `title_fa` + `summary_fa`; `in failing` = occurrences inside outputs that fail `is_persian`.

| # | token | count | in failing | in passing | example context |
|---|-------|------:|-----------:|-----------:|-----------------|
| 1 | `xrp` | 2538 | 138 | 2400 | ه تحلیلگر، در اینجا مسیر XRP به ۲ دلار است |
| 2 | `etf` | 2109 | 220 | 1889 | دهای آتی دائمی در سهام و ETFهای ایالات متحده ثبت نام  |
| 3 | `eth` | 652 | 71 | 581 | لار افزایش یافت. اتریوم (ETH) همچنین به بالاترین قیمت |
| 4 | `nifty` | 624 | 77 | 547 | یارهای سهام هند Sensex و Nifty در روز جمعه با افزایش به |
| 5 | `btc` | 551 | 76 | 475 | فه می کند زیرا بیت کوین (BTC) از ۸۱ هزار دلار عبور می |
| 6 | `s&p` | 523 | 28 | 495 | S&P ۵۰۰ از سال ۱۹۵۸ سالانه ح |
| 7 | `solana` | 515 | 110 | 405 | بلاک چین Allfunds Solana را برای استراتژی توزیع و |
| 8 | `dogecoin` | 488 | 20 | 468 | ۶۷.۵ میلیون Dogecoin پشتیبان AI محور SANGRIX  |
| 9 | `crypto` | 483 | 149 | 334 | SEC Crypto Custody Rewrite وارد برر |
| 10 | `sec` | 472 | 37 | 435 | SEC Crypto Custody Rewrite و |
| 11 | `ada` | 409 | 41 | 368 | و ۱۱ درصد: آنچه دارندگان ADA باید قبل از رای گیری خزا |
| 12 | `cardano` | 402 | 66 | 336 | Cardano Price Dynamics در یک منظ |
| 13 | `nasdaq` | 400 | 139 | 261 | قیمت سهام استراتژی (NASDAQ: MSTR) در ۱۸ سپتامبر ۱۶  |
| 14 | `sol` | 399 | 43 | 356 | سولانا (SOL) با جهش ۱۰.۷۵ درصدی از ۱ |
| 15 | `rbi` | 380 | 19 | 361 | RBI هند ۱۰ میلیارد دلار سوآپ |
| 16 | `remittix` | 362 | 18 | 344 | LARITY پیروی می کند زیرا Remittix به قیمت بعدی خود نزدیک م |
| 17 | `sensex` | 360 | 55 | 305 | معیارهای سهام هند Sensex و Nifty در روز جمعه با ا |
| 18 | `coinbase` | 326 | 31 | 295 | Coinbase Derivatives برای فهرست ق |
| 19 | `de` | 322 | 314 | 8 | ضرابخانه فرانسوی Monnaie de Paris. آنها ۲۲.۲ گرم در  |
| 20 | `cftc` | 315 | 4 | 311 |  Onchain پاک می کند زیرا CFTC کمک نرم افزاری را گسترش  |
| 21 | `zcash` | 301 | 48 | 253 | طرح ETF Zcash Grayscale ۳-for-۱ پس از  |
| 22 | `d` | 269 | 184 | 85 | ده باش https://preview.redd.it/۰e۲pjawt۰bqh۱.png?wi |
| 23 | `usdt` | 259 | 21 | 238 | بران اجازه می دهد USDC و USDT را در مقابل HYPE یا بیت  |
| 24 | `x` | 258 | 54 | 204 |  اخبار اتریوم: EIP-۸۳۶۵ ۰x۰۰ قدیمی را هدف قرار می د |
| 25 | `usdc` | 257 | 14 | 243 | وزارت خزانه داری USDC استخراج ۲۵۰ میلیون دلار  |
| 26 | `edt` | 257 | 0 | 257 | تامبر ۲۰۲۶ در ساعت ۳ صبح EDT بازار پیش بینی |
| 27 | `doge` | 242 | 24 | 218 | تم متمرکز بر پرداخت خود، DOGE به بالای ۰.۰۸۵ دلار بازگ |
| 28 | `defi` | 240 | 19 | 221 | دلار از دست داد: درس های DeFi برای کاربران |
| 29 | `ledger` | 239 | 27 | 212 | XRP Ledger با افزایش قیمت ۱.۴۳ دلار |
| 30 | `le` | 217 | 213 | 4 | Phong Le مدیر عامل استراتژی مجله  |
| 31 | `l` | 215 | 130 | 85 | رسال شده توسط /u/KateR_H۰l۱day [پیوند] [نظر] |
| 32 | `s` | 214 | 142 | 72 | ی را در شبکه اصلی Circle’s Arc راه‌اندازی کرد و مشت |
| 33 | `gold` | 208 | 92 | 116 | Snowline Gold: Early Ounces Valley's S |
| 34 | `the` | 203 | 84 | 119 | The post بهترین سهام نفت در  |
| 35 | `https` | 201 | 59 | 142 | ورد r/ethereum خوش آمدید https://imgur.com/۳y۷vezP نشان |
| 36 | `hyperliquid` | 195 | 25 | 170 | یک نهنگ بزرگ Hyperliquid موقعیت کوتاه بزرگی را کا |
| 37 | `les` | 192 | 191 | 1 | Les marchés predictifs antic |
| 38 | `circle` | 190 | 29 | 161 | ۹۴.۵ میلیون یورو از EURC Circle گزارش داد. |
| 39 | `ripple` | 189 | 39 | 150 | شوارتز، مدیر ارشد فناوری Ripple، قطع ارتباط همتایان کمتر |
| 40 | `okx` | 184 | 29 | 155 | OKX ۷۰ سهام و ETF توکن شده ا |
| 41 | `la` | 184 | 180 | 4 | Más Plata para la Reserva |
| 42 | `bitget` | 178 | 5 | 173 | Bitget CLO در هشتمین سالگرد امن |
| 43 | `a` | 176 | 79 | 97 | چرا Linera با پشتوانه a۱۶z قبل از M |
| 44 | `news` | 175 | 61 | 114 | Crypto News: Upbit برای حذف ICX/KRW  |
| 45 | `nyse` | 167 | 34 | 133 | دیا برای عرضه اولیه سهام NYSE در حالی که قراردادها به  |
| 46 | `ai` | 162 | 38 | 124 |  میلیون Dogecoin پشتیبان AI محور SANGRIX (BTOG) است |
| 47 | `k` | 160 | 21 | 139 |  بخرم، و اکنون با قیمت ۸۱k، FML، به آن نگاه کنید، ت |
| 48 | `binance` | 154 | 25 | 129 | میلیارد جریان نهنگ را در Binance جذب می کنند و شکست روزان |
| 49 | `clarity` | 151 | 11 | 140 |  به دلیل گزارش های قانون CLARITY انتقاد می کند |
| 50 | `bitwise` | 149 | 23 | 126 | چرا CIO Bitwise معتقد است که کریپتو می ت |
| 51 | `prnewswire` | 149 | 93 | 56 |  عربی، ۲۱ سپتامبر ۲۰۲۶ / PRNewswire/ - Bybit، دومین برنامه ب |
| 52 | `bitcoin` | 145 | 110 | 35 | $Bitcoin (BTC.CC)$ شورت GG ۲,۱ |
| 53 | `near` | 145 | 38 | 107 | حلیل قیمت Uniswap (UNI)، Near Protocol (NEAR)، Hyperli |
| 54 | `token` | 143 | 38 | 105 | اپیتول سنگاپور برای هفته Token۲۰۴۹ می آورد |
| 55 | `strategy` | 136 | 15 | 121 | Coinbase، Strategy و سایر سهام مرتبط با رمز |
| 56 | `robinhood` | 134 | 12 | 122 | مسیر پیش‌فرض رمزارز Robinhood برای معامله بیت‌کوین تقر |
| 57 | `b` | 134 | 41 | 93 | preview.redd.it/۰e۲pjawt۰bqh۱.png?width=۱۸۶۴&format |
| 58 | `inc` | 132 | 87 | 45 | در حالی که BlackRock Inc. (NYSE: BLK) برای تقسیم  |
| 59 | `bnb` | 131 | 25 | 106 | Genius.fun در زنجیره BNB راه اندازی شد تا تصاحب خ |
| 60 | `ipo` | 131 | 11 | 120 | آیا باید در یک ETF IPO Anthropic سرمایه گذاری ک |
| 61 | `hype` | 126 | 20 | 106 | قیمت HYPE Crypto با افزایش وام های |
| 62 | `e` | 126 | 87 | 39 | مردم آماده باش https://preview.redd.it/۰e۲pjawt۰bqh |
| 63 | `et` | 120 | 113 | 7 | ین را کنار می‌گذارد (۱۸۳۷ET): این سریع بود، و در نها |
| 64 | `en` | 119 | 117 | 2 | eht Ripple vor der nächsten großen Bewegung؟ - newsb |
| 65 | `sur` | 118 | 117 | 1 | «حفاری‌های جاری در Bonza Sur همچنان از تفسیر زمین‌شنا |
| 66 | `zec` | 116 | 27 | 89 | مله در بورس (ETF) Zcash (ZEC) در هفته منتهی به ۱۸ سپت |
| 67 | `ethereum` | 112 | 63 | 49 | The post Solana vs Ethereum: چه کسی در مسابقه On-Cha |
| 68 | `des` | 112 | 110 | 2 | ون توکن ها، du staking و des rachats |
| 69 | `v` | 109 | 29 | 80 |  درصدی در حالی که تراکنش V۱ فعال می شود، بالای ۱۱۰  |
| 70 | `cpi` | 107 | 1 | 106 | CPI سنگاپور همانطور که انتظا |
| 71 | `ad` | 105 | 49 | 56 | اکتبر ۲۰۲۶ بسته می‌شوند. Ad Ad Lemon عملیات برزیل را |
| 72 | `une` | 105 | 105 | 0 | o qui n’est pas lui-même une valeur mobilière peut to |
| 73 | `fomc` | 104 | 3 | 101 | ۶f۶۱۳۹۴۹۹۴a۷ca۰۷a۵۳d۹bfd FOMC در حال حاضر برای ActsFlo |
| 74 | `g` | 103 | 17 | 86 |  در هفته‌های آتی کشورهای G۷ را برای هماهنگ کردن سطح |
| 75 | `f` | 103 | 58 | 45 | tps://preview.redd.it/۰۰hfhhhggaqh۱.png?width=۱۶۶۹& |
| 76 | `finance` | 102 | 28 | 74 |  ۲۰۲۶ با XRP در موج بعدی Finance اجرا می شود |
| 77 | `q` | 101 | 5 | 96 |  داشته است. آنچه در مورد Q۴ می گوید |
| 78 | `bank` | 100 | 42 | 58 | رایی با SNB Bancshares و Bank of Eufaula را اعلام کرد. |
| 79 | `silver` | 98 | 54 | 44 | Sunshine Silver Mining موقعیت حقوق مواد  |
| 80 | `evernorth` | 97 | 18 | 79 | Evernorth برای خریدهای XRP، فعالیت |
| 81 | `aave` | 95 | 19 | 76 | پیشنهاد Aave بیت کوین تحت کنترل آنکور |
| 82 | `fx` | 94 | 3 | 91 | د از طریق یک تراکنش مجاز FX یا یک حساب واقعی غیر مقی |
| 83 | `boj` | 94 | 0 | 94 |  پس از افزایش ۱.۲۵ درصدی BOJ افزایش یافت، اما آزمایش  |
| 84 | `xau/usd` | 94 | 4 | 90 | ز قرار می دهد تحلیل طلا (XAU/USD): تثبیت قبل از مذاکرات ک |
| 85 | `t` | 93 | 53 | 40 | ک لیموی مطلق بود. بیش از t |
| 86 | `kalshi` | 93 | 2 | 91 | Kalshi برای قراردادهای آتی دائم |
| 87 | `un` | 93 | 93 | 0 | ه‌های پرسنل وقایع پیشین. Un actif crypto qui n’est p |
| 88 | `pepeto` | 91 | 9 | 82 | Eyes Dijkstra در حالی که Pepeto در پیش فروش از ۱۱ میلیون |
| 89 | `wti` | 89 | 0 | 89 | نفت خام WTI در قرارداد نوامبر با ۱.۶ |
| 90 | `chainlink` | 89 | 18 | 71 |  کلود پیش‌بینی می‌کند که Chainlink (LINK) تا ۱ ژانویه ۲۰۲۷  |
| 91 | `openai` | 87 | 10 | 77 | کاربران از OpenAI، Anthropic، xAI و Google |
| 92 | `xrpl` | 85 | 11 | 74 | RP با گسترش بیشتر فعالیت XRPL است |
| 93 | `ondo` | 85 | 6 | 79 | Ondo’s Oasis Pro به صندوق DTC |
| 94 | `bitmine` | 85 | 33 | 52 | داری اتریوم، SharpLink و BitMine Eye را افزایش می‌دهد، زی |
| 95 | `blackrock` | 84 | 14 | 70 | شده وارد شده است که توسط BlackRock IBIT رهبری می شود. این ت |
| 96 | `pi` | 84 | 4 | 80 | پیش‌بینی قیمت شبکه Pi به‌عنوان به‌روزرسانی‌های |
| 97 | `alphapepe` | 84 | 2 | 82 | دیگر ارائه دهد؟ خریداران AlphaPepe به دنبال سکه AI Meme هست |
| 98 | `global` | 82 | 24 | 58 |  می شد، علیرغم اینکه BiT Global فروشنده بود، تا زمانی که |
| 99 | `mica` | 81 | 5 | 76 | زی اروپا در پیشنهاد مجوز MiCA یونان بایننس مداخله کرده |
| 100 | `kitco` | 81 | 20 | 61 | لا شکست نخورد: دلیل آن - KITCO |

### 6. 200 most frequent source n-grams (1–4 words) in headlines, with current Persian renderings

Pure-digit n-grams excluded (numbers are copied verbatim, not glossary targets). Examples are the shortest headlines containing the n-gram; the rendering shown is their current `title_fa`.

| # | n-gram | n | headlines | example: source → output |
|---|--------|---|----------:|--------------------------|
| 1 | `to` | 1 | 4318 | bitcoin to hit $300k → بیت کوین به ۳۰۰ هزار دلار رسید ／ Sold my car to buy btc → ماشینم را برای خرید btc فروختم |
| 2 | `as` | 1 | 3861 | Buying gold as investment → خرید طلا به عنوان سرمایه گذاری ／ As for me, I just Lite the coin. → در مورد من، من فقط سکه را لایت می کنم. |
| 3 | `in` | 1 | 3051 | In The Blink Of An Eye → در یک چشم به هم زدن ／ Big Oil’s day in court → روز بزرگ نفت در دادگاه |
| 4 | `the` | 1 | 2993 | Be on the lookout!!! → مواظب باشید!!! ／ The gang is all here. → باند همه اینجا هستند. |
| 5 | `and` | 1 | 2860 | Ethereum and Bitcoin → اتریوم و بیت کوین ／ Show and tell time :) → زمان را نشان بده و بگو :) |
| 6 | `bitcoin` | 1 | 2811 | bitcoin to hit $300k → بیت کوین به ۳۰۰ هزار دلار رسید ／ Ethereum and Bitcoin → اتریوم و بیت کوین |
| 7 | `gold` | 1 | 2332 | Are these real gold? → آیا اینها طلای واقعی هستند؟ ／ Gold newbie question → سوال طلایی تازه کار |
| 8 | `price` | 1 | 2274 | Price oracles on Solana → اوراکلای قیمت در سولانا ／ 1/10oz gold price at LCS → قیمت طلا ۱/۱۰ اونس در LCS |
| 9 | `for` | 1 | 2216 | Decent find for 50¢! → پیدا کردن مناسب برای ۵۰ ¢! ／ Mining for ebay gold → استخراج طلا ebay |
| 10 | `s` | 1 | 2183 | Wondering it’s worth → تعجب که ارزشش را دارد ／ Let’s see your booty! → بیایید غنیمت را ببینیم! |
| 11 | `a` | 1 | 1948 | Found a broken chain → یک زنجیر شکسته پیدا کرد ／ Is this a decent deal? → آیا این معامله مناسبی است؟ |
| 12 | `on` | 1 | 1906 | Be on the lookout!!! → مواظب باشید!!! ／ Price oracles on Solana → اوراکلای قیمت در سولانا |
| 13 | `crypto` | 1 | 1886 | My crypto got stollen → رمز ارز من به سرقت رفت ／ Daily Crypto Discussion → بحث رمزنگاری روزانه |
| 14 | `of` | 1 | 1783 | First 10oz of silver → ۱۰ اونس نقره اول ／ In The Blink Of An Eye → در یک چشم به هم زدن |
| 15 | `is` | 1 | 1590 | Why is XRP rallying? → چرا XRP رالی است؟ ／ Why Is XRP Up Today? → چرا XRP امروز بالا است؟ |
| 16 | `market` | 1 | 1481 | This market ruined me → این بازار مرا خراب کرد ／ Sunset Market Commentary → تفسیر بازار غروب |
| 17 | `oil` | 1 | 1323 | Big Oil’s day in court → روز بزرگ نفت در دادگاه ／ Oil Prices Climb Higher → افزایش قیمت نفت |
| 18 | `xrp` | 1 | 1139 | Why is XRP rallying? → چرا XRP رالی است؟ ／ Why Is XRP Up Today? → چرا XRP امروز بالا است؟ |
| 19 | `with` | 1 | 1024 | With The Fed Behind Us… → با فدرال رزرو پشت سر ما… ／ Silver with black diamonds → نقره با الماس سیاه |
| 20 | `us` | 1 | 1004 | With The Fed Behind Us… → با فدرال رزرو پشت سر ما… ／ US Treasury yields soar → بازدهی خزانه داری آمریکا افزایش یافت |
| 21 | `at` | 1 | 981 | Nepotism at Berkshire → خویشاوندی در برکشایر ／ GOLD AT SPOT on APMEX!! → طلا در نقطه در APMEX!! |
| 22 | `ethereum` | 1 | 974 | Ethereum and Bitcoin → اتریوم و بیت کوین ／ Ethereum’s Summer Movements → حرکات تابستانی اتریوم |
| 23 | `after` | 1 | 898 | After all, why not just blame Reddit → پس از همه، چرا فقط Reddit را سرزنش نکنید ／ US stocks retreat after record closes → سهام ایالات متحده پس از بسته شدن رکورد عقب نشینی کرد |
| 24 | `prediction` | 1 | 841 | XRP Price Prediction For September 24 → پیش بینی قیمت XRP برای ۲۴ سپتامبر ／ XRP Price Prediction For September 21-27 → پیش بینی قیمت XRP برای ۲۱-۲۷ سپتامبر |
| 25 | `says` | 1 | 828 | French stock market says 'au revoir' → بازار سهام فرانسه می گوید "au revoir" ／ New River Report Says $840,000 Bitcoin → گزارش New River می گوید بیت کوین ۸۴۰۰۰۰ دلار است |
| 26 | `stock` | 1 | 762 | Started my stock this month → سهام من را در این ماه شروع کردم ／ Meta Stock Is Still Too Cheap → سهام متا هنوز خیلی ارزان است |
| 27 | `fed` | 1 | 750 | With The Fed Behind Us… → با فدرال رزرو پشت سر ما… ／ The Fed Created Zohran Mamdani → فدرال رزرو زهران ممدانی را ایجاد کرد |
| 28 | `what` | 1 | 736 | We Eat What We Like! → ما آنچه دوست داریم می خوریم! ／ Damn what it could have been → لعنت به چیزی که میتونست باشه |
| 29 | `rate` | 1 | 733 | RBI rate hike pulls markets lower → افزایش نرخ بهره RBI بازارها را پایین می آورد ／ India Signals More Rate Hikes Ahead → هند سیگنال های افزایش نرخ بیشتر در پیش است |
| 30 | `etf` | 1 | 730 | AQE Core ETF declares $0.0544 dividend → AQE Core ETF ۰.۰۵۴۴ دلار سود سهام اعلام می کند ／ TDAQ Lift ETF declares $0.0866 dividend → TDAQ Lift ETF ۰.۰۸۶۶ دلار سود سهام اعلام می کند |
| 31 | `ai` | 1 | 713 | AI Garden is coming to Solana → باغ هوش مصنوعی به سولانا می آید ／ AI bubble and gold investment → حباب هوش مصنوعی و سرمایه گذاری طلا |
| 32 | `prices` | 1 | 696 | Oil Prices Climb Higher → افزایش قیمت نفت ／ Oil Prices Tumble Again → قیمت نفت دوباره سقوط کرد |
| 33 | `solana` | 1 | 687 | Price oracles on Solana → اوراکلای قیمت در سولانا ／ AI Garden is coming to Solana → باغ هوش مصنوعی به سولانا می آید |
| 34 | `silver` | 1 | 676 | First 10oz of silver → ۱۰ اونس نقره اول ／ Silver bars reduction → کاهش میله های نقره |
| 35 | `from` | 1 | 639 | cool trade up from investor crate → تجارت سرد از صندوق سرمایه گذار ／ 1912 Sovereign from the Perth mint → ۱۹۱۲ حاکم از ضرابخانه پرث |
| 36 | `stocks` | 1 | 631 | Best Oil Stocks Right Now → بهترین سهام نفت در حال حاضر ／ Best Gold Stocks Right Now → بهترین سهام طلا در حال حاضر |
| 37 | `why` | 1 | 621 | Why is XRP rallying? → چرا XRP رالی است؟ ／ Why Is XRP Up Today? → چرا XRP امروز بالا است؟ |
| 38 | `btc` | 1 | 611 | Sold my car to buy btc → ماشینم را برای خرید btc فروختم ／ Buying BTC peer-to-peer → خرید BTC نظیر به نظیر |
| 39 | `this` | 1 | 593 | This market ruined me → این بازار مرا خراب کرد ／ This time is different → این بار متفاوت است |
| 40 | `price prediction` | 2 | 592 | XRP Price Prediction For September 24 → پیش بینی قیمت XRP برای ۲۴ سپتامبر ／ XRP Price Prediction For September 21-27 → پیش بینی قیمت XRP برای ۲۱-۲۷ سپتامبر |
| 41 | `million` | 1 | 591 | Bitwise Buys Over $19 Million of XRP → Bitwise بیش از ۱۹ میلیون دلار XRP خریداری می کند ／ Samsung Brings Solana to 82 Million Phones → سامسونگ سولانا را به ۸۲ میلیون گوشی می آورد |
| 42 | `yields` | 1 | 589 | US Treasury yields soar → بازدهی خزانه داری آمریکا افزایش یافت ／ Treasury Yields Little Changed → بازدهی خزانه داری کمی تغییر کرده است |
| 43 | `it` | 1 | 572 | Wondering it’s worth → تعجب که ارزشش را دارد ／ Is this coin worth it? → آیا این سکه ارزشش را دارد؟ |
| 44 | `could` | 1 | 565 | Damn what it could have been → لعنت به چیزی که میتونست باشه ／ Could Buying XRP Today Set You Up for Life? → آیا خرید XRP امروز می تواند شما را برای زندگی آماده کن… |
| 45 | `inflation` | 1 | 560 | Inflation not just Fed’s problem → تورم فقط مشکل فدرال رزرو نیست ／ What is driving Singapore inflation? → چه چیزی باعث تورم سنگاپور می شود؟ |
| 46 | `new` | 1 | 552 | New colorized friend → دوست رنگی جدید ／ New Custom Name Piece → قطعه نام سفارشی جدید |
| 47 | `its` | 1 | 545 | How Crypto Blew Its Big Moment → چگونه Crypto لحظه بزرگ خود را منفجر کرد ／ Is XRP poised to extend its uptrend? → آیا XRP آماده است که روند صعودی خود را گسترش دهد؟ |
| 48 | `up` | 1 | 545 | Why Is XRP Up Today? → چرا XRP امروز بالا است؟ ／ Why Is XRP Up Today? → چرا XRP امروز بالا است؟ |
| 49 | `today` | 1 | 543 | Why Is XRP Up Today? → چرا XRP امروز بالا است؟ ／ Why Is XRP Up Today? → چرا XRP امروز بالا است؟ |
| 50 | `by` | 1 | 539 | [ Removed by Reddit ] → [حذف شده توسط Reddit] ／ [ Removed by Reddit ] → [حذف شده توسط Reddit] |
| 51 | `over` | 1 | 511 | Up to a smidge over 17oz → تا ضخامت بیش از ۱۷ اونس ／ Those folks over at MintBuilder... → کسانی که در MintBuilder هستند... |
| 52 | `can` | 1 | 504 | Can I be the only one? → آیا می توانم تنها باشم؟ ／ How can I get dogecoin → چگونه می توانم dogecoin دریافت کنم |
| 53 | `are` | 1 | 497 | Are these real gold? → آیا اینها طلای واقعی هستند؟ ／ Are we heading to 82k again? → آیا دوباره به سمت ۸۲k می رویم؟ |
| 54 | `but` | 1 | 485 | Crypto Pulls Back, but Greed Lingers → کریپتو عقب می نشیند، اما طمع به تعویق می افتد ／ I like the boggle head approach — but, → من رویکرد کاوشگر را دوست دارم - اما، |
| 55 | `october` | 1 | 454 | Daily Discussion, October 03, 2026 → بحث روزانه، ۰۳ اکتبر ۲۰۲۶ ／ Daily Discussion, October 04, 2026 → بحث روزانه، ۰۴ اکتبر ۲۰۲۶ |
| 56 | `dollar` | 1 | 452 | 1913 Indian head $10 dollar → ۱۰ دلار سر هندی ۱۹۱۳ ／ Strong dollar pulls gold down → دلار قوی طلا را پایین می آورد |
| 57 | `hike` | 1 | 446 | Fed Hike Adds to Dollar Momentum → افزایش فدرال رزرو به شتاب دلار می افزاید ／ RBI rate hike pulls markets lower → افزایش نرخ بهره RBI بازارها را پایین می آورد |
| 58 | `bank` | 1 | 428 | Got something cool at the bank → یه چیز جالب تو بانک گرفتم ／ Fintech Wants the Keys to the Bank → فین‌تک کلیدهای بانک را می‌خواهد |
| 59 | `high` | 1 | 428 | How High Can Solana Price Go? → قیمت سولانا چقدر می تواند بالا رود؟ ／ How High Can Solana Price Go? → قیمت سولانا چقدر می تواند بالا رود؟ |
| 60 | `rally` | 1 | 428 | Has the Bitcoin Rally Fizzled Out? → آیا رالی بیت کوین از بین رفته است؟ ／ Weekly Wrap: The Crypto Rally Continues → بسته بندی هفتگی: رالی کریپتو ادامه دارد |
| 61 | `will` | 1 | 418 | Will XRP Hit $4 By 2028? → آیا XRP تا سال ۲۰۲۸ به ۴ دلار خواهد رسید؟ ／ Where Will Ethereum Be in 2030? → اتریوم در سال ۲۰۳۰ کجا خواهد بود؟ |
| 62 | `markets` | 1 | 407 | RBI rate hike pulls markets lower → افزایش نرخ بهره RBI بازارها را پایین می آورد ／ Stock Markets Hit New All Time Highs → بازارهای سهام به رکوردهای جدید در تمام دوران رسیدند |
| 63 | `hits` | 1 | 403 | Posting until DOGE hits $1 - day 148 → ارسال تا زمانی که DOGE به ۱ دلار برسد - روز ۱۴۸ ／ Posting until DOGE hits $1 - day 149 → ارسال تا زمانی که DOGE به ۱ دلار برسد - روز ۱۴۹ |
| 64 | `eth` | 1 | 399 | Skipped the ETH cycle → از چرخه ETH رد شد ／ Ethereum News: ETH Breaks Above $2,750 → اخبار اتریوم: ETH به بالای ۲۷۵۰ دلار می‌رسد |
| 65 | `next` | 1 | 399 | Hunt for the next 10x? → ۱۰ برابر بعدی را شکار کنید؟ ／ Hunt for the next 10x? → ۱۰ برابر بعدی را شکار کنید؟ |
| 66 | `treasury` | 1 | 391 | US Treasury yields soar → بازدهی خزانه داری آمریکا افزایش یافت ／ Treasury Yields Little Changed → بازدهی خزانه داری کمی تغییر کرده است |
| 67 | `near` | 1 | 390 | BMNR's near future potential. JMHO → پتانسیل آینده نزدیک BMNR JMHO ／ Bitwise Teases NEAR ETF Launch for Today → Bitwise Teases NEAR ETF برای امروز راه اندازی شد |
| 68 | `more` | 1 | 389 | Now I just need like 10 more → الان فقط ۱۰ تا دیگه نیاز دارم ／ One of my more interesting pieces → یکی از کارهای جالب تر من |
| 69 | `week` | 1 | 386 | Economics Week Ahead → هفته اقتصاد در پیش است ／ BTC Market Pulse: Week 39 → نبض بازار بیت کوین: هفته ۳۹ |
| 70 | `amid` | 1 | 380 | LandBridge Vaults 75% Amid Oil Supply Shock → خزانه های LandBridge ۷۵% در میان شوک عرضه نفت ／ Şimşek pledges liquidity support amid fund p… → شیمشک در بحبوحه تحقیقات صندوق متعهد به حمایت نقدینگی شد |
| 71 | `hit` | 1 | 377 | bitcoin to hit $300k → بیت کوین به ۳۰۰ هزار دلار رسید ／ Will XRP Hit $4 By 2028? → آیا XRP تا سال ۲۰۲۸ به ۴ دلار خواهد رسید؟ |
| 72 | `news` | 1 | 376 | Cardano (ADA) news today - newsbtc.com → اخبار کاردانو (ADA) امروز - newsbtc.com ／ Ethereum News: ETH Breaks Above $2,750 → اخبار اتریوم: ETH به بالای ۲۷۵۰ دلار می‌رسد |
| 73 | `billion` | 1 | 373 | XRP adds $7 billion in a day; Is $2 next? → XRP ۷ میلیارد دلار در روز اضافه می کند. آیا ۲ دلار بعد… ／ XRP Reclaims Massive $100 Billion Market Cap → XRP ارزش بازار عظیم ۱۰۰ میلیارد دلاری را پس می گیرد |
| 74 | `september` | 1 | 361 | Payments Roundup: September 2026 → جمع بندی پرداخت ها: سپتامبر ۲۰۲۶ ／ XRP Price on September 21, 4PM UTC → قیمت XRP در ۲۱ سپتامبر، ساعت ۱۶ UTC |
| 75 | `forecast` | 1 | 352 | Cardano Price Forecast: What's next for ADA? → پیش بینی قیمت Cardano: آینده ADA چیست؟ ／ XRP Price Forecast as We Approach October 1,… → پیش بینی قیمت XRP با نزدیک شدن به ۱ اکتبر ۲۰۲۶ |
| 76 | `trading` | 1 | 352 | is gmgn a good trading app? → آیا gmgn یک برنامه تجاری خوب است؟ ／ Best coin combo for trading? → بهترین ترکیب سکه برای تجارت؟ |
| 77 | `record` | 1 | 339 | US stocks retreat after record closes → سهام ایالات متحده پس از بسته شدن رکورد عقب نشینی کرد ／ Is SpaceX Stock a Buy at a Record High? → آیا سهام SpaceX خریدی با رکورد بالا است؟ |
| 78 | `etfs` | 1 | 335 | Solana Spot ETFs See $3.6849M Net Outflows → ETF های نقطه ای Solana به خروجی خالص ۳.۶۸۴۹ میلیون دلا… ／ Bitcoin ETFs have erased a $5.8 billion hole → ETF های بیت کوین حفره ۵.۸ میلیارد دلاری را پاک کرده اند |
| 79 | `investors` | 1 | 327 | These Money Illusions Can Cost Investors Dea… → این توهمات پولی می تواند هزینه گزافی برای سرمایه گذارا… ／ Ondo lets investors trade pre-IPO exposure 2… → Ondo به سرمایه گذاران این امکان را می دهد که قرار گرفت… |
| 80 | `below` | 1 | 326 | Brent Price Slips Below $100 → قیمت برنت به زیر ۱۰۰ دلار رسید ／ Saudi Export Pivot Sends Brent Below $105 → محور صادرات عربستان، برنت را به زیر ۱۰۵ دلار می‌فرستد |
| 81 | `buy` | 1 | 323 | Should I buy DigiByte → آیا باید دیجی بایت بخرم؟ ／ Sold my car to buy btc → ماشینم را برای خرید btc فروختم |
| 82 | `how` | 1 | 323 | How much M5 costed you → M۵ چقدر برای شما هزینه کرد ／ How can I get dogecoin → چگونه می توانم dogecoin دریافت کنم |
| 83 | `bond` | 1 | 320 | Bond sell-off deepens as oil price rises → با افزایش قیمت نفت، فروش اوراق قرضه عمیق تر می شود ／ Higher Bond Yields Mark a Return to Normal → بازده اوراق قرضه بالاتر بازگشت به حالت عادی را نشان می… |
| 84 | `data` | 1 | 313 | Interesting U.S Trends Data on Silver → داده های جالب روند ایالات متحده در مورد نقره ／ September inflation data due this week → آمار تورم سپتامبر در این هفته منتشر می شود |
| 85 | `first` | 1 | 312 | First 10oz of silver → ۱۰ اونس نقره اول ／ My first ancient coin. → اولین سکه باستانی من |
| 86 | `stock market` | 2 | 310 | French stock market says 'au revoir' → بازار سهام فرانسه می گوید "au revoir" ／ Stock Market Today (Oct. 5, 2026): (Futures) → بورس امروز (۵ اکتبر ۲۰۲۶): (آینده) |
| 87 | `tokenized` | 1 | 310 | Base Unveils 26 New Tokenized Stocks → شرکت Base از ۲۶ سهام جدید توکن شده رونمایی کرد ／ Anyone actually arb’ing tokenized stocks? → آیا کسی واقعاً سهام توکنیزه شده را جذب می کند؟ |
| 88 | `be` | 1 | 308 | Be on the lookout!!! → مواظب باشید!!! ／ Can I be the only one? → آیا می توانم تنها باشم؟ |
| 89 | `global` | 1 | 307 | Global Selloff in Bonds Intensifies → فروش جهانی اوراق قرضه تشدید می شود ／ Crude oil futures fall on weak global cues → قیمت آتی نفت خام بر اساس نشانه های ضعیف جهانی سقوط می … |
| 90 | `ahead` | 1 | 306 | Economics Week Ahead → هفته اقتصاد در پیش است ／ India Signals More Rate Hikes Ahead → هند سیگنال های افزایش نرخ بیشتر در پیش است |
| 91 | `rise` | 1 | 305 | Silver prices rise positively → قیمت نقره مثبت شد ／ Stocks Decline as Treasury Yields Rise → با افزایش بازدهی خزانه داری، سهام کاهش می یابد |
| 92 | `trump` | 1 | 302 | Trump to Meet Ukraine's Zelenskyy → ترامپ با زلنسکی اوکراینی دیدار می کند ／ The battle between the Fed and Trump → نبرد بین فدرال رزرو و ترامپ |
| 93 | `above` | 1 | 300 | XRP Price Climbed Above $1.40 → قیمت XRP به بالای ۱.۴۰ دلار رسید ／ Ethereum News: ETH Breaks Above $2,750 → اخبار اتریوم: ETH به بالای ۲۷۵۰ دلار می‌رسد |
| 94 | `just` | 1 | 299 | Key date or just bullion? → تاریخ کلیدی یا فقط شمش؟ ／ my wallet just got drained → کیف من به تازگی خالی شده است |
| 95 | `nifty` | 1 | 299 | Flat opening seen for Nifty, Sensex → دهانه صاف برای Nifty، Sensex دیده می شود ／ Nifty slips below 23,000 as bank stocks tumb… → با سقوط سهام بانکی، Nifty به زیر ۲۳۰۰۰ سقوط کرد |
| 96 | `binance` | 1 | 296 | Binance to Delist 22 Tokens in Brazil → بایننس به حذف ۲۲ توکن در برزیل ／ Binance Lists Two New Cryptocurrencies → بایننس دو ارز دیجیتال جدید را فهرست کرده است |
| 97 | `now` | 1 | 291 | Many bears right now: → خرس های زیادی در حال حاضر: ／ How is bro doing now? 😭 → داداش الان چطوره؟ 😭 |
| 98 | `wall` | 1 | 290 | Wall Street’s great money spinner → پول‌گردان بزرگ وال استریت ／ Print Edition \| Wall Street Journal → نسخه چاپی \| وال استریت ژورنال |
| 99 | `gains` | 1 | 287 | Gold Futures Slip As U.S. Dollar Gains → معاملات آتی طلا با افزایش ارزش دلار آمریکا کاهش می یابد ／ This XRP Price Zone Delivered 500% Gains Once → این منطقه قیمت XRP یک بار ۵۰۰٪ سود تحویل می دهد |
| 100 | `rate hike` | 2 | 287 | RBI rate hike pulls markets lower → افزایش نرخ بهره RBI بازارها را پایین می آورد ／ Fed Issues First Rate Hike Since 2023 → فدرال رزرو برای اولین بار نرخ بهره را از سال ۲۰۲۳ افزا… |
| 101 | `cardano` | 1 | 285 | Cardano Climbs 10% In a Green Day → کاردانو ۱۰ درصد در یک روز سبز صعود می کند ／ Cardano Climbs 10% In Bullish Trade → کاردانو ۱۰ درصد در معاملات صعودی صعود کرد |
| 102 | `bitcoin price` | 2 | 280 | What's Happening With Bitcoin Price? → با قیمت بیت کوین چه اتفاقی می افتد؟ ／ Why Is the Bitcoin Price Soaring Again? → چرا قیمت بیت کوین دوباره افزایش می یابد؟ |
| 103 | `key` | 1 | 280 | Key date or just bullion? → تاریخ کلیدی یا فقط شمش؟ ／ The Address is not the Public Key → آدرس کلید عمومی نیست |
| 104 | `futures` | 1 | 277 | Gold, Silver Futures Settle Higher → آتی طلا و نقره بالاتر می رود ／ Gold Futures Slip As U.S. Dollar Gains → معاملات آتی طلا با افزایش ارزش دلار آمریکا کاهش می یابد |
| 105 | `higher` | 1 | 275 | Oil Prices Climb Higher → افزایش قیمت نفت ／ Oil's New Normal Is Higher Prices → قیمت های معمولی جدید نفت بالاتر است |
| 106 | `that` | 1 | 273 | I love that coinstar machines hate Silver → من عاشق این هستم که ماشین های کوین استار از نقره متنفر… ／ What is your story of the one that got away? → داستانت از اونی که فرار کرد چیه؟ |
| 107 | `street` | 1 | 270 | Wall Street’s great money spinner → پول‌گردان بزرگ وال استریت ／ Print Edition \| Wall Street Journal → نسخه چاپی \| وال استریت ژورنال |
| 108 | `stablecoin` | 1 | 268 | Defi stablecoin platforms → پلتفرم های استیبل کوین را تعریف کنید ／ Changer+ Launches Self-Hosted Stablecoin Wal… → Changer+ کیف پول استیبل کوین خود میزبان را راه اندازی … |
| 109 | `ripple` | 1 | 267 | Ripple Adds XRP Payments To Stripe → Ripple پرداخت های XRP را به Stripe اضافه می کند ／ XRP News: Seoul Event Shows Ripple Reach → اخبار XRP: رویداد سئول ریپل ریچ را نشان می دهد |
| 110 | `dogecoin` | 1 | 266 | How can I get dogecoin → چگونه می توانم dogecoin دریافت کنم ／ Where is Dogecoin heading? → Dogecoin به کجا می رود؟ |
| 111 | `rates` | 1 | 265 | Federal Reserve raises interest rates → فدرال رزرو نرخ بهره را افزایش می دهد ／ Supertanker Rates Slip From Record Highs → نرخ سوپرتانکر از بالاترین رکورد سقوط کرد |
| 112 | `back` | 1 | 263 | The Royal Mint , sell back → ضرابخانه سلطنتی، فروش مجدد ／ CryptoPunks Are Heating Back Up → CryptoPunks در حال گرم شدن هستند |
| 113 | `has` | 1 | 263 | Has the Bitcoin Rally Fizzled Out? → آیا رالی بیت کوین از بین رفته است؟ ／ The War on High Oil Prices has Many Fronts → جنگ بر سر قیمت های بالای نفت جبهه های زیادی دارد |
| 114 | `launches` | 1 | 260 | DeFi Technologies’ Valour Launches Zcash ETP → Valor شرکت DeFi Technologies Zcash ETP را راه اندازی ک… ／ How to Snipe New Memecoin Launches (Tutorial) → نحوه Snipe کردن راه اندازی Memecoin جدید (آموزش) |
| 115 | `price forecast` | 2 | 256 | Cardano Price Forecast: What's next for ADA? → پیش بینی قیمت Cardano: آینده ADA چیست؟ ／ XRP Price Forecast as We Approach October 1,… → پیش بینی قیمت XRP با نزدیک شدن به ۱ اکتبر ۲۰۲۶ |
| 116 | `down` | 1 | 254 | It goes up it goes down → بالا می رود پایین می آید ／ Strong dollar pulls gold down → دلار قوی طلا را پایین می آورد |
| 117 | `into` | 1 | 254 | Ran into a new "problem" → به یک "مشکل" جدید برخورد کرد ／ Good time to get into Doge? → زمان خوبی برای ورود به Doge است؟ |
| 118 | `nasdaq` | 1 | 252 | XRP Treasury Giant Delays Nasdaq Debut → غول خزانه داری XRP معرفی نزدک را به تاخیر انداخت ／ COMMENTARY: Trading Day: Oil slips, Nasdaq r… → تفسیر: روز معامله: نفت لغزش، ریزش نزدک |
| 119 | `coinbase` | 1 | 251 | Coinbase Wallet Extension → افزونه کیف پول کوین بیس ／ IOTA Rival Dropped by Coinbase → رقیب IOTA توسط Coinbase حذف شد |
| 120 | `fall` | 1 | 251 | Gilt Yields Fall After Oil Prices Drop → کاهش بازده طلا پس از کاهش قیمت نفت ／ Meta leads tech rally as oil prices fall → متا با کاهش قیمت نفت پیشتاز رشد فناوری است |
| 121 | `since` | 1 | 251 | Stacking since August → انباشته شدن از اوت ／ First gold purchase since… → اولین خرید طلا از زمان… |
| 122 | `falls` | 1 | 250 | Treasury Yields Decline as Oil Falls → با سقوط نفت، بازدهی خزانه داری کاهش می یابد ／ European Indexes Higher as Oil Falls Back → با کاهش قیمت نفت، شاخص های اروپا بالاتر می رود |
| 123 | `iran` | 1 | 247 | Iran Talks Take the Heat Out of the Oil Rally → مذاکرات ایران گرمای رالی نفت را از بین می برد ／ The Iran energy shock is wrongfooting the wo… → شوک انرژی ایران جهان را نادرست کرده است |
| 124 | `inflows` | 1 | 246 | Bitcoin Holds Above $81K as ETF Inflows Retu… → بیت کوین به عنوان بازده ورودی ETF بالای ۸۱ هزار دلار ا… ／ XRP Whale Inflows to Binance Hit Six-Month H… → ورود نهنگ XRP به بایننس به بالاترین حد شش ماهه رسید |
| 125 | `u.s.` | 1 | 246 | Gold Futures Slip As U.S. Dollar Gains → معاملات آتی طلا با افزایش ارزش دلار آمریکا کاهش می یابد ／ U.S. Treasury Yields Ease; Dollar Stable → تسهیل بازدهی خزانه داری ایالات متحده؛ استیبل دلار |
| 126 | `holds` | 1 | 245 | Bitcoin Holds Above $81K as ETF Inflows Retu… → بیت کوین به عنوان بازده ورودی ETF بالای ۸۱ هزار دلار ا… ／ Gold Holds Near US$4,344, Rate Hike Bets Ret… → طلا نزدیک به ۴,۳۴۴ دلار آمریکا باقی می ماند، شرط های ا… |
| 127 | `outlook` | 1 | 242 | EUR/USD Daily Outlook → چشم انداز روزانه EUR/USD ／ EUR/USD Daily Outlook → چشم انداز روزانه EUR/USD |
| 128 | `s&p` | 1 | 241 | S&P 500's Newest Member Is Monday's Biggest … → جدیدترین عضو S&P ۵۰۰ بزرگترین بازنده دوشنبه است ／ S&P 500 at 10,000? AI Boom Keeps Earnings Su… → S&P ۵۰۰ در ۱۰۰۰۰؟ AI Boom درآمد را افزایش می دهد |
| 129 | `surge` | 1 | 241 | CFX Climbs Past $0.066 With 10.31% Surge → CFX با افزایش ۱۰.۳۱ درصدی از ۰.۰۶۶ دلار گذشت ／ Institutional Surge in Crypto Investments → جهش نهادی در سرمایه گذاری های رمزنگاری |
| 130 | `risk` | 1 | 236 | The biggest risk for Bitcoin → بزرگترین خطر برای بیت کوین ／ S&P Brings Traditional Risk Ratings to DeFi … → S&P رتبه بندی ریسک سنتی را به DeFi Vaults می آورد |
| 131 | `xrp price` | 2 | 235 | XRP Price Climbed Above $1.40 → قیمت XRP به بالای ۱.۴۰ دلار رسید ／ XRP Price on September 21, 4PM UTC → قیمت XRP در ۲۱ سپتامبر، ساعت ۱۶ UTC |
| 132 | `despite` | 1 | 234 | Bitcoin Sentiment Warms Despite Softer Price → احساسات بیت کوین با وجود قیمت پایین تر گرم می شود ／ IT stocks surge despite US immigration curbs → با وجود محدودیت‌های مهاجرتی ایالات متحده، سهام فناوری … |
| 133 | `wall street` | 2 | 231 | Wall Street’s great money spinner → پول‌گردان بزرگ وال استریت ／ Print Edition \| Wall Street Journal → نسخه چاپی \| وال استریت ژورنال |
| 134 | `oil prices` | 2 | 225 | Oil Prices Climb Higher → افزایش قیمت نفت ／ Oil Prices Tumble Again → قیمت نفت دوباره سقوط کرد |
| 135 | `sensex` | 1 | 225 | Flat opening seen for Nifty, Sensex → دهانه صاف برای Nifty، Sensex دیده می شود ／ Sensex, Nifty plunge over 1%; realty shares … → Sensex، Nifty plunge بیش از ۱%; سهام املاک لغزش |
| 136 | `top` | 1 | 224 | Top 12 NFT games of September 2026 → ۱۲ بازی برتر NFT سپتامبر ۲۰۲۶ ／ Top des communautés crypto en 2026 → Top des communautés crypto en ۲۰۲۶ |
| 137 | `ethereum price` | 2 | 221 | Will Ethereum Price Reach $3,000 in October? → آیا قیمت اتریوم در ماه اکتبر به ۳۰۰۰ دلار خواهد رسید؟ ／ Ethereum Price Prediction: ETH Falls to $2,5… → پیش بینی قیمت اتریوم: ETH به ۲۵۰۰ دلار سقوط می کند |
| 138 | `demand` | 1 | 220 | Higher Rates Beginning to Weigh on Demand → نرخ های بالاتر شروع به وزن گیری بر اساس تقاضا ／ AI boom fails to lift gold demand, WGC says → WGC می گوید رونق هوش مصنوعی نتوانست تقاضای طلا را افزا… |
| 139 | `interest` | 1 | 220 | UK observation, metals interest → مشاهده بریتانیا، علاقه فلزات ／ Federal Reserve raises interest rates → فدرال رزرو نرخ بهره را افزایش می دهد |
| 140 | `you` | 1 | 220 | How much M5 costed you → M۵ چقدر برای شما هزینه کرد ／ How much would you pay? → چقدر پرداخت می کنید؟ |
| 141 | `strategy` | 1 | 219 | Why Strategy Stock Surged Today → چرا سهام استراتژی امروز افزایش یافت؟ ／ Saylor Posts Sunday Strategy Bitcoin Tease → سایلر یکشنبه استراتژی بیت کوین را منتشر می کند |
| 142 | `may` | 1 | 218 | Talent crunch may hamper Sebi’s PMS revamp → تنگنای استعدادها ممکن است مانع از اصلاح PMS در Sebi شود ／ Novogratz Says Bitcoin May End 2026 Near $10… → نووگراتز می گوید بیت کوین ممکن است در سال ۲۰۲۶ نزدیک ب… |
| 143 | `central` | 1 | 217 | India's Central Bank Hikes Repo Rate by 25 B… → بانک مرکزی هند نرخ رپو را ۲۵ Bps افزایش داد ／ Sunface Gold! - Central American Republic Es… → Sunface Gold! - اسکودو جمهوری آمریکای مرکزی |
| 144 | `one` | 1 | 217 | Can I be the only one? → آیا می توانم تنها باشم؟ ／ Massive Silver Haul (One Day) → حجم عظیم نقره ای (یک روز) |
| 145 | `traders` | 1 | 216 | Robinhood plans 10x crypto perps for U.S. tr… → Robinhood ۱۰ برابر سود رمزنگاری برای معامله گران ایالا… ／ Hong Kong Traders Are Borrowing Like Never B… → معامله گران هنگ کنگ مانند گذشته قرض می گیرند |
| 146 | `bets` | 1 | 214 | Gold slips on Fed policy tightening bets → طلا در شرط بندی های سختگیرانه فدرال رزرو سقوط می کند ／ Gold drops more than 2% on US rate-hike bets → طلا در شرط‌بندی‌های افزایش نرخ در آمریکا بیش از ۲ درصد… |
| 147 | `live` | 1 | 214 | PEPE Is Live On Solana Via Sunrise → PEPE از طریق Sunrise در Solana پخش می شود ／ Made a free live crypto volatility scanner. → یک اسکنر زنده رایگان نوسانات کریپتو ساخته شده است. |
| 148 | `an` | 1 | 213 | In The Blink Of An Eye → در یک چشم به هم زدن ／ Do you have an end goal? → آیا هدف نهایی دارید؟ |
| 149 | `as oil` | 2 | 213 | Treasury Yields Decline as Oil Falls → با سقوط نفت، بازدهی خزانه داری کاهش می یابد ／ Bitcoin and Stocks Recover as Oil Eases → بیت کوین و سهام با کاهش قیمت نفت بهبود می یابند |
| 150 | `i` | 1 | 212 | Should I buy DigiByte → آیا باید دیجی بایت بخرم؟ ／ Can I be the only one? → آیا می توانم تنها باشم؟ |
| 151 | `here` | 1 | 211 | Moon season is here 🌙 → فصل ماه اینجاست🌙 ／ Here come the goofies → در اینجا احمق ها می آیند |
| 152 | `ahead of` | 2 | 206 | XRP Price Ahead of Trump Announcement Today → قیمت XRP در آستانه اعلام امروز ترامپ ／ FPIs pare bank Nifty shorts ahead of RBI pol… → FPI ها شورت های بانک Nifty را قبل از سیاست RBI کاهش می… |
| 153 | `rbi` | 1 | 206 | Rupee Jumps on RBI Measures → روپیه بر روی اقدامات RBI می پرد ／ RBI rate hike pulls markets lower → افزایش نرخ بهره RBI بازارها را پایین می آورد |
| 154 | `rises` | 1 | 206 | Ethereum Rises 7.3% -- Crypto Mover → افزایش ۷.۳ درصدی اتریوم -- Crypto Mover ／ WSJ Dollar Index Rises 0.09% to 96.19 → شاخص دلار WSJ با ۰.۰۹ درصد افزایش به ۹۶.۱۹ رسید |
| 155 | `or` | 1 | 205 | pengu coin dead or naa? → سکه پنگو مرده یا نه؟ ／ Key date or just bullion? → تاریخ کلیدی یا فقط شمش؟ |
| 156 | `report` | 1 | 204 | AUD/USD Daily Report → گزارش روزانه AUD/USD ／ AUD/USD Daily Report → گزارش روزانه AUD/USD |
| 157 | `targets` | 1 | 202 | Solana News: DvP Targets Atomic Settlement → سولانا نیوز: DvP حل و فصل اتمی را هدف قرار می دهد ／ The Fed Rate Hike Won’t Fix The Inflation It… → افزایش نرخ بهره فدرال رزرو تورم مورد نظر را برطرف نمی … |
| 158 | `about` | 1 | 201 | My story about buying fakes → داستان من در مورد خرید تقلبی ／ I'm all about the Benjamin's → من در مورد بنیامین هستم |
| 159 | `still` | 1 | 201 | Are u still waiting for 40k? → آیا هنوز منتظر ۴۰ هزار هستید؟ ／ Meta Stock Is Still Too Cheap → سهام متا هنوز خیلی ارزان است |
| 160 | `support` | 1 | 201 | Gold Rises as Strong Fundamentals Support → طلا با حمایت بنیادی قوی افزایش یافت ／ Bybit Launches USD Deposit Support via OpenP… → Bybit پشتیبانی سپرده دلاری را از طریق OpenPayd راه اند… |
| 161 | `sec` | 1 | 200 | SEC Approval Expands Leveraged ETP Menu → تأیید SEC منوی اهرمی ETP را گسترش می‌دهد ／ SEC Clarifies New Rules For Staked Ethereum → SEC قوانین جدیدی را برای Staked Ethereum روشن می کند |
| 162 | `trade` | 1 | 200 | Best copy trade memecoin bot? → بهترین ربات memecoin تجارت کپی؟ ／ cool trade up from investor crate → تجارت سرد از صندوق سرمایه گذار |
| 163 | `ada` | 1 | 199 | Cardano (ADA) news today - newsbtc.com → اخبار کاردانو (ADA) امروز - newsbtc.com ／ Where Will Cardano (ADA) Be in 3 Years? → کاردانو (ADA) ۳ سال دیگر کجا خواهد بود؟ |
| 164 | `buying` | 1 | 198 | Buying Event Ripoff? → خرید رویداد Ripoff؟ ／ Buying BTC peer-to-peer → خرید BTC نظیر به نظیر |
| 165 | `gold price` | 2 | 198 | 1/10oz gold price at LCS → قیمت طلا ۱/۱۰ اونس در LCS ／ Gold ETF rush defies 8.5% gold price slide → هجوم ETF طلا با کاهش ۸.۵ درصدی قیمت طلا مخالفت می کند |
| 166 | `while` | 1 | 198 | Gold prices fall, while silver rises on glob… → قیمت طلا کاهش می یابد و نقره در بازارهای جهانی افزایش … ／ Cardano’s $20 Dream Resurfaces While CIP-011… → در حالی که CIP-۰۱۱۳ زنده می‌شود، رویای ۲۰ دلاری کاردان… |
| 167 | `low` | 1 | 197 | My RCM Collectible (Low Mint) Pickups → پیکاپ های کلکسیونی RCM من (کم نعناع). ／ Euro hits 17-month low against dollar → یورو در برابر دلار به پایین ترین حد در ۱۷ ماه گذشته رس… |
| 168 | `token` | 1 | 195 | Would you a new coin or token there? → آیا یک سکه یا توکن جدید در آنجا می خواهید؟ ／ 3 Token Unlocks to Watch in This Week → ۳ توکن برای تماشا در این هفته باز می شود |
| 169 | `not` | 1 | 192 | Inflation not just Fed’s problem → تورم فقط مشکل فدرال رزرو نیست ／ The Address is not the Public Key → آدرس کلید عمومی نیست |
| 170 | `crude` | 1 | 191 | US Crude Inventories Slide → کاهش ذخایر نفت خام ایالات متحده ／ Crude Oil Is Driving the Forex Market → نفت خام بازار فارکس را هدایت می کند |
| 171 | `mining` | 1 | 190 | Mining for ebay gold → استخراج طلا ebay ／ Who is mining Bitcoin in China? → چه کسی بیت کوین را در چین استخراج می کند؟ |
| 172 | `weekly` | 1 | 190 | AUD/USD Weekly Report → گزارش هفتگی AUD/USD ／ AUD/USD Weekly Report → گزارش هفتگی AUD/USD |
| 173 | `supply` | 1 | 187 | Trump Says Putin to Supply US With Diesel → ترامپ: پوتین به آمریکا گازوئیل می‌دهد ／ LandBridge Vaults 75% Amid Oil Supply Shock → خزانه های LandBridge ۷۵% در میان شوک عرضه نفت |
| 174 | `treasury yields` | 2 | 187 | US Treasury yields soar → بازدهی خزانه داری آمریکا افزایش یافت ／ Treasury Yields Little Changed → بازدهی خزانه داری کمی تغییر کرده است |
| 175 | `years` | 1 | 187 | Litcoin 15 Years Full Time → لیت کوین ۱۵ سال تمام وقت ／ My stack - 2 years in making → پشته من - ۲ سال در حال ساخت |
| 176 | `risks` | 1 | 186 | France: Debt Risks Are Mounting → فرانسه: خطرات بدهی در حال افزایش است ／ Nvidia turns to insurers to offset AI risks → انویدیا برای جبران خطرات هوش مصنوعی به بیمه‌گران روی م… |
| 177 | `shares` | 1 | 186 | REX Shares, Osprey Push for SEI Staked ETF → سهام REX، Osprey Push برای ETF سهامدار SEI ／ Market under pressure; PSU Bank shares drop → بازار تحت فشار؛ کاهش سهام بانک PSU |
| 178 | `year` | 1 | 186 | First silver buy for my 9 year old. → اولین خرید نقره برای کودک ۹ ساله من. ／ Spot pick up, first year of issue Morgan → دریافت نقطه ای، سال اول انتشار مورگان |
| 179 | `banks` | 1 | 185 | Banks Strengthen Institutional Trust in Cryp… → بانک‌ها اعتماد نهادی به کریپتو را تقویت می‌کنند ／ US Banks Plan Shared Blockchain Network For … → بانک های ایالات متحده شبکه بلاک چین مشترک را برای سال … |
| 180 | `before` | 1 | 185 | The funding fees are insane before pump → هزینه های بودجه قبل از پمپاژ دیوانه کننده است ／ Tesla Stock Could Hit $400 Again Before 2027 → سهام تسلا ممکن است تا قبل از سال ۲۰۲۷ دوباره به ۴۰۰ دل… |
| 181 | `gold prices` | 2 | 185 | Gold prices hit 5-week bottom → قیمت طلا به کف ۵ هفته ای رسید ／ Experts predict unexpected gold prices next … → کارشناسان قیمت غیرمنتظره طلا را در هفته آینده پیش بینی… |
| 182 | `remittix` | 1 | 184 | Cardano Price: ADA Consolidation Meets Remit… → قیمت Cardano: ADA Consolidation با پنجره مالی نهایی ۴ … ／ Solana Price Prediction Rallies on Bank News… → با چرخش معامله گران به Remittix، پیش بینی قیمت سولانا … |
| 183 | `spot` | 1 | 183 | GOLD AT SPOT on APMEX!! → طلا در نقطه در APMEX!! ／ All my LCS wants 2-4 + spot → همه LCS من ۲-۴ + نقطه می خواهد |
| 184 | `bullish` | 1 | 182 | I am bullish to .....? → من نسبت به ..... خوشبین هستم؟ ／ Reasons to be bullish on equities → دلایل صعودی بودن در سهام |
| 185 | `sol` | 1 | 181 | The easiest way to reclaim stuck SOL? → ساده ترین راه برای بازیابی SOL گیر کرده؟ ／ Personal milestone reached: 100 SOL 💪🏆 → نقطه عطف شخصی رسیده به: ۱۰۰ SOL 💪🏆 |
| 186 | `eyes` | 1 | 180 | CFTC Eyes New Crypto Market Rules → قوانین جدید بازار کریپتو CFTC Eyes ／ Kevin O'Leary returns to crypto, eyes blockc… → کوین اولری به کریپتو بازگشته و به بلاک چین چشم دوخته ا… |
| 187 | `than` | 1 | 179 | Dogecoin run is closer than you think → اجرای Dogecoin نزدیکتر از چیزی است که فکر می کنید ／ Crypto: Ethereum Fees Drop by More Than 85% → کریپتو: کارمزد اتریوم بیش از ۸۵ درصد کاهش می یابد |
| 188 | `wallet` | 1 | 179 | I opened my jade wallet → کیف پول یشم را باز کردم ／ GrapheneOS for BTC wallet → GrapheneOS برای کیف پول BTC |
| 189 | `faces` | 1 | 178 | The Australian Dollar Faces a Defining Week → دلار استرالیا هفته تعیین کننده ای را پیش رو دارد ／ Video: Mining’s next generation faces the te… → ویدئو: نسل بعدی ماینینگ با این آزمایش روبرو است |
| 190 | `out` | 1 | 178 | Has the Bitcoin Rally Fizzled Out? → آیا رالی بیت کوین از بین رفته است؟ ／ I am srs out of excuses for nocoiners. → من srs از بهانه برای nocoiners هستم. |
| 191 | `rising` | 1 | 177 | Coinbase's Martin Sees Rising Demand for Cry… → مارتین از کوین بیس شاهد افزایش تقاضا برای کریپتو است ／ Rising rates: What should your debt strategy… → افزایش نرخ ها: استراتژی بدهی شما چگونه باید باشد؟ |
| 192 | `pressure` | 1 | 176 | Market under pressure; PSU Bank shares drop → بازار تحت فشار؛ کاهش سهام بانک PSU ／ Diesel Prices Keep Pressure on Fed and Marke… → قیمت گازوئیل بر فدرال رزرو و بازارها فشار می آورد |
| 193 | `mine` | 1 | 175 | Vale takes 30% of Ligga iron ore mine in $19… → واله ۳۰ درصد از معدن سنگ آهن لیگا را در معامله ۱۹۰ میل… ／ Sigma Lithium jumps after Brazil court reope… → سیگما لیتیوم پس از بازگشایی معدن توسط دادگاه برزیل افز… |
| 194 | `sees` | 1 | 175 | Solana Sees Biggest ETF Week Since Launch → سولانا شاهد بزرگترین هفته ETF از زمان راه اندازی است ／ Zcash ETF sees $93.6M exit as ZEC drops 23% → ETF Zcash با کاهش ۲۳ درصدی ZEC شاهد خروج ۹۳.۶ میلیون د… |
| 195 | `move` | 1 | 172 | ZETA And AnumaAI Will Move To Solana → ZETA و AnumaAI به سولانا نقل مکان خواهند کرد ／ Ethereum Wallets Move 2,903 ETH to Coinbase → کیف پول اتریوم ۲۹۰۳ اتریوم را به کوین بیس منتقل می کند |
| 196 | `ceo` | 1 | 171 | Silicon Data CEO Li on AI Race and Tokenomics → مدیر عامل شرکت داده سیلیکون لی در زمینه هوش مصنوعی Rac… ／ Qantas CEO Vanessa Hudson on Long-Haul Demand → ونسا هادسون، مدیرعامل کانتاس در مورد تقاضای طولانی مدت |
| 197 | `daily` | 1 | 171 | AUD/USD Daily Report → گزارش روزانه AUD/USD ／ AUD/USD Daily Report → گزارش روزانه AUD/USD |
| 198 | `india` | 1 | 171 | NSE India Makes Trading Debut → NSE هند اولین معاملات را انجام می دهد ／ India Signals More Rate Hikes Ahead → هند سیگنال های افزایش نرخ بیشتر در پیش است |
| 199 | `jumps` | 1 | 169 | Rupee Jumps on RBI Measures → روپیه بر روی اقدامات RBI می پرد ／ GTC Jumps 10.44%, Is $0.24 Within Reach? → GTC ۱۰.۴۴% پرش می کند، آیا ۰.۲۴ دلار در دسترس است؟ |
| 200 | `day` | 1 | 168 | Big Oil’s day in court → روز بزرگ نفت در دادگاه ／ Today is BTC confidence day → امروز روز اعتماد به نفس بیت کوین است |

Appendix — top 3-grams:

| n-gram | headlines | example: source → output |
|--------|----------:|--------------------------|
| `ethereum price prediction` | 127 | Ethereum Price Prediction: ETH Falls to $2,5… → پیش بینی قیمت اتریوم: ETH به ۲۵۰۰ دلار سقوط می کند ／ Ethereum Price Prediction: Analyst Sees ETH … → پیش بینی قیمت اتریوم: تحلیلگر ETH را ۸۶۰۰ دلار می بیند |
| `crypto prediction market` | 106 | XRP price at Oct 3, 2026 at 9am EDT Crypto P… → قیمت XRP در ۳ اکتبر ۲۰۲۶ در ساعت ۹ صبح EDT بازار پیش ب… ／ BTC price on Oct 4, 2026 at 3am EDT Crypto P… → قیمت بیت کوین در ۴ اکتبر ۲۰۲۶ در ساعت ۳ بامداد EDT باز… |
| `edt crypto prediction` | 106 | XRP price at Oct 3, 2026 at 9am EDT Crypto P… → قیمت XRP در ۳ اکتبر ۲۰۲۶ در ساعت ۹ صبح EDT بازار پیش ب… ／ BTC price on Oct 4, 2026 at 3am EDT Crypto P… → قیمت بیت کوین در ۴ اکتبر ۲۰۲۶ در ساعت ۳ بامداد EDT باز… |
| `fed rate hike` | 85 | US jobs data revised lower after Fed rate hi… → پس از افزایش نرخ بهره فدرال رزرو، داده های مشاغل ایالا… ／ What’s Next for Stocks After the US Fed Rate… → آینده سهام پس از افزایش نرخ بهره فدرال رزرو آمریکا چیس… |
| `bitcoin price prediction` | 80 | Bitcoin Price Prediction: Can BTC Extend the… → پیش بینی قیمت بیت کوین: آیا بیت کوین می تواند رشد رالی… ／ Bitcoin Price Prediction: Power Law Model Ma… → پیش بینی قیمت بیت کوین: نقشه های مدل قانون قدرت ۱۵۷.۸ … |
| `solana price prediction` | 75 | Solana Price Prediction: What Comes Next for… → پیش‌بینی قیمت سولانا: آینده SOL چه خواهد شد؟ ／ Solana Price Prediction: Why SOL Is Setting … → پیش بینی قیمت Solana: چرا SOL با قیمت ۱۲۰ دلار راه اند… |
| `xrp price prediction` | 72 | XRP Price Prediction For September 24 → پیش بینی قیمت XRP برای ۲۴ سپتامبر ／ XRP Price Prediction For September 21-27 → پیش بینی قیمت XRP برای ۲۱-۲۷ سپتامبر |
| `gold and silver` | 69 | What’s the best way to buy gold and silver? → بهترین راه برای خرید طلا و نقره چیست؟ ／ Gold and silver prices fall on global markets → کاهش قیمت طلا و نقره در بازارهای جهانی |
| `cardano price prediction` | 61 | Cardano Price Prediction Q4 2026: Can ADA Cl… → پیش بینی قیمت Cardano Q۴ ۲۰۲۶: آیا ADA می تواند دیوار … ／ Cardano Price Prediction for October: Will A… → پیش بینی قیمت Cardano برای ماه اکتبر: آیا ADA به بالای… |
| `dogecoin price prediction` | 61 | Dogecoin Price Prediction: DOGE Keeps Climbi… → پیش بینی قیمت Dogecoin: DOGE به صعود ادامه می دهد ／ Dogecoin Price Prediction: Can DOGE Reach $0… → پیش بینی قیمت Dogecoin: آیا DOGE می تواند به ۰.۱۱۷ دلا… |
| `stock market live` | 60 | Yahoo Finance - Stock Market Live, Quotes, B… → یاهو فاینانس - بازار سهام زنده، مظنه، اخبار تجاری و ما… ／ Stock Market LIVE: Sensex down 400 pts, Nift… → بازار سهام زنده: Sensex ۴۰۰ درصد کاهش، Nifty زیر ۲۲۶۰۰… |
| `on sep at` | 59 | — |
| `today stock market` | 57 | Sensex today \| Stock Market Live: Sensex cra… → سکس امروز \| بازار سهام زنده: Sensex بیش از ۹۵۰ امتیاز … ／ Sensex today \| Stock Market Live: Sensex tan… → سکس امروز \| بازار سهام زنده: Sensex تانک ۱۱۲۴ امتیاز د… |
| `price prediction can` | 56 | Dogecoin Price Prediction: Can DOGE Reach $0… → پیش بینی قیمت Dogecoin: آیا DOGE می تواند به ۰.۱۱۷ دلا… ／ Bitcoin Price Prediction: Can BTC Extend the… → پیش بینی قیمت بیت کوین: آیا بیت کوین می تواند رشد رالی… |
| `stock market today` | 56 | Stock Market Today (Oct. 5, 2026): (Futures) → بورس امروز (۵ اکتبر ۲۰۲۶): (آینده) ／ Nasdaq 100 Hits Record, Brazil's EWZ Soars 1… → نزدک ۱۰۰ رکورد، EWZ برزیل ۱۳ درصد افزایش یافت: بازار س… |
| `sensex today stock` | 55 | Sensex today \| Stock Market Live: Sensex cra… → سکس امروز \| بازار سهام زنده: Sensex بیش از ۹۵۰ امتیاز … ／ Sensex today \| Stock Market Live: Sensex tan… → سکس امروز \| بازار سهام زنده: Sensex تانک ۱۱۲۴ امتیاز د… |
| `xrp price at` | 53 | XRP price at Sep 19, 2026 at 3am EDT Predict… → قیمت XRP در ۱۹ سپتامبر ۲۰۲۶ در ساعت ۳ صبح EDT بازار پی… ／ XRP price at Sep 20, 2026 at 2am EDT Predict… → قیمت XRP در ۲۰ سپتامبر ۲۰۲۶ در ساعت ۲ بامداد EDT بازار… |
| `here s why` | 52 | Here’s Why the Elites are Rushing CBDCs → در اینجا دلیل عجله نخبگان در CBDC ها آمده است ／ Here’s why the KOSPI index is plunging today… → در اینجا دلیل سقوط شاخص KOSPI در امروز (۶ اکتبر) است. |
| `the stock market` | 51 | AI Agents Are Upending a Big Slice of the St… → عوامل هوش مصنوعی بخش بزرگی از بازار سهام را از بین می … ／ S&P 500: Rising Rates Put the Stock Market B… → S&P ۵۰۰: افزایش نرخ ها بازار سهام را به حالت هشدار باز… |
| `silver price forecast` | 48 | Silver Price Forecast: Bearish Breakdown Put… → پیش بینی قیمت نقره: شکست نزولی ۵۴.۷۸ دلار را در معرض خ… ／ Silver Price Forecast: XAG/USD builds base a… → پیش بینی قیمت نقره: XAG/USD پایه بالاتر از ۶۰ دلار، چش… |

Appendix — top 4-grams:

| n-gram | headlines | example: source → output |
|--------|----------:|--------------------------|
| `edt crypto prediction market` | 106 | XRP price at Oct 3, 2026 at 9am EDT Crypto P… → قیمت XRP در ۳ اکتبر ۲۰۲۶ در ساعت ۹ صبح EDT بازار پیش ب… ／ BTC price on Oct 4, 2026 at 3am EDT Crypto P… → قیمت بیت کوین در ۴ اکتبر ۲۰۲۶ در ساعت ۳ بامداد EDT باز… |
| `sensex today stock market` | 55 | Sensex today \| Stock Market Live: Sensex cra… → سکس امروز \| بازار سهام زنده: Sensex بیش از ۹۵۰ امتیاز … ／ Sensex today \| Stock Market Live: Sensex tan… → سکس امروز \| بازار سهام زنده: Sensex تانک ۱۱۲۴ امتیاز د… |
| `today stock market live` | 48 | Sensex today \| Stock Market Live: Sensex cra… → سکس امروز \| بازار سهام زنده: Sensex بیش از ۹۵۰ امتیاز … ／ Sensex today \| Stock Market Live: Sensex tan… → سکس امروز \| بازار سهام زنده: Sensex تانک ۱۱۲۴ امتیاز د… |
| `price on sep at` | 44 | — |
| `price at sep at` | 42 | — |
| `xrp price at sep` | 42 | XRP price at Sep 19, 2026 at 3am EDT Predict… → قیمت XRP در ۱۹ سپتامبر ۲۰۲۶ در ساعت ۳ صبح EDT بازار پی… ／ XRP price at Sep 20, 2026 at 2am EDT Predict… → قیمت XRP در ۲۰ سپتامبر ۲۰۲۶ در ساعت ۲ بامداد EDT بازار… |
| `stock market live sensex` | 38 | Stock Market LIVE: Sensex down 400 pts, Nift… → بازار سهام زنده: Sensex ۴۰۰ درصد کاهش، Nifty زیر ۲۲۶۰۰… ／ Stock Market LIVE: Sensex, Nifty stuck in ra… → بازار سهام زنده: Sensex، Nifty در محدوده گیر کرده است.… |
| `dogecoin price on sep` | 37 | Dogecoin price on Sep 20, 2026 at 1am EDT Pr… → قیمت Dogecoin در ۲۰ سپتامبر ۲۰۲۶ در ساعت ۱ بامداد EDT … ／ Dogecoin price on Sep 20, 2026 at 3am EDT Pr… → قیمت Dogecoin در ۲۰ سپتامبر ۲۰۲۶ در ساعت ۳ صبح EDT باز… |
| `ethereum price prediction eth` | 28 | Ethereum Price Prediction: ETH Falls to $2,5… → پیش بینی قیمت اتریوم: ETH به ۲۵۰۰ دلار سقوط می کند ／ Ethereum Price Prediction: ETH Breakout Targ… → پیش بینی قیمت اتریوم: ETH Breakout ۳۴۰۰ دلار را هدف قر… |
| `a stock market crash` | 25 | Worried About a Stock Market Crash? History … → نگران سقوط بازار سهام هستید؟ تاریخ می گوید نه چندان سر… ／ 2 Stocks to Buy Hand Over Fist if a Stock Ma… → ۲ سهام برای خرید در صورت سقوط بازار سهام |
| `silver price forecast xag/usd` | 25 | Silver Price Forecast: XAG/USD builds base a… → پیش بینی قیمت نقره: XAG/USD پایه بالاتر از ۶۰ دلار، چش… ／ Silver Price Forecast: XAG/USD remains below… → پیش بینی قیمت نقره: XAG/USD با افزایش قیمت نفت زیر ۶۱.… |
| `silver rate today in` | 24 | Silver Rate Today in Kochi – Silver Price pe… → نرخ نقره امروز در کوچی – قیمت نقره هر گرم و کیلوگرم \| … ／ Silver Rate Today in Mysore – Silver Price p… → نرخ نقره امروز در میسور – قیمت نقره هر گرم و کیلوگرم \|… |
| `for the first time` | 23 | Bitcoin Hits $85,000 For The First Time Sinc… → بیت کوین برای اولین بار از ژانویه ۲۰۲۶ به ۸۵۰۰۰ دلار ر… ／ BOK to add gold to its coffers for the first… → BOK برای اولین بار از سال ۲۰۱۳ طلا را به خزانه خود اضا… |
| `gold price forecast xau/usd` | 23 | Gold Price Forecast: XAU/USD extends its str… → پیش بینی قیمت طلا: XAU/USD مبارزه خود را به زیر ۴۲۰۰ د… ／ Gold Price Forecast: XAU/USD Plunges 12.4% T… → پیش بینی قیمت طلا: XAU/USD ۱۲.۴ درصد به سمت حمایت بحرا… |
| `kg todays silver price` | 21 | Silver Rate Today in Dhar 10th October 2026 … → نرخ نقره امروز به در ۱۰ اکتبر ۲۰۲۶: ۱ کیلوگرم، قیمت نق… ／ Silver Rate Today in Ahmedabad 4th October 2… → نرخ نقره امروز در احمدآباد ۴ اکتبر ۲۰۲۶: ۱ کیلوگرم، قی… |
| `todays silver price in` | 21 | Silver Rate Today in Dhar 10th October 2026 … → نرخ نقره امروز به در ۱۰ اکتبر ۲۰۲۶: ۱ کیلوگرم، قیمت نق… ／ Silver Rate Today in Ahmedabad 4th October 2… → نرخ نقره امروز در احمدآباد ۴ اکتبر ۲۰۲۶: ۱ کیلوگرم، قی… |
| `btc price range on` | 20 | BTC price range on Oct 5, 2026 at 8am EDT Cr… → محدوده قیمت بیت کوین در تاریخ ۵ اکتبر ۲۰۲۶ در ساعت ۸ ص… ／ BTC price range on Oct 5, 2026 at 9am EDT Cr… → محدوده قیمت بیت کوین در ۵ اکتبر ۲۰۲۶ در ساعت ۹ صبح به … |
| `stock market crash is` | 20 | 2 Stocks to Buy Hand Over Fist if a Stock Ma… → ۲ سهام برای خرید در صورت سقوط بازار سهام ／ 2 Stocks to Buy Hand Over Fist if a Stock Ma… → ۲ سهام برای خرید در صورت سقوط بازار سهام |
| `what it means for` | 20 | Bitget’s $352M Loss: What It Means for DeFi … → ضرر ۳۵۲ میلیون دلاری Bitget: معنای آن برای کاربران DeFi ／ How Liquid Network Lost $15B—and What It Mea… → چگونه Liquid Network ۱۵ میلیارد دلار از دست داد – و مع… |
| `cardano price prediction ada` | 19 | Cardano Price Prediction: ADA Is Up 30% in a… → پیش بینی قیمت Cardano: ADA در یک هفته ۳۰٪ افزایش می یا… ／ Cardano Price Prediction: ADA Rallies 11%, O… → پیش بینی قیمت Cardano: ADA رالی ۱۱٪، بهره باز جهش ۱۵٪ |

### 7. Inconsistent renderings of the same finance term

**Method A — known renderings (vendor `crypto_names.txt`):** all surface variants found in outputs of sources containing the term (≥ 15 outputs; variant counted if seen ≥ 5×; 161 vendor triples skipped as irregular):

| EN term | FA rendering | surface variants (count) | verdict |
|---------|--------------|--------------------------:|---------|
| `Binance Coin` | بایننس کوین | «بایننس کوین»×23 | ok ✓ |
| `Bitcoin` | بیت کوین | «بیت کوین»×6077, «بیت‌کوین»×607 | inconsistent ✗ |
| `Cardano` | کاردانو | «کاردانو»×192 | ok ✓ |
| `Ethereum` | اتریوم | «اتریوم»×2166 | ok ✓ |
| `Monero` | مونرو | «مونرو»×15 | ok ✓ |
| `SHIBA INU` | شیبا اینو | «شیبا اینو»×47 | ok ✓ |
| `Stellar` | استلار | «استلار»×12 | ok ✓ |
| `TRON` | ترون | «ترون»×10 | ok ✓ |
| `Tether` | تتر | «تتر»×137 | ok ✓ |
| `XRP` | بیت‌کوین | «بیت‌کوین»×67 | ok ✓ |

**Method B — data-driven candidates** (frequent EN terms; word/bigram candidates with count ≥ max(6, 12% of matching outputs) and lift ≥ 5 vs background; flagged when two strong candidates rarely co-occur (obs < 0.5·expected) and neither key contains the other). Flags include polysemy (one English word with several legitimate Persian words); only stylistic alternates of the same meaning are glossary targets — sorted by matched-set size, smallest first:

| EN term | outputs | candidate renderings (count) | obs/exp co-occur | verdict |
|---------|--------:|-----------------------------|-----------------:|---------|
| `thorchain` | 48 | «میلیون»×25, «دلار»×19, «مسدود»×18, «میلیون دلار»×16, «کرد»×15 | 0.021/0.109 | inconsistent ✗ |
| `avalanche` | 55 | «بهمن»×25, «است»×20, «برای»×20, «های»×16, «دلار»×14 | 0.036/0.093 | inconsistent ✗ |
| `status` | 56 | «وضعیت»×43, «است»×26, «کند»×23, «برای»×20, «می کند»×20 | 0.054/0.110 | inconsistent ✗ |
| `tron` | 58 | «است»×20, «های»×19, «کوین»×13, «پرداخت»×13, «کند»×12 | 0.000/0.043 | inconsistent ✗ |
| `stellar` | 59 | «کند»×19, «های»×19, «می کند»×18, «است»×16, «برای»×14 | 0.017/0.060 | inconsistent ✗ |
| `quant` | 63 | «دلار»×21, «افزایش»×19, «است»×17, «کوانت»×16, «قیمت»×16 | 0.000/0.039 | inconsistent ✗ |
| `flow` | 66 | «کند»×17, «نقدی»×17, «های»×17, «است»×16, «می کند»×15 | 0.015/0.066 | inconsistent ✗ |
| `aave` | 72 | «شده»×25, «افزایش»×24, «وام»×22, «برای»×22, «سهام»×21 | 0.028/0.093 | inconsistent ✗ |
| `tether` | 174 | «تتر»×126, «میلیون»×63, «دلار»×60, «کوین»×54, «است»×50 | 0.040/0.081 | inconsistent ✗ |
| `gas` | 371 | «طبیعی»×148, «گاز طبیعی»×148, «نفت»×128, «های»×123, «است»×86 | 0.065/0.138 | inconsistent ✗ |
| `cardano` | 538 | «قیمت»×283, «کاردانو»×168, «دلار»×161, «پیش»×122, «بینی»×106 | 0.017/0.071 | inconsistent ✗ |
| `eth` | 807 | «اتریوم»×535, «دلار»×369, «قیمت»×339, «قیمت اتریوم»×250, «است»×180 | 0.032/0.069 | inconsistent ✗ |
| `how` | 842 | «چگونه»×408, «است»×316, «این»×262, «برای»×256, «های»×196 | 0.006/0.079 | inconsistent ✗ |
| `amid` | 850 | «میان»×460, «در میان»×459, «بحبوحه»×353, «در بحبوحه»×353, «افزایش»×327 | 0.005/0.225 | inconsistent ✗ |
| `next` | 880 | «بعدی»×454, «است»×304, «دلار»×247, «قیمت»×246, «برای»×243 | 0.007/0.140 | inconsistent ✗ |
| `rally` | 893 | «رالی»×471, «افزایش»×422, «قیمت»×317, «دلار»×308, «کوین»×264 | 0.026/0.059 | inconsistent ✗ |
| `now` | 897 | «اکنون»×625, «است»×536, «این»×326, «حال»×245, «شده»×241 | 0.080/0.190 | inconsistent ✗ |
| `billion` | 904 | «دلار»×597, «میلیارد دلار»×539, «است»×299, «دلاری»×280, «میلیارد دلاری»×259 | 0.037/0.185 | inconsistent ✗ |
| `about` | 975 | «است»×496, «مورد»×387, «در مورد»×368, «حدود»×357, «این»×348 | 0.042/0.145 | inconsistent ✗ |
| `high` | 984 | «بالاترین»×466, «به بالاترین»×371, «قیمت»×299, «دلار»×297, «است»×285 | 0.015/0.061 | inconsistent ✗ |
| `submitted` | 1064 | «ارسال شده»×833, «شده توسط»×808, «نظر»×724, «لینک»×476, «است»×410 | 0.004/0.154 | inconsistent ✗ |
| `why` | 1074 | «است»×412, «کوین»×274, «بیت»×269, «دلار»×247, «بیت کوین»×246 | 0.014/0.030 | inconsistent ✗ |
| `comments` | 1112 | «توسط»×856, «ارسال»×851, «ارسال شده»×830, «شده توسط»×806, «نظر»×735 | 0.004/0.141 | inconsistent ✗ |
| `today` | 1137 | «امروز»×853, «قیمت»×488, «است»×262, «بازار»×257, «افزایش»×256 | 0.024/0.049 | inconsistent ✗ |
| `link` | 1140 | «شده»×905, «توسط»×857, «ارسال»×850, «ارسال شده»×831, «شده توسط»×806 | 0.004/0.150 | inconsistent ✗ |
| `september` | 1172 | «است»×385, «افزایش»×339, «قیمت»×333, «ماه»×317, «دلار»×295 | 0.011/0.060 | inconsistent ✗ |
| `silver` | 1211 | «قیمت»×516, «طلا»×482, «طلا و»×290, «و نقره»×289, «افزایش»×272 | 0.014/0.070 | inconsistent ✗ |
| `october` | 1223 | «قیمت»×430, «۲۰۲۶»×399, «اکتبر ۲۰۲۶»×364, «است»×352, «برای»×317 | 0.035/0.078 | inconsistent ✗ |
| `stocks` | 1275 | «افزایش»×463, «برای»×301, «است»×293, «نفت»×252, «ایالات»×251 | 0.024/0.060 | inconsistent ✗ |
| `trading` | 1279 | «معاملات»×554, «است»×488, «برای»×430, «دلار»×343, «این»×326 | 0.041/0.091 | inconsistent ✗ |
| `solana` | 1298 | «سولانا»×835, «دلار»×420, «قیمت»×353, «است»×262, «کند»×243 | 0.014/0.043 | inconsistent ✗ |
| `btc` | 1322 | «بیت»×1050, «کوین»×1041, «بیت کوین»×1034, «دلار»×541, «قیمت»×429 | 0.012/0.029 | inconsistent ✗ |
| `can` | 1345 | «تواند»×607, «آیا»×594, «می تواند»×592, «است»×436, «دلار»×392 | 0.054/0.114 | inconsistent ✗ |
| `yields` | 1348 | «بازدهی»×836, «افزایش»×780, «بازده»×450, «اوراق»×430, «خزانه»×425 | 0.088/0.198 | inconsistent ✗ |
| `will` | 1413 | «خواهد»×647, «است»×467, «این»×462, «برای»×416, «آیا»×328 | 0.023/0.049 | inconsistent ✗ |
| `stock` | 1467 | «بازار»×568, «بازار سهام»×449, «افزایش»×396, «است»×393, «برای»×321 | 0.010/0.024 | inconsistent ✗ |
| `more` | 1510 | «است»×717, «برای»×497, «این»×483, «بیش»×465, «بیش از»×463 | 0.015/0.077 | inconsistent ✗ |
| `prediction` | 1518 | «پیش»×938, «بینی»×923, «پیش بینی»×923, «دلار»×557, «بینی قیمت»×549 | 0.017/0.091 | inconsistent ✗ |
| `prices` | 1762 | «افزایش»×883, «کاهش»×727, «نفت»×706, «قیمت نفت»×582, «طلا»×578 | 0.040/0.131 | inconsistent ✗ |
| `ethereum` | 1965 | «دلار»×752, «قیمت»×632, «بیت»×460, «قیمت اتریوم»×455, «است»×405 | 0.013/0.054 | inconsistent ✗ |
| `xrp` | 2048 | «قیمت»×702, «دلار»×664, «است»×458, «کند»×358, «افزایش»×323 | 0.011/0.022 | inconsistent ✗ |
| `market` | 3593 | «است»×1213, «قیمت»×836, «افزایش»×811, «کوین»×748, «سهام»×732 | 0.006/0.042 | inconsistent ✗ |
| `crypto` | 3806 | «کریپتو»×1339, «است»×1020, «رمزنگاری»×958, «دلار»×953, «بازار»×900 | 0.011/0.089 | inconsistent ✗ |
| `gold` | 4210 | «طلا»×3124, «قیمت»×1390, «افزایش»×1044, «دلار»×921, «قیمت طلا»×863 | 0.024/0.050 | inconsistent ✗ |
| `price` | 4660 | «دلار»×1944, «پیش»×1297, «بینی»×1227, «پیش بینی»×1221, «افزایش»×1079 | 0.024/0.048 | inconsistent ✗ |

Worked examples (real source → current output):

- **`thorchain`** — «مسدود»×18 vs «شده»×14:
  - `Bitget CEO Wants Thorchain to Block Hackers, but There’s a Catch` → `مدیر عامل Bitget می خواهد Thorchain هکرها را مسدود کند، اما یک مشکل وجود دارد`
  - `On Saturday, two days after Bitget was hacked, CEO Gracy Chen publicl…` → `روز شنبه، دو روز پس از هک شدن Bitget، مدیر عامل Gracy Chen علناً از Thorchain خ…`
- **`avalanche`** — «برای»×20 vs «دلار»×14:
  - `ICE Considers Avalanche to Launch NYSE Tokenized Trading Engine` → `ICE بهمن را برای راه‌اندازی موتور معاملاتی توکن‌شده NYSE در نظر می‌گیرد`
  - `Kevin O’Leary says Bitcoin (BTC) can reach $1 million. He attaches on…` → `کوین اولری می گوید بیت کوین (BTC) می تواند به ۱ میلیون دلار برسد. او یک شرط را …`
- **`status`** — «کند»×23 vs «کرده»×15:
  - `The case highlights the growing risk of crypto in financial fraud, th…` → `این مورد، خطر فزاینده کریپتو در کلاهبرداری مالی را نشان می دهد که وضعیت هنگ کنگ…`
  - `Paxos Labs has launched PAXGy, a token backed by PAXG that can increa…` → `Paxos Labs PAXGy را راه‌اندازی کرده است، توکنی که توسط PAXG پشتیبانی می‌شود و م…`

### 8. Character / punctuation / digit problems in published outputs

Measured over **36546** published outputs (title_fa + summary_fa). Counts are outputs affected; each suspect pattern is a candidate defect, judged by its regex.

| problem | outputs affected | share | example fragment |
|---------|-----------------:|------:|-----------------|
| Arabic yeh/kaf (ي ك) instead of Persian ی ک | 4 | 0.0% | `ك` |
| tatweel ـ | 0 | 0.0% | `` |
| missing ZWNJ after می/نمی («می رود») | 15791 | 43.2% | `می ک` |
| missing ZWNJ in plural ها/های («سقوط ها») | 6886 | 18.8% | `م های ` |
| missing ZWNJ in comparative تر/ترین («بزرگ تر») | 1129 | 3.1% | `عمیق تر ` |
| space before ، ؛ ؟ («متن ،») | 2 | 0.0% | ` ،` |
| « » broken spacing («« متن» or «متن »») | 6 | 0.0% | `« ` |
| double space | 0 | 0.0% | `` |
| mixed digit styles (ASCII + Persian digits in one output) | 0 | 0.0% | `` |
| Persian digits inside URLs (fa_digits corrupted the link) | 101 | 0.3% | `https://imgur.com/۳y۷vezP` |

### 9. 30 worst examples (source → current output)

Sorted by lowest Persian letter share, then longest Latin run.

| # | kind | share | run | source | output |
|---|------|------:|----:|--------|--------|
| 1 | summary | 0.00 | 46 | Cointribune lance une nouvelle quête Read2Earn en partenari… | Cointribune lance une nouvelle quête Read۲Earn en partenariat avec OKX, un exch… |
| 2 | summary | 0.00 | 44 | Le marché crypto n’est pas encore entré dans une période d’… | Le marché crypto n’est pas encore entré dans une période d’altseason confirmée,… |
| 3 | summary | 0.00 | 43 | Le mot « courtier en ligne » recouvre aujourd'hui deux réal… | Le mot « courtier en ligne » recouvre aujourd'hui deux réalités qui n'ont plus … |
| 4 | summary | 0.00 | 33 | Depuis le 14 septembre 2026, les détenteurs de SPYx, QQQx e… | Depuis le ۱۴ Septembre ۲۰۲۶, les detenteurs de SPYx, QQQx et NVDAx sur Kraken p… |
| 5 | summary | 0.00 | 33 | Les marchés prédictifs anticipent encore une progression d’… | Les marchés predictifs anticipent encore une progression d’Ethereum، de Solana … |
| 6 | summary | 0.00 | 32 | Entre les portefeuilles secrets des géants et les simulatio… | Entre les portefeuilles Secrets des Géants et les Simulations Chocs de Wall Str… |
| 7 | summary | 0.00 | 32 | Mit Talea DRN können Arrangeure ein Wertpapier emittieren, … | Mit Talea DRN können Arrangeure ein Wertpapier emittieren, das sowohl tradicion… |
| 8 | title | 0.00 | 32 | Solidion Technology (NASDAQ: STI) sieht keinen Grund, sein … | Solidion Technology (NASDAQ: STI) sieht keinen Grund, sein Angebot an Polar Pow… |
| 9 | title | 0.00 | 31 | MTCM lance Talea DRN : un titre du marché privé, deux volet… | MTCM lance Talea DRN: un titre du marché privé، deux volets، destiné aux arrang… |
| 10 | summary | 0.00 | 30 | Das Unternehmen sieht keinen Grund für eine Erhöhung seines… | Das Unternehmen sieht keinen Grund für eine Erhöhung seines Angebots, da Flux P… |
| 11 | title | 0.00 | 30 | Solidion Technology (NASDAQ: STI) blijft bij zijn bod op Fl… | Solidion Technology (NASDAQ: STI) blijft bij zijn bod op Flux Power (NASDAQ: FL… |
| 12 | summary | 0.00 | 29 | La BCE veut préparer l’euro numérique à une économie où les… | La BCE veut préparer l’euro numérique à une économie où les humains ne seront p… |
| 13 | summary | 0.00 | 28 | Le bitcoin s’apprête à signer son meilleur troisième trimes… | Le bitcoin s’apprête à signer son meilleur troisième trimestre depuis ۲۰۱۷، ave… |
| 14 | summary | 0.00 | 28 | Vitalik Buterin estime que Hegota, le fork Ethereum prévu e… | Vitalik Buterin estime que Hegota, le fork Ethereum prévu en ۲۰۲۷, pourrait êtr… |
| 15 | summary | 0.00 | 24 | Talea DRN permet aux organisateurs d'émettre un titre uniqu… | Talea DRN permet aux organisateurs d'émettre un titre s'adressant à la fois aux… |
| 16 | title | 0.00 | 20 | MTCM lanza Talea DRN, bono de mercados privados que une lo … | MTCM lanza Talea DRN, bono de mercados privados que une lo tradicional y lo dig… |
| 17 | title | 0.00 | 19 | Bringin lance des comptes professionnels en euros destinés … | Bringin lance des comptes professionnels en euro destinés aux entreprises qui a… |
| 18 | summary | 0.00 | 19 | Les moyennes mobiles à 50, 100 et 200 jours du bitcoin sont… | Les moyennes mobiles à ۵۰, ۱۰۰ et ۲۰۰ jours du bitcoin sont sur le point de ret… |
| 19 | summary | 0.00 | 18 | Les cryptos liées à l’intelligence artificielle (IA) ont la… | Les cryptos liées à l’intelligence artificielle (IA) ont largement dépassé le m… |
| 20 | summary | 0.00 | 17 | Langkah terbaru DFA untuk mengubah reksa dana kloning menja… | Langkah terbaru DFA untuk mengubah reksa dana kloning menjadi kelas saham ETF b… |
| 21 | title | 0.00 | 16 | Bringin führt Euro-Geschäftskonten für Unternehmen ein, die… | Bringin führt Euro-Geschäftskonten für Unternehmen ein, die Bitcoin einsetzen, … |
| 22 | summary | 0.00 | 16 | Crystal Intelligence a coopéré avec les forces de l’ordre d… | Crystal Intelligence a coopéré avec les force de l’ordre dans le cadre d’une en… |
| 23 | title | 0.00 | 14 | CoinMarketCap s’offre Coinglass et met la main sur les donn… | CoinMarketCap s'offre Coinglass et met la main sur les données du marché des dé… |
| 24 | summary | 0.00 | 14 | Niedawne duże transfery Bitcoin przez podmioty instytucjona… | Niedawne duże transfery Bitcoin przez podmioty instytucjonalne zwróciły uwagę r… |
| 25 | title | 0.00 | 13 | BORICA und OpenWay gewinnen den PAY360-Award für die Umstel… | BORICA und OpenWay gewinnen den PAY۳۶۰-Award für die Umstellung des Euro-Zahlun… |
| 26 | title | 0.00 | 13 | Dow Jones Futures: Yields Move Higher; Samsung, Micron, Tai… | Dow Jones Futures: Yields Move Higher. Samsung, Micron, Taiwan Semi, Sandisk In… |
| 27 | summary | 0.00 | 12 | Le réseau Bitcoin se trouve désormais à moins de 80000 bloc… | Le réseau Bitcoin se trouve désormais à moins de ۸۰۰۰۰ blocs de son cinquième h… |
| 28 | title | 0.00 | 12 | XRP : Les progrès du réseau ne se traduisent pas encore en … | XRP: Les progrès du réseau ne se traduisent pas encore en hausse |
| 29 | title | 0.00 | 11 | Crypto : Bitwise lance le premier ETF NEAR au comptant aux … | Crypto: Bitwise lance le premier ETF NEAR au comptant aux États-Unis |
| 30 | title | 0.00 | 11 | Crypto : Le Kazakhstan étudie avec Tether un stablecoin en … | Crypto: Le Kazakhstan étudie avec Tether un stablecoin en monnaie locale |

### 10. Live endpoint probe (network; `tools/fa_build/probe_endpoint.py`)

Run 2026-10-12 10:52 local, ~15 GETs, 1 req/s, raw endpoint requests (no cache
writes, no translate.translate_many):

- **(a) Re-asking echoed headlines:** both fixed English headlines (cache value
  byte-identical to the source) were asked again through a fresh request —
  **still verbatim echoes** (Persian share 0.00, pass=0). A second ask does not
  fix an echo; a third-party retry would just re-cache the same text.
- **(b) Sentence-by-sentence:** a 374-char half-translated summary (4 sentences):
  whole ask → share 0.42, Latin run 27, fail; per-sentence asks → only 1/4
  sentences passes `is_persian`; joined result still fails (0.42/27).
  Sentence splitting alone does not rescue texts with embedded
  non-translatable content — the D.2 retry must accept-and-join-or-«""».
- **(c) Query length:** URL length 4,078 → 200; 8,081 → 200; 12,084 → 200;
  **20,090 → HTTP 400**. The cliff sits between ≈12 KB and ≈20 KB of URL; the
  conservative Phase-3b batch budget is **≈8.4 KB (70% × 12,084, the largest
  confirmed-OK URL)**.
- **(d) Batch of 16 alignment:** complete batch → 16/16 aligned. With slot 8
  replaced by an **empty string** the endpoint still returned 16 items with the
  empty kept in place → 15/16 markers at their expected positions, **no mid-drop
  shift**; a very short member ("ok") → 16/16 aligned. The end-padding
  misalignment (A3) did not reproduce for empty/short members in this probe.

### 11. Method & caveats

- DB read with `file:.mohmd_news.db?mode=ro`; cache read from a temp copy;
  `translate.translate_many` / `save_cache` never called — this audit performs
  **zero writes and zero network requests**.
- Gate semantics are `translate.py`'s own (`is_persian`, `persian_share`,
  `longest_latin_run`, `_looks_persian`) — measured, not re-implemented.
- N-grams: `title` sources, lowercased, tokens `[a-z0-9'&.%/-]*`, pure-digit
  tokens dropped, orders 1–4.
- Term inconsistency is a *screen*, not ground truth: Method A is exact for
  vendor-known renderings; Method B is a lift + co-occurrence heuristic and
  may miss alternates that share words (or flag rare combinations) — every
  flagged item above ships with real source/output examples for manual review.
- `summary_fa` is stored from `summary[:1000]` (app.py
  `_translate_articles_inplace`), so long summaries are only audited on their
  first 1000 chars.
- Generated by `tools/fa_build/audit.py` on 2026-10-12.
