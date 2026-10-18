#!/usr/bin/env python3
"""
FA data collection — entities.tsv (Phase 1, deliverable a)
==========================================================
English -> Persian labels + aliases for the entity families the audit found
leaking into published outputs: central banks, stock exchanges, indices,
currencies, commodities, countries, banks, crypto exchanges — plus a curated
seed list of prominent finance organizations/companies/people (audit §5/§9).

Source: Wikidata (CC0). SPARQL for instance-classes; search+getentities API
for the seed list (avoids hand-guessed QIDs).

Network: only here, >=1.1 s between requests, resumable (raw JSON cached in
var/fa_raw/, gitignored). Run standalone:  python tools/fa_build/fetch_entities.py
Never imported by app.py.
"""
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fa_norm import (RAW_DIR, DATA_FA, http_get_json, norm_en, norm_fa,
                     write_stats, write_tsv)

SPARQL_URL = "https://query.wikidata.org/sparql?format=json&query="
SEARCH_URL = ("https://www.wikidata.org/w/api.php?action=wbsearchentities"
              "&search={q}&language=en&type=item&format=json&uselang=en&limit=5")
GETENT_URL = ("https://www.wikidata.org/w/api.php?action=wbgetentities"
              "&ids={ids}&props=labels|aliases&languages=en|fa&format=json")

# Seeds whose label differs from the search top-hit; QIDs pinned manually and
# re-verified by the wbgetentities response (labels cross-checked in output).
SEED_QID_PIN = {
    "Federal Reserve": "Q24812",   # Federal Reserve System
    "U.S. Securities and Exchange Commission": "Q783764",
    "Taiwan Semiconductor Manufacturing Company": "@top",  # label now "TSMC"
    "Crude oil": "@top",          # search top-hit = petroleum (نفت)
}


def _norm_name(s):
    s = s.lower().replace(".", " ").replace(",", " ").replace("'", "")
    s = re.sub(r"\b(the|group|inc|corp|corporation|company|holding)s?\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _names_match(seed, label):
    """Loose-but-safe label match: containment or a shared distinctive token."""
    if not label:
        return False
    a, b = _norm_name(seed), _norm_name(label)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    ta = {t for t in a.split() if len(t) >= 5}
    tb = {t for t in b.split() if len(t) >= 5}
    return bool(ta & tb)

# kind -> SPARQL instance-of class (verified QIDs, 2026-10-12)
SPARQL_CLASSES = [
    ("central_bank",   "Q66344"),
    ("stock_exchange", "Q11691"),
    ("stock_index",    "Q223371"),
    ("currency",       "Q8142"),
    ("commodity",      "Q317088"),
    ("country",        "Q6256"),
    ("bank",           "Q22687"),
    ("crypto_exchange", "Q25401607"),
]

# ONE combined request for all classes (WDQS is currently at ~1 req/min; batching
# keeps us far below that). `cls` carries the instance-of class back out.
_QUERY = ("SELECT ?item ?cls ?en ?fa ?enAlt ?faAlt WHERE { "
          "VALUES ?cls { " + " ".join("wd:" + c for _k, c in SPARQL_CLASSES) + " } "
          "?item wdt:P31 ?cls. "
          "OPTIONAL { ?item rdfs:label ?en. FILTER(LANG(?en)=\"en\") } "
          "OPTIONAL { ?item rdfs:label ?fa. FILTER(LANG(?fa)=\"fa\") } "
          "OPTIONAL { ?item skos:altLabel ?enAlt. FILTER(LANG(?enAlt)=\"en\") } "
          "OPTIONAL { ?item skos:altLabel ?faAlt. FILTER(LANG(?faAlt)=\"fa\") } "
          "} LIMIT 20000")

# Curated seeds (every entry appears in the project's own corpus — audit §5/§9
# worst-example names or top Latin residue tokens; finance/crypto figures &
# organizations). Resolved via the Wikidata search API, never by guessed QIDs.
SEEDS = [
    ("org",     "Federal Reserve"),
    ("org",     "U.S. Securities and Exchange Commission"),
    ("org",     "European Central Bank"),
    ("org",     "Bank of England"),
    ("org",     "People's Bank of China"),
    ("org",     "Bank of Japan"),
    ("org",     "Swiss National Bank"),
    ("org",     "International Monetary Fund"),
    ("org",     "World Bank"),
    ("org",     "BlackRock"),
    ("org",     "Vanguard Group"),
    ("org",     "Fidelity Investments"),
    ("org",     "Goldman Sachs"),
    ("org",     "JPMorgan Chase"),
    ("org",     "Morgan Stanley"),
    ("org",     "Citigroup"),
    ("org",     "UBS Group"),
    ("org",     "HSBC"),
    ("org",     "Deutsche Bank"),
    ("org",     "Standard Chartered"),
    ("company", "MicroStrategy"),
    ("company", "Coinbase"),
    ("company", "Binance"),
    ("company", "Tether"),
    ("company", "Ripple Labs"),
    ("company", "Grayscale Investments"),
    ("company", "NVIDIA"),
    ("company", "Tesla, Inc."),
    ("company", "Apple Inc."),
    ("company", "Microsoft"),
    ("company", "Amazon"),
    ("company", "Alphabet Inc."),
    ("company", "Samsung Electronics"),
    ("company", "Taiwan Semiconductor Manufacturing Company"),
    ("company", "Micron Technology"),
    ("person",  "Jerome Powell"),
    ("person",  "Janet Yellen"),
    ("person",  "Christine Lagarde"),
    ("person",  "Gary Gensler"),
    ("person",  "Austan Goolsbee"),
    ("person",  "Neel Kashkari"),
    ("person",  "Mary Daly"),
    ("person",  "Raphael Bostic"),
    ("person",  "Michael Barr"),
    ("person",  "Christopher Waller"),
    ("person",  "John C. Williams"),
    ("person",  "Michelle Bowman"),
    ("person",  "Philip Jefferson"),
    ("person",  "Adriana Kugler"),
    ("person",  "Lorie Logan"),
    ("person",  "Thomas Barkin"),
    ("person",  "Michael Saylor"),
    ("person",  "Vitalik Buterin"),
    ("person",  "Changpeng Zhao"),
    ("person",  "Brian Armstrong"),
    ("person",  "Cathie Wood"),
    ("person",  "Warren Buffett"),
    ("person",  "Charlie Munger"),
    ("person",  "Jamie Dimon"),
    ("person",  "Larry Fink"),
    ("person",  "Ray Dalio"),
    ("person",  "Peter Schiff"),
    ("person",  "Robert Kiyosaki"),
    ("person",  "Donald Trump"),
    # commodities: P31=Q317088 is sparse on Wikidata (~8 instances); the
    # traded-commodity names that actually appear in finance news are seeded.
    ("commodity", "Gold"),
    ("commodity", "Silver"),
    ("commodity", "Crude oil"),
    ("commodity", "Natural gas"),
    ("commodity", "Copper"),
    ("commodity", "Aluminium"),
    ("commodity", "Zinc"),
    ("commodity", "Nickel"),
    ("commodity", "Lithium"),
    ("commodity", "Uranium"),
    ("commodity", "Wheat"),
    ("commodity", "Maize"),
    ("commodity", "Soybeans"),
    ("commodity", "Coffee"),
    ("commodity", "Cotton"),
    ("commodity", "Sugar"),
    ("commodity", "Iron ore"),
    ("commodity", "Cocoa bean"),
]

PAUSE = 1.5  # politeness: <=0.7 req/s (spec allows 1 req/s; extra headroom)


def _cached_json(url, cache_name, timeout=120, backoff=8):
    """GET url, caching the raw response under var/fa_raw/ (resumable).

    Retries HTTP 429 with growing backoff. WDQS occasionally enforces
    ~1 req/min, so `backoff=65` is used for the SPARQL call.
    """
    path = RAW_DIR / cache_name
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if not (isinstance(cached, dict) and cached.get("error")):
            return cached
        path.unlink()                      # error body was cached: refetch
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
            time.sleep(wait)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(PAUSE)
    return data


def _norm_alias(a):
    """One alias token -> normalized string or None if empty/junk."""
    a = norm_fa(a)
    a = a.strip("\"'()[]{} ")
    return a or None


def _collect(qid2row, qid, kind, en, fa, en_alt, fa_alt, source):
    if not en or not fa:
        return
    row = qid2row.setdefault(qid, {
        "kind": kind, "qid": qid, "en": norm_en(en), "fa": norm_fa(fa),
        "aliases_en": [], "aliases_fa": [], "source": source,
    })
    for alt in ([en_alt] if isinstance(en_alt, str) else (en_alt or [])):
        a = norm_en(alt or "")
        if a and a != row["en"] and a not in row["aliases_en"]:
            row["aliases_en"].append(a)
    for alt in ([fa_alt] if isinstance(fa_alt, str) else (fa_alt or [])):
        a = _norm_alias(alt or "")
        if a and a != row["fa"] and a not in row["aliases_fa"]:
            row["aliases_fa"].append(a)


def fetch_sparql(qid2row):
    cls2kind = {c: k for k, c in SPARQL_CLASSES}
    url = SPARQL_URL + urllib.parse.quote(_QUERY, safe="")
    try:
        data = _cached_json(url, "wd_classes.json", timeout=300, backoff=65)
    except Exception as e:                # noqa: BLE001 - report & continue
        print(f"  [skip] sparql classes: {e}")
        return
    rows = data.get("results", {}).get("bindings", [])
    per_kind = {}
    for b in rows:
        def v(name, b=b):
            return b.get(name, {}).get("value")
        qid = v("item")
        if not qid:
            continue
        qid = qid.rsplit("/", 1)[-1]
        cls = (v("cls") or "").rsplit("/", 1)[-1]
        kind = cls2kind.get(cls)
        if not kind:
            continue
        before = len(qid2row)
        _collect(qid2row, qid, kind, v("en"), v("fa"),
                 v("enAlt"), v("faAlt"), f"wikidata-sparql:{cls}")
        per_kind[kind] = per_kind.get(kind, 0) + len(qid2row) - before
    print(f"  [ok]   sparql: {len(rows)} bindings -> rows={per_kind}")


def fetch_seeds(qid2row):
    resolved, unresolved = {}, []
    for i, (kind, name) in enumerate(SEEDS):
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        try:
            data = _cached_json(SEARCH_URL.format(q=name.replace(" ", "%20")),
                                f"wd_search_{slug}.json")
        except Exception as e:            # noqa: BLE001
            print(f"  [skip] search {name!r}: {e}")
            continue
        top = (data.get("search") or [{}])[0]
        label = top.get("label", "")
        pin = SEED_QID_PIN.get(name)
        if not top.get("id"):
            # empty search response (transient API behaviour) — reported
            unresolved.append((name, label or "(empty search response)"))
            continue
        if pin:                                   # pinned: accept top hit
            qid = top["id"] if pin == "@top" else pin
        elif _names_match(name, label):           # loose label match
            qid = top["id"]
        else:
            unresolved.append((name, label))
            continue
        resolved[qid] = kind
    ids = list(resolved)
    for start in range(0, len(ids), 50):
        chunk = ids[start:start + 50]
        tag = hashlib.md5("|".join(sorted(chunk)).encode()).hexdigest()[:10]
        try:
            data = _cached_json(GETENT_URL.format(ids="|".join(chunk)),
                                f"wd_entities_{tag}.json")
        except Exception as e:            # noqa: BLE001
            print(f"  [skip] entities chunk {start}: {e}")
            continue
        for qid, ent in (data.get("entities") or {}).items():
            labels = ent.get("labels") or {}
            aliases = ent.get("aliases") or {}
            _collect(qid2row, qid, resolved.get(qid, "seed"),
                     (labels.get("en") or {}).get("value"),
                     (labels.get("fa") or {}).get("value"),
                     [a.get("value") for a in aliases.get("en", [])],
                     [a.get("value") for a in aliases.get("fa", [])],
                     "wikidata-search:seed")
    for name, got in unresolved:
        print(f"  [warn] seed unresolved (search top={got!r}): {name}")


def main():
    print("[entities] Wikidata -> data/fa/entities.tsv")
    qid2row = {}
    fetch_sparql(qid2row)
    print("[entities] seed list via search API ...")
    fetch_seeds(qid2row)

    rows = []
    for r in sorted(qid2row.values(), key=lambda x: (x["kind"], x["en"], x["qid"])):
        rows.append([
            r["kind"], r["qid"], r["en"], r["fa"],
            "|".join(r["aliases_en"][:6]), "|".join(r["aliases_fa"][:6]),
            r["source"],
        ])
    out = DATA_FA / "entities.tsv"
    write_tsv(out, ["kind", "qid", "en", "fa", "aliases_en", "aliases_fa", "source"],
              rows)

    sparql_k, seed_k = {}, {}
    for r in rows:
        bucket = sparql_k if r[6].startswith("wikidata-sparql") else seed_k
        bucket[r[0]] = bucket.get(r[0], 0) + 1
    fmt = lambda d: ", ".join(f"{k}={v}" for k, v in sorted(d.items()))
    sources = ([{"name": "Wikidata (SPARQL, CC0)",
                 "url": "https://query.wikidata.org/sparql",
                 "license": "CC0-1.0",
                 "detail": fmt(sparql_k)}]
               + [{"name": "Wikidata (search+getentities, CC0)",
                   "url": "https://www.wikidata.org/w/api.php",
                   "license": "CC0-1.0",
                   "detail": fmt(seed_k)}]
               + [{"name": "project corpus audit seeds",
                   "url": "docs/fa_audit.md §5/§9",
                   "license": "n/a (input list)",
                   "detail": f"{len(SEEDS)} English names: corpus-audit finance/crypto names + traded commodities"}])
    write_stats("entities", "entities.tsv", len(rows), sources,
                notes=["No inferred rows: entities without an fa Wikidata label "
                       "are skipped (never fabricated)."])
    print(f"[entities] wrote {out} rows={len(rows)} "
          f"sparql={fmt(sparql_k)} seeds={fmt(seed_k)}")


if __name__ == "__main__":
    main()
