#!/usr/bin/env python3
"""
FA data collection — terms.tsv (Phase 1, deliverable b)
========================================================
English -> Persian term pairs for finance / economics / trading / crypto.

Sources (all license-clean):
  1. vendor/persian-crypto-words (MIT)  — crypto glossary, mixed triple
     orientations; kept only when both an EN key and an FA value survive
     script-detection (same rule the audit used).
  2. Wikidata (CC0) via enwiki category members -> fa labels. This is the
     modern form of "interlanguage links": an EN wikipedia article title in a
     finance category maps to its Wikidata item, which carries the fa label.
  3. fa.wiktionary (CC BY-SA) dump — interwiki [[en:...]] links on fa pages.

Output columns (fixed by the spec): en, fa, pos, domain, source, confidence.
pos is "-" unless a source states it (never guessed).

Where one EN key has several FA renderings, corpus evidence (how often each
rendering appears in pairs whose EN source contains the key) is computed here;
the preferred rendering is only auto-marked on strong evidence, everything
else goes to data/fa/REVIEW.md for human review.

Network: Wikidata API + dump download only, >=1.1 s/req, raw cached in
var/fa_raw/ (gitignored). DB opened read-only. Standalone only.
"""
import hashlib
import json
import re
import sqlite3
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fa_norm import (BASE, DATA_FA, RAW_DIR, ZWNJ, http_get_json,
                     norm_en, norm_fa, write_stats, write_tsv)

PAUSE = 1.1  # >=1 req/s for every Wikidata/dump request (politeness budget)

VENDOR_NAMES = BASE / "vendor" / "persian-crypto-words" / "crypto_names.txt"
VENDOR_LIST = BASE / "vendor" / "persian-crypto-words" / "list.txt"
WIKTIONARY_DUMP = RAW_DIR / "fawiktionary-pages-articles.xml.bz2"
WIKTIONARY_URL = ("https://dumps.wikimedia.org/fawiktionary/latest/"
                  "fawiktionary-latest-pages-articles.xml.bz2")
DB_FILE = BASE / ".mohmd_news.db"

CATMEM_URL = ("https://en.wikipedia.org/w/api.php?action=query&list=categorymembers"
              "&cmtitle={cat}&cmlimit=500&cmtype=file|subcat|page&format=json"
              "&continuation={cont}")
GETENT_URL = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
              "&sites=enwiki&titles={titles}&props=labels&languages=fa|en"
              "&format=json")

# enwiki category -> domain (page members whose Wikidata item has an fa label)
CATEGORIES = [
    ("finance",       "Category:Finance"),
    ("economics",     "Category:Economics"),
    ("monetary",      "Category:Monetary policy"),
    ("markets",       "Category:Financial markets"),
    ("trading",       "Category:Commodity exchanges"),
    ("crypto",        "Category:Cryptocurrencies"),
    ("central-banks", "Category:Central banks"),
    ("banking",       "Category:Banking"),
    ("stock-market",  "Category:Stock markets"),
    ("commodities",   "Category:Commodities"),
    ("inflation",     "Category:Inflation"),
    ("currencies",    "Category:Currencies"),
    ("fiscal",        "Category:Fiscal policy"),
    ("investing",     "Category:Investment"),
]

# Generic finance/econ/trading/crypto TERMS that the category scrape misses
# (enwiki has no "terminology" category). Every entry was seen among the top
# corpus n-grams in docs/fa_audit.md §6 — resolved via the Wikidata search API
# (top hit accepted only when the label contains the term).
TERM_SEEDS = [
    ("economics", "recession"), ("economics", "growth"), ("economics", "gdp"),
    ("economics", "unemployment"), ("economics", "consumer"),
    ("economics", "consumer price index"), ("economics", "inflation rate"),
    ("economics", "deficit"), ("economics", "surplus"), ("economics", "debt"),
    ("monetary", "interest rate"), ("monetary", "rate cut"),
    ("monetary", "rate hike"), ("monetary", "quantitative tightening"),
    ("monetary", "quantitative easing"), ("monetary", "stimulus"),
    ("monetary", "sanctions"), ("monetary", "tariff"),
    ("markets", "bond"), ("markets", "bond yield"), ("markets", "treasury"),
    ("markets", "yield curve"), ("markets", "inversion"),
    ("markets", "benchmark"), ("markets", "etf"), ("markets", "futures"),
    ("markets", "options"), ("markets", "hedge fund"), ("markets", "asset"),
    ("markets", "safe haven"), ("markets", "dividend"), ("markets", "earnings"),
    ("markets", "revenue"), ("markets", "profit"), ("markets", "loss"),
    ("markets", "volatility"), ("markets", "liquidity"), ("markets", "premium"),
    ("markets", "discount"), ("markets", "market capitalization"),
    ("trading", "rally"), ("trading", "selloff"), ("trading", "correction"),
    ("trading", "bubble"), ("trading", "breakout"), ("trading", "support"),
    ("trading", "resistance"), ("trading", "all-time high"),
    ("trading", "short squeeze"), ("trading", "flash crash"),
    ("trading", "bull market"), ("trading", "bear market"),
    ("crypto", "altcoin"), ("crypto", "halving"), ("crypto", "mining"),
    ("crypto", "hashrate"), ("crypto", "staking"), ("crypto", "airdrop"),
    ("crypto", "stablecoin"), ("crypto", "wallet"), ("crypto", "whale"),
    ("crypto", "market dominance"), ("crypto", "decentralized finance"),
    ("crypto", "bitcoin"), ("crypto", "ethereum"), ("crypto", "solana"),
    ("crypto", "binance coin"), ("crypto", "cardano"), ("crypto", "dogecoin"),
    ("crypto", "ripple"), ("crypto", "litecoin"), ("crypto", "chainlink"),
    ("crypto", "polkadot"), ("crypto", "avalanche"), ("crypto", "tron"),
]

CONF = {"vendor": 0.9, "wikidata": 0.8, "wiktionary": 0.7}
EVID_PREF = 0.7   # auto-preferred share of aligned evidence
EVID_MIN = 10     # ... with at least this many aligned occurrences

_LATIN_RE = re.compile(r"[A-Za-z]")
_FA_RE = re.compile(r"[\u0600-\u06FF]")


def _cached_json(url, cache_name, timeout=90, backoff=8):
    from time import sleep
    import urllib.error
    path = RAW_DIR / cache_name
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if not (isinstance(cached, dict) and cached.get("error")):
            return cached
        path.unlink()
    data = None
    for attempt in range(6):
        try:
            data = http_get_json(url, timeout=timeout)
            break
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 5:
                raise
            wait = backoff * (attempt + 1)
            print(f"    [throttle] 429 on {cache_name}, waiting {wait}s")
            sleep(wait)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    sleep(PAUSE)
    return data


# ---------------------------------------------------------------- source 1
def load_vendor():
    """crypto_names.txt: mostly (EN, FA, ticker) 3-line groups, but the file
    has structural defects (a duplicated FA line shifts several groups, and at
    least one group has no FA at all). So we scan semantically instead of
    trusting fixed offsets:

      * a line containing Persian letters is an FA value; the EN key is the
        closest preceding Latin line (within 2 lines);
      * a following ALL-CAPS token is the ticker (kept as a separate, lower-
        confidence pair — Phase 2 gates on ambiguity);
      * one FA value may only map to ONE EN key per source: later contradic-
        tions (e.g. the duplicated 'بیت‌کوین' glued onto 'XRP') are dropped,
        never guessed around.
    """
    lines = [ln.strip() for ln in
             VENDOR_NAMES.read_text(encoding="utf-8").splitlines()]
    fa_re = re.compile(r"[\u0621-\u063A\u0641-\u064A\u067E\u0686\u0698\u06A9"
                       r"\u06AF\u06CC]")
    latin_re = re.compile(r"^[A-Za-z][A-Za-z0-9 .'\-/&]*$")
    ticker_re = re.compile(r"^[A-Z0-9]{2,10}$")

    pairs, seen_fa, dropped = [], {}, 0
    for i, line in enumerate(lines):
        if not line or not fa_re.search(line):
            continue                        # only anchor on FA lines
        # EN key: closest Latin line above (skip the FA line itself)
        en = ""
        for j in range(i - 1, max(-1, i - 3), -1):
            if j >= 0 and latin_re.match(lines[j]):
                en = norm_en(lines[j])
                break
        fa = norm_fa(line)
        if not en or not fa or en == fa:
            continue                        # no EN side, or FA missing (Latin)
        if fa in seen_fa and seen_fa[fa] != en:
            dropped += 1                    # contradiction: keep first mapping
            continue
        seen_fa.setdefault(fa, en)
        pairs.append({"en": en, "fa": fa, "pos": "-", "domain": "crypto",
                      "source": "vendor:crypto_names", "conf": CONF["vendor"]})
        # optional ticker on the next line
        if i + 1 < len(lines) and ticker_re.match(lines[i + 1]):
            pairs.append({"en": norm_en(lines[i + 1]), "fa": fa, "pos": "-",
                          "domain": "crypto",
                          "source": "vendor:crypto_names#ticker", "conf": 0.75})
    if dropped:
        print(f"  [warn] vendor: dropped {dropped} contradicting FA duplicates")
    # vendor/list.txt is FA-only -> cannot form EN->FA pairs (documented skip)
    return pairs


# ---------------------------------------------------------------- source 2
def load_wikidata_terms():
    """enwiki category members -> Wikidata fa labels."""
    out = []
    seen_en = defaultdict(set)
    for i, (domain, cat) in enumerate(CATEGORIES):
        titles, cont = [], ""
        while len(titles) < 500:
            url = CATMEM_URL.format(cat=urllib.parse.quote(cat),
                                    cont=urllib.parse.quote(cont))
            data = _cached_json(url, f"catmem_{i}_{len(titles)}.json")
            qm = data.get("query", {})
            cm = qm.get("categorymembers", [])
            titles += [m["title"] for m in cm
                       if m.get("ns") == 0 and not m["title"].startswith("List ")]
            cont = (qm.get("continue", {}) or {}).get("cmcontinue")
            if not cont or not cm:
                break
        # -> fa label, 50 titles per request
        for s in range(0, len(titles), 50):
            chunk = titles[s:s + 50]
            url = GETENT_URL.format(titles=urllib.parse.quote("|".join(chunk)))
            try:
                data = _cached_json(url, f"gent_{i}_{s}.json", timeout=90)
            except Exception as e:            # noqa: BLE001
                print(f"  [skip] {cat} chunk {s}: {e}")
                continue
            for ent in (data.get("entities") or {}).values():
                labels = ent.get("labels") or {}
                en = (labels.get("en") or {}).get("value")
                fa = (labels.get("fa") or {}).get("value")
                if not en or not fa:
                    continue
                key = norm_en(en)
                val = norm_fa(fa)
                if not key or not val or key == val:
                    continue        # same-script labels: no EN->FA pair
                if val in seen_en[key]:
                    continue
                seen_en[key].add(val)
                out.append({"en": key, "fa": val, "pos": "-", "domain": domain,
                            "source": "wikidata:interlanguage",
                            "conf": CONF["wikidata"]})
        print(f"  [ok]   {domain}: titles={len(titles)}")
    return out


# ------------------------------------------------------- source 2b (seeds)
SEARCH_URL = ("https://www.wikidata.org/w/api.php?action=wbsearchentities"
              "&search={q}&language=en&type=item&format=json&uselang=en&limit=8")
GETENT_IDS_URL = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
                  "&ids={ids}&props=labels&languages=fa|en&format=json")
# Seeds whose Wikidata label does not contain the term textually; accepted as
# an unambiguous hit (each is the standard expansion of the abbreviation).
TERM_PIN = {"etf", "gdp"}
# Finance-sense check on the hit's English description: generic words like
# "bond"/"ripple"/"options" otherwise resolve to given names, villages or
# editions. An item is only a candidate when its description mentions the
# financial domain.
DOMAIN_HINT = re.compile(
    r"econom|financ|bank|currenc|market|trad|invest|stock|bond|securit"
    r"|money|monetar|fiscal|crypto|blockchain|coin|derivativ|tax|debt"
    r"|profit|revenu|risk|exchange|price|inflat|payment|commodit|treasur"
    r"|yield|capital|equity|dividend|lend|borrow"
    # business-cycle & corporate wording used by Wikidata descriptions
    r"|business|company|corporat|product|output|contraction|expansion"
    r"|unemploy|wage|spending|supply|demand|decline|recover", re.I)


def load_term_seeds():
    """Generic terms via the Wikidata search API.

    For each seed: keep the ranked hits whose label contains the term (or vice
    versa) AND whose description is finance-flavoured; batch-fetch fa labels
    for all candidates; accept the FIRST ranked candidate that actually has an
    fa label. Unresolved terms are reported, never guessed.
    """
    candidates = {}
    qids = []
    for i, (domain, term) in enumerate(TERM_SEEDS):
        slug = re.sub(r"[^a-z0-9]+", "_", term)
        try:
            data = _cached_json(SEARCH_URL.format(q=urllib.parse.quote(term)),
                                f"tsearch8_{i}_{slug}.json")
        except Exception as e:            # noqa: BLE001
            print(f"  [skip] term search {term!r}: {e}")
            continue
        cands = []
        for h in data.get("search") or []:
            label = (h.get("label") or "").lower()
            desc = h.get("description") or ""
            if not h.get("id"):
                continue
            if not (term in label or (label in term and len(label) >= 4)
                    or term in TERM_PIN):
                continue
            if not DOMAIN_HINT.search(desc):
                continue
            cands.append(h["id"])
        if cands:
            candidates[i] = cands
            qids += cands

    labels = {}
    uniq = list(dict.fromkeys(qids))
    for s in range(0, len(uniq), 50):
        chunk = uniq[s:s + 50]
        tag = hashlib.md5("|".join(sorted(chunk)).encode()).hexdigest()[:10]
        try:
            data = _cached_json(GETENT_IDS_URL.format(ids="|".join(chunk)),
                                f"tgent_{tag}.json")
        except Exception as e:            # noqa: BLE001
            print(f"  [skip] term entities chunk {s}: {e}")
            continue
        for qid, ent in (data.get("entities") or {}).items():
            l = ent.get("labels") or {}
            labels[qid] = ((l.get("en") or {}).get("value"),
                           (l.get("fa") or {}).get("value"))

    out = []
    for i, (domain, term) in enumerate(TERM_SEEDS):
        for qid in candidates.get(i, []):
            fa = (labels.get(qid) or (None, None))[1]
            if fa:
                out.append({"en": norm_en(term), "fa": norm_fa(fa), "pos": "-",
                            "domain": domain, "source": "wikidata:term-seed",
                            "conf": CONF["wikidata"]})
                break
        else:
            print(f"  [warn] term unresolved: {term}")
    return out


# ---------------------------------------------------------------- source 3
def load_wiktionary():
    """fa.wiktionary pages: page title (FA word) x [[en:...]] interwiki links."""
    if not WIKTIONARY_DUMP.exists():
        from fa_norm import download
        print("[wiktionary] downloading dump ...")
        size = download(WIKTIONARY_URL, WIKTIONARY_DUMP, timeout=180)
        print(f"[wiktionary] dump bytes={size}")
    import bz2
    import xml.etree.ElementTree as ET
    pairs = []
    interwiki_re = re.compile(r"\[\s*en\s*:\s*([^\]#|]+)", re.I)
    with bz2.open(WIKTIONARY_DUMP, "rb") as fh:
        for _event, el in ET.iterparse(fh, events=("end",)):
            if el.tag.rsplit("}", 1)[-1] != "page":
                continue
            title, text = None, None
            for sub in el:
                tag = sub.tag.rsplit("}", 1)[-1]
                if tag == "title":
                    title = sub.text or ""
                elif tag == "revision":
                    for s2 in sub:
                        if s2.tag.rsplit("}", 1)[-1] == "text":
                            text = s2.text or ""
            el.clear()
            if not title or not text or text.lstrip().startswith("#REDIRECT"):
                continue
            if ":" in title:
                continue            # template / namespace / interwiki pages
            fa = norm_fa(title)
            if not fa or not _FA_RE.match(fa):
                continue
            for en in interwiki_re.findall(text):
                en = norm_en(en)
                if en and _LATIN_RE.match(en) and ":" not in en:
                    pairs.append({"en": en, "fa": fa, "pos": "-",
                                  "domain": "general", "source": "wiktionary-fa",
                                  "conf": CONF["wiktionary"]})
    return pairs


# ---------------------------------------------------------------- evidence
def _canon(fa):
    """Typography-insensitive form: ZWNJ/space removed (so «بیت‌کوین» and
    «بیت کوین» count as one rendering family; genuinely different words like
    «بازدهی» vs «بازده» stay separate)."""
    return fa.replace(ZWNJ, "").replace(" ", "")


def corpus_evidence(contested):
    """For each contested key: occurrences of each rendering family inside the
    FA titles whose EN title contains the key. Read-only DB.

    contested: {en_key: [fa_rendering, ...]}; returns {en_key: {canon: count}}.
    """
    ev = defaultdict(Counter)
    try:
        con = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True)
        cur = con.cursor()
        rows = cur.execute(
            "SELECT title, title_fa FROM articles "
            "WHERE title_fa IS NOT NULL AND title_fa <> ''"
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return ev
    wanted = {k: [_canon(f) for f in v] for k, v in contested.items()}
    for title, title_fa in rows:
        if not title or not title_fa:
            continue
        low = title.lower()
        canon_title = _canon(title_fa)
        for key, fams in wanted.items():
            if key in low:
                for fam in fams:
                    c = canon_title.count(fam)
                    if c:
                        ev[key][fam] += c
    return ev


def main():
    print("[terms] sources: vendor + wikidata + fa.wiktionary")
    all_pairs = []
    all_pairs += load_vendor()
    print(f"  [ok]   vendor: {len(all_pairs)} pairs")
    all_pairs += load_wikidata_terms()
    print(f"  [ok]   wikidata: total {len(all_pairs)} pairs")
    all_pairs += load_term_seeds()
    print(f"  [ok]   term-seeds: total {len(all_pairs)} pairs")
    all_pairs += load_wiktionary()
    print(f"  [ok]   wiktionary: total {len(all_pairs)} pairs")

    # merge: one row per (en, fa); domains/sources/conf merged per (en, fa)
    merged = {}
    for p in all_pairs:
        k = (p["en"], p["fa"])
        m = merged.setdefault(k, dict(p, domains=[p["domain"]],
                                      sources=[p["source"]],
                                      conf=p["conf"]))
        if p["domain"] not in m["domains"]:
            m["domains"].append(p["domain"])
        if p["source"] not in m["sources"]:
            m["sources"].append(p["source"])
            m["conf"] = max(m["conf"], p["conf"])

    by_en = defaultdict(list)
    for (en, fa), m in merged.items():
        by_en[en].append(m)

    # corpus evidence only for contested keys (multi-family renderings)
    fam_map = {}
    for en, ms in by_en.items():
        fams = {_canon(m["fa"]) for m in ms}
        if len(fams) > 1:
            fam_map[en] = sorted(fams)
    evidence = corpus_evidence(fam_map) if fam_map else {}

    rows, review = [], []
    for en in sorted(by_en):
        variants = sorted(by_en[en], key=lambda m: m["fa"])
        fams = {_canon(m["fa"]) for m in variants}
        pref_fam = None
        if len(fams) > 1:
            ev = evidence.get(en, Counter())
            aligned = sum(ev.get(f, 0) for f in fams)
            top = max(fams, key=lambda f: ev.get(f, 0))
            if aligned >= EVID_MIN and ev.get(top, 0) / aligned >= EVID_PREF:
                pref_fam = top
            review.append({
                "en": en,
                "domains": sorted({d for m in variants for d in m["domains"]}),
                "variants": [(m["fa"], _canon(m["fa"]), ev.get(_canon(m["fa"]), 0))
                             for m in variants],
                "aligned": aligned,
                "preferred_fam": pref_fam,
            })
        for m in variants:
            conf = m["conf"]
            if pref_fam is not None:
                conf = 0.95 if _canon(m["fa"]) == pref_fam else 0.6
            rows.append([m["en"], m["fa"], m["pos"], ",".join(m["domains"]),
                         "+".join(m["sources"]), f"{conf:.2f}"])

    out = DATA_FA / "terms.tsv"
    write_tsv(out, ["en", "fa", "pos", "domain", "source", "confidence"], rows)

    # REVIEW.md: contested keys with evidence; preferred only when evidence
    # supports it, otherwise human review.
    DATA_FA.mkdir(parents=True, exist_ok=True)
    lines = ["# data/fa/REVIEW.md — terms needing a human decision",
             "",
             "Generated by `tools/fa_build/fetch_terms.py`. Each block is one "
             "English key with\nseveral Persian rendering families (typography "
             "variants like space-vs-ZWNJ are\ngrouped: `بیت‌کوین` == `بیت "
             "کوین`). `evidence` = occurrences inside the project's own "
             "published (EN title -> FA title) pairs, read-only. **preferred** "
             "is set only when one family holds >=70% of >=10 aligned "
             "occurrences; otherwise the key stays open for a human. "
             "Finance-domain keys come first in full blocks; general-"
             "vocabulary keys are listed compactly at the end.",
             ""]
    open_keys = 0
    domain_items = [it for it in review if it["domains"] != ["general"]]
    general_items = [it for it in review if it["domains"] == ["general"]]
    lines.append(f"### Finance / economics / trading / crypto keys "
                 f"({len(domain_items)})")
    lines.append("")
    for item in domain_items:
        if item["preferred_fam"]:
            tag = "auto-preferred (strong corpus evidence)"
        else:
            tag = "NEEDS REVIEW"
            open_keys += 1
        lines.append(f"## {item['en']} — {tag} "
                     f"(domain: {','.join(item['domains'])})")
        for fa, fam, cnt in item["variants"]:
            mark = (" **<-- preferred family**"
                    if fam == item["preferred_fam"] else "")
            lines.append(f"- `{fa}` — evidence={cnt}{mark}")
        lines.append(f"- aligned occurrences: {item['aligned']}")
        lines.append("")
    lines.append(f"### General vocabulary keys from fa.wiktionary "
                 f"({len(general_items)}) — lower priority")
    lines.append("")
    for item in general_items:
        if not item["preferred_fam"]:
            open_keys += 1
        variants = " / ".join(f"`{fa}`({cnt})" for fa, _f, cnt in item["variants"])
        tag = "auto-preferred" if item["preferred_fam"] else "open"
        lines.append(f"- {item['en']}: {variants} — {tag}, "
                     f"aligned={item['aligned']}")
    lines.append("")
    lines += [f"Contested keys: {len(review)} (open: {open_keys}, "
              f"auto-preferred: {len(review) - open_keys}).", ""]
    (DATA_FA / "REVIEW.md").write_text("\r\n".join(lines), encoding="utf-8",
                                       newline="")

    sources = [
        {"name": "vendor/persian-crypto-words (MIT)",
         "url": "vendor/persian-crypto-words/crypto_names.txt",
         "license": "MIT",
         "detail": "local file; semantic line scan (EN/FA/ticker), "
                   "contradicting duplicate FA values dropped"},
        {"name": "Wikidata via enwiki categories (CC0)",
         "url": "https://www.wikidata.org/w/api.php (sites=enwiki)",
         "license": "CC0-1.0",
         "detail": ", ".join(f"{d}:{c}" for d, c in CATEGORIES)},
        {"name": "Wikidata term seeds (CC0)",
         "url": "https://www.wikidata.org/w/api.php (wbsearchentities)",
         "license": "CC0-1.0",
         "detail": f"{len(TERM_SEEDS)} generic finance/econ/trading/crypto "
                   "terms from docs/fa_audit.md §6"},
        {"name": "fa.wiktionary dump (CC BY-SA 4.0)",
         "url": WIKTIONARY_URL,
         "license": "CC BY-SA 4.0",
         "detail": "interwiki [[en:...]] links on fa pages"},
        {"name": "project corpus (read-only)",
         "url": ".mohmd_news.db articles.title/title_fa",
         "license": "n/a (own data)",
         "detail": "evidence counts for REVIEW.md only"},
    ]
    write_stats("terms", "terms.tsv", len(rows), sources,
                notes=[f"contested keys: {len(review)} (open: {open_keys}); "
                       "pos '-' where no source states it (never guessed).",
                       "vendor/list.txt skipped: FA-only, cannot form EN->FA "
                       "pairs."])
    print(f"[terms] wrote {out} rows={len(rows)} "
          f"contested={len(review)} open={open_keys}")


if __name__ == "__main__":
    main()
