#!/usr/bin/env python3
"""
Phase-0 live endpoint probe — NETWORK REQUIRED. Standalone by construction:
  * never imported by the app; tests never run it,
  * performs no writes: no cache file, no DB, no settings.json,
  * raw requests.get only — never translate.translate_many (which would
    write to .translate_cache.json),
  * translate.is_persian is imported for the gate (pure function, no I/O),
  * 1 request/second; honors the MOHMD_PROXY env var.

Prints measurements only. Nothing here changes translate.py.

Run: .venv/Scripts/python.exe tools/fa_build/probe_endpoint.py
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
from translate import ENDPOINT, UA, _flatten, is_persian  # noqa: E402
from fa_format import fa_digits  # noqa: E402

DB = BASE / ".mohmd_news.db"
CACHE = BASE / ".translate_cache.json"

SLEEP = 1.1

# fixed samples chosen from the real cache (md5 of the source text)
ECHO_KEYS = [
    "1a53186f9758b5dc42c576011b71ce3d",   # English headline echoed verbatim
    "2db546e661768672079665f69e37f772",   # English headline echoed verbatim
]
MULTI_KEY = "018e8646ea91197e78b4c628d3261cb1"   # multi-sentence, half-translated
LENGTH_TARGETS = [2048, 4096, 8192, 16384]       # total query length, chars


def md5(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "cache_copy.json"
        shutil.copyfile(CACHE, tmp)
        cache = json.loads(tmp.read_text(encoding="utf-8"))
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute("SELECT title, summary FROM articles").fetchall()
    con.close()
    idx = {}
    for title, summary in rows:
        if title:
            idx.setdefault(md5(title), title)
        if summary and len(summary) >= 40:
            idx.setdefault(md5(summary[:1000]), summary[:1000])
            idx.setdefault(md5(summary), summary)
    return cache, idx


def ask(qs):
    """One GET with the given q params (production shape). 1 req/s enforced."""
    params = [("client", "dict-chrome-ex"), ("sl", "en"), ("tl", "fa")]
    params += [("q", q) for q in qs]
    prepared = requests.Request("GET", ENDPOINT, params=params, headers=UA).prepare()
    proxies = {}
    if os.environ.get("MOHMD_PROXY"):
        proxies = {"http": os.environ["MOHMD_PROXY"],
                   "https": os.environ["MOHMD_PROXY"]}
    status, items = -1, []
    try:
        r = requests.get(prepared.url, headers=UA, timeout=25, proxies=proxies)
        status = r.status_code
        if status == 200:
            items = _flatten(r.json())
    except Exception as ex:
        print(f"   transport error: {type(ex).__name__}")
    time.sleep(SLEEP)
    return status, items, len(prepared.url)


def gate_line(text):
    from translate import persian_share, longest_latin_run
    return (f"pass={1 if is_persian(text) else 0} "
            f"share={persian_share(text):.2f} run={longest_latin_run(text)}")


def probe_a(cache, idx):
    print("== (a) re-asking echoed headlines ==")
    for key in ECHO_KEYS:
        cached = cache.get(key, "")
        src = idx.get(key) or cached
        status, items, _ = ask([src])
        out = items[0] if items else ""
        print(f"[a] key={key[:8]} status={status} n={len(items)} "
              f"cached={gate_line(cached)}")
        print(f"    cached_is_source={1 if cached == src else 0} "
              f"fresh_empty={1 if not out else 0} {gate_line(out)}")


def probe_b(cache, idx):
    print("== (b) sentence-by-sentence on a failing multi-sentence text ==")
    cached = cache.get(MULTI_KEY, "")
    src = idx.get(MULTI_KEY) or cached
    sents = [s for s in re.split(r"(?<=[.!?])\s+", src) if s.strip()]
    status, items, _ = ask([src])
    whole = items[0] if items else ""
    print(f"[b] src_len={len(src)} sents={len(sents)} cached={gate_line(cached)}")
    print(f"    whole: status={status} n={len(items)} {gate_line(whole)}")
    parts = []
    part_pass = []
    for s in sents:
        st, it, _ = ask([s[:4000]])
        t = it[0] if it else ""
        parts.append(t)
        part_pass.append(1 if is_persian(t) else 0)
    joined = " ".join(p for p in parts if p)
    print(f"    split: per_sentence_pass={part_pass}")
    print(f"    split_joined: {gate_line(joined)}")


def probe_c():
    print("== (c) request failure vs total query length ==")
    filler = ("Gold holds steady as traders weigh Fed rate path outlook for the "
              "coming weeks amid persistent inflation concerns worldwide ")
    for target in LENGTH_TARGETS:
        q, qs, total = "", [], 0
        while total < target:
            q = (filler * (1 + (4000 // len(filler))))[:4000]
            qs.append(q)
            total += len(q) + 3          # ~"q=&" overhead per param
            if len(qs) >= 16:
                break
        status, items, url_len = ask(qs)
        ok = 1 if (status == 200 and len(items) == len(qs)) else 0
        print(f"[c] target={target} n_q={len(qs)} url_len={url_len} "
              f"status={status} n_items={len(items)} complete={ok}")


def probe_d(idx):
    print("== (d) batch-of-16 alignment with an empty / very short member ==")
    ascii_titles = []
    for key, text in idx.items():
        letters = [c for c in text if c.isalpha()]
        if 30 <= len(text) <= 90 and letters and \
                sum(1 for c in letters if c.isascii()) / len(letters) > 0.9:
            ascii_titles.append((key, text))
    ascii_titles.sort(key=lambda x: x[0])
    chosen = [t for _k, t in ascii_titles[:40]][:16]
    if len(chosen) < 16:
        print("[d] not enough English sources — aborting")
        return
    for run, slot7 in (("D1", chosen[7]), ("D2", ""), ("D3", "ok")):
        qs = []
        for i, t in enumerate(chosen):
            if i == 7:
                qs.append(f"{slot7} 9107" if slot7 else "")
            else:
                qs.append(f"{t} {9100 + i}")
        status, items, _ = ask(qs)
        hits = []
        for i in range(len(items)):
            marker = str(9100 + i)
            ok = 1 if (marker in items[i] or fa_digits(marker) in items[i]) else 0
            hits.append(str(ok))
        print(f"[d] run={run} slot7={'empty' if not slot7 else repr(slot7)[:12]} "
              f"status={status} n_req={len(qs)} n_items={len(items)} "
              f"aligned={sum(int(h) for h in hits)}/{len(qs)} pattern={''.join(hits)}")


def main():
    print(f"probe start — {time.strftime('%Y-%m-%d %H:%M:%S')}")
    cache, idx = load()
    probe_a(cache, idx)
    probe_b(cache, idx)
    probe_c()
    probe_d(idx)
    print("probe done")


if __name__ == "__main__":
    main()
