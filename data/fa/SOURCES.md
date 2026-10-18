# data/fa/SOURCES.md — provenance for the Phase-1 FA data bundle

Built by the standalone scripts in `tools/fa_build/` (network lives there only; nothing in this directory is imported by the app at runtime). Raw downloads cached under `var/fa_raw/` (gitignored). License rule: openly-licensed sources only.

## entities.tsv

- rows: **1345**
- built: 2026-10-12
- source: Wikidata (SPARQL, CC0) — CC0-1.0 — https://query.wikidata.org/sparql
  - detail: bank=464, central_bank=93, commodity=8, country=212, crypto_exchange=17, currency=303, stock_exchange=130, stock_index=68
- source: Wikidata (search+getentities, CC0) — CC0-1.0 — https://www.wikidata.org/w/api.php
  - detail: commodity=13, company=12, org=6, person=19
- source: project corpus audit seeds — n/a (input list) — docs/fa_audit.md §5/§9
  - detail: 82 English names: corpus-audit finance/crypto names + traded commodities
- note: No inferred rows: entities without an fa Wikidata label are skipped (never fabricated).

### 20-row sample (deterministic md5 ordering)

```
kind | qid | en | fa | aliases_en | aliases_fa | source
central_bank | Q5194994 | currency commission | کمیسیون ارز ایرلند |  |  | wikidata-sparql:Q66344
bank | Q30686532 | x.com | ایکس دات کام |  |  | wikidata-sparql:Q22687
bank | Q4034833 | al habib bank | بانک الحبیب | bank al habib limited|bank al habib |  | wikidata-sparql:Q22687
bank | Q631047 | hdfc bank | اچدیافسی بانک | payzapp |  | wikidata-sparql:Q22687
central_bank | Q806703 | bank of canada | بانک کانادا | 19065377 |  | wikidata-sparql:Q66344
country | Q228 | andorra | آندورا | principality of the valleys of andorra|principality of andorra |  | wikidata-sparql:Q6256
country | Q1037 | rwanda | رواندا | the land of a thousand hills|republic of rwanda | روآندا | wikidata-sparql:Q6256
company | Q1192211 | strategy | مایکرواستراتژی | mstr|microstrategy|strategy inc. |  | wikidata-search:seed
bank | Q6068974 | icbc turkey bank | تکستیلبانک | tekstilbank |  | wikidata-sparql:Q22687
central_bank | Q2631674 | central bank of chile | بانک مرکزی شیلی |  |  | wikidata-sparql:Q66344
currency | Q200753 | mozambican metical | مثقال موزایکی | metical | متیکال موزامبیک | wikidata-sparql:Q8142
currency | Q3833310 | tuscan pound | پوند توسکانی |  |  | wikidata-sparql:Q8142
stock_exchange | Q891559 | mexican stock exchange | بورس اوراق بهادار مکزیک | xmex|mexbol|ibarrapromocion|bolsa mexicana|bmv|bolsa mexicana de valores |  | wikidata-sparql:Q11691
country | Q148 | people's republic of china | جمهوری خلق چین | the people's republic of china|the prc|pr china|p.r.c.|china pr|communist china |  | wikidata-sparql:Q6256
bank | Q2882611 | bank negara indonesia | بانک نگارا اندونزی | state bank of indonesia|pt bank negara indonesia (persero) tbk|bbni|bank negara indonesia (persero)|bni |  | wikidata-sparql:Q22687
crypto_exchange | Q104438477 | uniswap | یونیسواپ |  |  | wikidata-sparql:Q25401607
currency | Q187776 | denarius | دناریوس |  | دنار|دینار | wikidata-sparql:Q8142
bank | Q674093 | bank bph | بانک بیپیاچ | bank przemysłowo-handlowy |  | wikidata-sparql:Q22687
bank | Q105574200 | bank syariah indonesia | بانک سیاریا | bbsi|bsi |  | wikidata-sparql:Q22687
currency | Q522701 | netherlands antillean guilder | گیلدر آنتیل هلند | naƒ|naf|gulden (1828-date)|ƒ|ang|f |  | wikidata-sparql:Q8142
```

## terms.tsv

- rows: **3674**
- built: 2026-10-12
- source: vendor/persian-crypto-words (MIT) — MIT — vendor/persian-crypto-words/crypto_names.txt
  - detail: local file; semantic line scan (EN/FA/ticker), contradicting duplicate FA values dropped
- source: Wikidata via enwiki categories (CC0) — CC0-1.0 — https://www.wikidata.org/w/api.php (sites=enwiki)
  - detail: finance:Category:Finance, economics:Category:Economics, monetary:Category:Monetary policy, markets:Category:Financial markets, trading:Category:Commodity exchanges, crypto:Category:Cryptocurrencies, central-banks:Category:Central banks, banking:Category:Banking, stock-market:Category:Stock markets, commodities:Category:Commodities, inflation:Category:Inflation, currencies:Category:Currencies, fiscal:Category:Fiscal policy, investing:Category:Investment
- source: Wikidata term seeds (CC0) — CC0-1.0 — https://www.wikidata.org/w/api.php (wbsearchentities)
  - detail: 75 generic finance/econ/trading/crypto terms from docs/fa_audit.md §6
- source: fa.wiktionary dump (CC BY-SA 4.0) — CC BY-SA 4.0 — https://dumps.wikimedia.org/fawiktionary/latest/fawiktionary-latest-pages-articles.xml.bz2
  - detail: interwiki [[en:...]] links on fa pages
- source: project corpus (read-only) — n/a (own data) — .mohmd_news.db articles.title/title_fa
  - detail: evidence counts for REVIEW.md only
- note: contested keys: 178 (open: 167); pos '-' where no source states it (never guessed).
- note: vendor/list.txt skipped: FA-only, cannot form EN->FA pairs.

### 20-row sample (deterministic md5 ordering)

```
en | fa | pos | domain | source | confidence
tormenting | آزارنده | - | general | wiktionary-fa | 0.70
2021–2023 inflation surge | اوج‌گیری تورم ۲۰۲۲–۲۰۲۱ | - | inflation | wikidata:interlanguage | 0.80
koorooshan | کروشان | - | general | wiktionary-fa | 0.70
posterity | اعقاب | - | general | wiktionary-fa | 0.70
tinder | آتش‌افروز | - | general | wiktionary-fa | 0.70
mehran | مهران | - | general | wiktionary-fa | 0.70
chainlink | چین لینک | - | crypto | vendor:crypto_names | 0.90
audius | آدیوس | - | crypto | vendor:crypto_names | 0.90
cosmetologist | مشاطه | - | general | wiktionary-fa | 0.70
astronomer | اختر شناس | - | general | wiktionary-fa | 0.70
habil | هابیل | - | general | wiktionary-fa | 0.70
gymnospore | اسپر | - | general | wiktionary-fa | 0.70
phase | اهله | - | general | wiktionary-fa | 0.70
alis | آلیس | - | general | wiktionary-fa | 0.70
urbilum | اوربیلوم | - | general | wiktionary-fa | 0.70
asa daruv | اسادارو | - | general | wiktionary-fa | 0.70
success | نای | - | general | wiktionary-fa | 0.70
yield curve | منحنی بازدهی | - | markets | wikidata:term-seed | 0.80
sarpol-e-zahab | سرپل زهاب | - | general | wiktionary-fa | 0.70
semifluid | آب‌گون | - | general | wiktionary-fa | 0.70
```

## fa_wordfreq.tsv

**not built yet** (run the fetch script).

## Considered but skipped

- **Dehkhoda dictionary** — proprietary/copyright-unknown — not openly licensed
- **scraped news sites** — only acceptable for counts, none needed beyond the project's own feeds; robots/politeness risk
- **OPUS corpora** — no verified openly-licensed EN<->FA parallel corpus of financial terms fit for glossary extraction
- **Tatoeba** — CC BY but sentence-level example data, no domain glossary value beyond what Wiktionary already provides
- **vendor/persian-crypto-words list.txt** — FA-only list: cannot form EN->FA pairs (pairs come from crypto_names.txt)
